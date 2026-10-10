"""Read statement password *hints* from Gmail.

Banks email the rule for a statement password ("last 5 digits of your mobile number
followed by your date of birth"), never the password itself. This connector finds that
sentence with read-only Gmail access and saves it locally so the dashboard can show it
next to a password field. Nothing here reads, derives, or stores a password.

Uses the official google-api-python-client with Desktop OAuth consent (offline refresh
token); the cached token keeps whatever scopes it was granted.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")
_ABOUT_THE_FILE = re.compile(r"\b(open|attach\w*|statement|pdf|file|protected|encrypted)\b", re.IGNORECASE)
_PASSWORD_RULE = re.compile(
    r"\b(digits?|date of birth|dob|mobile|ddmm\w*|dd/mm\w*|pan|letters|characters|customer id|name)\b", re.IGNORECASE
)
_SECURITY_BOILERPLATE = re.compile(r"\b(never|do not share|don't share|otp|phishing|reset)\b", re.IGNORECASE)


@dataclass(slots=True)
class PasswordHint:
    bank: str
    hint: str
    subject: str
    received: str
    message_id: str


def authorize(credentials_path: str, token_path: str):
    """Return Gmail credentials, running the browser consent flow when there is no usable token.

    ``credentials_path`` is the OAuth "Desktop app" client JSON from Google Cloud Console.
    The token (with refresh token) is cached at ``token_path`` with 0600 permissions.
    """
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    token = Path(token_path)
    if token.exists():
        # scopes=None: adopt the token's granted scopes, so a broader read-only token also works.
        creds = Credentials.from_authorized_user_file(str(token))
        if creds.valid:
            return creds
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                _write_token(token, creds)
                return creds
            except RefreshError:
                pass  # revoked, or a Testing-mode refresh token past its 7 days: ask for consent again

    if not Path(credentials_path).exists():
        raise FileNotFoundError(f"Gmail OAuth client credentials not found: {credentials_path}")
    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, GMAIL_SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    _write_token(token, creds)
    return creds


def gmail_service(creds):
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def fetch_password_hints(service: Any, queries: dict[str, str], max_messages: int = 10) -> list[PasswordHint]:
    """For each bank, return the hint from the newest message matching its Gmail search query."""
    messages = service.users().messages()
    hints: list[PasswordHint] = []
    for bank, query in queries.items():
        listing = messages.list(userId="me", q=query, maxResults=max_messages).execute()
        for ref in listing.get("messages", []):  # Gmail lists newest first
            message = messages.get(userId="me", id=ref["id"], format="full").execute()
            payload = message.get("payload", {})
            hint = extract_password_hint(message_text(payload) or message.get("snippet", ""))
            if hint is None:
                continue
            hints.append(
                PasswordHint(
                    bank=bank.upper(),
                    hint=hint,
                    subject=_header(payload, "Subject"),
                    received=datetime.fromtimestamp(int(message["internalDate"]) / 1000, UTC).date().isoformat(),
                    message_id=message["id"],
                )
            )
            break
    return hints


def extract_password_hint(text: str) -> str | None:
    """Pick the sentence that best describes how the statement password is formed."""
    best: str | None = None
    best_score = 0
    for raw in _SENTENCE_BREAK.split(text):
        sentence = " ".join(raw.split())
        if "password" not in sentence.lower():
            continue
        score = (
            1
            + 3 * bool(_PASSWORD_RULE.search(sentence))
            + 2 * bool(_ABOUT_THE_FILE.search(sentence))
            - 4 * bool(_SECURITY_BOILERPLATE.search(sentence))
        )
        if score > best_score:
            best, best_score = sentence, score
    return best[:400] if best else None


def message_text(payload: dict) -> str:
    """Concatenate the text/plain parts of a Gmail message payload, falling back to text/html."""
    plain: list[str] = []
    html: list[str] = []
    stack = [payload]
    while stack:
        part = stack.pop()
        stack.extend(reversed(part.get("parts", [])))
        data = part.get("body", {}).get("data")
        if not data:
            continue
        decoded = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")
        if part.get("mimeType") == "text/plain":
            plain.append(decoded)
        elif part.get("mimeType") == "text/html":
            html.append(_html_to_text(decoded))
    return "\n".join(plain or html)


def load_password_hints(path: str) -> dict[str, dict]:
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return {}


def save_password_hints(hints: list[PasswordHint], path: str) -> None:
    """Merge hints into the JSON file keyed by bank, keeping banks that had no new match."""
    stored = load_password_hints(path)
    stored.update({hint.bank: asdict(hint) for hint in hints})
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(stored, indent=2, sort_keys=True) + "\n")


def _write_token(token: Path, creds: Any) -> None:
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(creds.to_json())
    token.chmod(0o600)


def _header(payload: dict, name: str) -> str:
    for header in payload.get("headers", []):
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


class _TextExtractor(HTMLParser):
    _BLOCK_TAGS = {"br", "p", "div", "tr", "li", "td", "h1", "h2", "h3", "table"}

    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip += 1
        elif tag in self._BLOCK_TAGS:
            self.chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.chunks.append(data)


def _html_to_text(html: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(html)
    return "".join(extractor.chunks)
