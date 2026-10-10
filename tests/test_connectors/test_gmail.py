"""Gmail password-hint connector, exercised against a fake Gmail service (synthetic emails only)."""

from __future__ import annotations

import base64
import json

import pytest

from src.connectors.gmail import (
    PasswordHint,
    authorize,
    extract_password_hint,
    fetch_password_hints,
    load_password_hints,
    message_text,
    save_password_hints,
)
from src.core.application import CommandInputError, run_gmail_command

RULE = "The password is the last 5 digits of your registered mobile number followed by your date of birth in DDMMYY format."
SBI_BODY = f"Dear Customer, your account statement is attached. The attachment is password protected. {RULE} Never share your password or OTP with anyone."


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def _message(message_id: str, body: str, *, mime: str = "text/plain", subject: str = "Account Statement") -> dict:
    return {
        "id": message_id,
        "internalDate": "1784073600000",  # 2026-07-15T00:00:00Z
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [{"name": "Subject", "value": subject}],
            "parts": [
                {"mimeType": "multipart/alternative", "parts": [{"mimeType": mime, "body": {"data": _b64(body)}}]},
                {"mimeType": "application/vnd.ms-excel", "filename": "statement.xlsx", "body": {"attachmentId": "a1"}},
            ],
        },
    }


class _Exec:
    def __init__(self, value: dict):
        self._value = value

    def execute(self) -> dict:
        return self._value


class FakeGmail:
    """Fake googleapiclient Gmail service: users().messages().list/get(...).execute()."""

    def __init__(self, listings: dict[str, list[str]], messages: dict[str, dict]):
        self.listings = listings
        self.messages_by_id = messages
        self.list_calls: list[dict] = []

    def users(self) -> FakeGmail:
        return self

    def messages(self) -> FakeGmail:
        return self

    def list(self, **kwargs) -> _Exec:
        self.list_calls.append(kwargs)
        return _Exec({"messages": [{"id": i} for i in self.listings.get(kwargs["q"], [])]})

    def get(self, userId: str, id: str, format: str) -> _Exec:  # noqa: A002 - mirrors the Gmail API signature
        assert (userId, format) == ("me", "full")
        return _Exec(self.messages_by_id[id])


def test_extract_password_hint_prefers_the_rule_over_boilerplate():
    assert extract_password_hint(SBI_BODY) == RULE


def test_extract_password_hint_returns_none_without_a_password_sentence():
    assert extract_password_hint("Your statement for July is attached.") is None


def test_message_text_falls_back_to_html_and_drops_markup():
    html = f"<html><style>p {{color: red}}</style><p>Statement attached.</p><p>{RULE}</p></html>"
    text = message_text(_message("m1", html, mime="text/html")["payload"])
    assert extract_password_hint(text) == RULE
    assert "color" not in text


def test_fetch_password_hints_uses_newest_message_that_has_a_hint():
    gmail = FakeGmail(
        listings={"from:sbi.co.in password": ["newest", "older"], "from:axisbank.com password": []},
        messages={
            "newest": _message("newest", "Reset your net banking password here."),
            "older": _message("older", SBI_BODY, subject="SBI e-Statement"),
        },
    )

    hints = fetch_password_hints(gmail, {"sbi": "from:sbi.co.in password", "AXIS": "from:axisbank.com password"})

    assert hints == [PasswordHint("SBI", RULE, "SBI e-Statement", "2026-07-15", "older")]
    assert gmail.list_calls[0] == {"userId": "me", "q": "from:sbi.co.in password", "maxResults": 10}


def test_save_password_hints_merges_by_bank(tmp_path):
    path = str(tmp_path / "hints.json")
    save_password_hints([PasswordHint("HDFC", "old rule", "s", "2026-01-01", "h1")], path)
    save_password_hints([PasswordHint("SBI", RULE, "s", "2026-07-15", "s1")], path)

    stored = load_password_hints(path)
    assert stored["HDFC"]["hint"] == "old rule"
    assert stored["SBI"]["hint"] == RULE


def test_run_gmail_command_saves_hints_and_reports_each_bank(tmp_path):
    hints_path = tmp_path / "hints.json"
    config = {
        "paths": {"password_hints": str(hints_path)},
        "gmail": {"queries": {"SBI": "from:sbi.co.in password", "AXIS": "from:axisbank.com password"}},
    }
    gmail = FakeGmail({"from:sbi.co.in password": ["m1"]}, {"m1": _message("m1", SBI_BODY)})

    lines = run_gmail_command(config, service=gmail)

    assert lines == [
        "AXIS: no password hint found in Gmail",
        f"SBI: {RULE}  (email of 2026-07-15: 'Account Statement')",
        f"Saved to {hints_path}",
    ]
    assert json.loads(hints_path.read_text())["SBI"]["message_id"] == "m1"


def test_run_gmail_command_requires_queries():
    with pytest.raises(CommandInputError, match=r"\[gmail.queries\]"):
        run_gmail_command({"gmail": {}}, service=FakeGmail({}, {}))


def test_fetch_password_hints_falls_back_to_snippet():
    message = _message("m1", "")
    message["payload"]["parts"][0]["parts"][0]["body"] = {}
    message["snippet"] = RULE
    gmail = FakeGmail({"q": ["m1"]}, {"m1": message})

    assert fetch_password_hints(gmail, {"SBI": "q"})[0].hint == RULE


class FakeCreds:
    def __init__(self, *, valid: bool, refresh_error: bool = False, label: str = "stored"):
        self.valid = valid
        self.expired = not valid
        self.refresh_token = "refresh"
        self.refresh_error = refresh_error
        self.label = label

    def refresh(self, _request) -> None:
        from google.auth.exceptions import RefreshError

        if self.refresh_error:
            raise RefreshError("invalid_grant")
        self.valid, self.expired, self.label = True, False, "refreshed"

    def to_json(self) -> str:
        return json.dumps({"label": self.label})


class FakeFlow:
    consent_kwargs: dict = {}

    @classmethod
    def from_client_secrets_file(cls, path, scopes):
        assert scopes == ["https://www.googleapis.com/auth/gmail.readonly"]
        return cls()

    def run_local_server(self, **kwargs):
        FakeFlow.consent_kwargs = kwargs
        return FakeCreds(valid=True, label="consented")


@pytest.fixture
def oauth(tmp_path, monkeypatch):
    stored: dict[str, FakeCreds] = {}
    monkeypatch.setattr(
        "google.oauth2.credentials.Credentials.from_authorized_user_file",
        lambda path, scopes=None: stored["creds"],
    )
    monkeypatch.setattr("google_auth_oauthlib.flow.InstalledAppFlow", FakeFlow)
    client = tmp_path / "client.json"
    client.write_text("{}")
    token = tmp_path / "token.json"
    return stored, str(client), token


def test_authorize_reuses_valid_token(oauth):
    stored, client, token = oauth
    token.write_text("{}")
    stored["creds"] = FakeCreds(valid=True)

    assert authorize(client, str(token)).label == "stored"


def test_authorize_refreshes_expired_token_and_saves_it(oauth):
    stored, client, token = oauth
    token.write_text("{}")
    stored["creds"] = FakeCreds(valid=False)

    assert authorize(client, str(token)).label == "refreshed"
    assert json.loads(token.read_text()) == {"label": "refreshed"}
    assert token.stat().st_mode & 0o777 == 0o600


def test_authorize_reconsents_offline_when_refresh_fails(oauth):
    stored, client, token = oauth
    token.write_text("{}")
    stored["creds"] = FakeCreds(valid=False, refresh_error=True)

    assert authorize(client, str(token)).label == "consented"
    assert FakeFlow.consent_kwargs == {"port": 0, "prompt": "consent", "access_type": "offline"}


def test_authorize_without_token_or_client_explains_setup(oauth, tmp_path):
    with pytest.raises(FileNotFoundError, match="Gmail OAuth client credentials not found"):
        authorize(str(tmp_path / "missing.json"), str(tmp_path / "token.json"))
