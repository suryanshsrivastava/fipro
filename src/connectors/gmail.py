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
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

_STATEMENT_EXTENSIONS = {".pdf", ".xls", ".xlsx"}
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


def fetch_password_hints(service: Any, queries: Mapping[str, str], max_messages: int = 10) -> list[PasswordHint]:
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


def fetch_statement_attachments(
    service: Any, queries: Mapping[str, str], dest_root: str, max_messages: int = 10
) -> list[Path]:
    """Save PDF/Excel attachments of mail matching each folder's query to ``dest_root/<folder>/``.

    Files are named ``<date>_<message id>_<original name>``; one that already exists is skipped,
    so re-running never overwrites. New files are made read-only like the rest of the corpus.
    """
    messages = service.users().messages()
    saved: list[Path] = []
    for folder, query in queries.items():
        target = Path(dest_root) / Path(folder.lower()).name
        listing = messages.list(userId="me", q=query, maxResults=max_messages).execute()
        for ref in listing.get("messages", []):
            message = messages.get(userId="me", id=ref["id"], format="full").execute()
            received = datetime.fromtimestamp(int(message["internalDate"]) / 1000, UTC).date().isoformat()
            for part in _attachment_parts(message.get("payload", {})):
                name = Path(part["filename"]).name
                if Path(name).suffix.lower() not in _STATEMENT_EXTENSIONS:
                    continue
                path = target / f"{received}_{message['id']}_{name}"
                if path.exists():
                    continue
                body = part["body"]
                data = body.get("data")
                if data is None:
                    attachment = messages.attachments().get(
                        userId="me", messageId=message["id"], id=body["attachmentId"]
                    )
                    data = attachment.execute()["data"]
                target.mkdir(parents=True, exist_ok=True)
                path.write_bytes(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)))
                path.chmod(0o444)
                saved.append(path)
    return saved


def _attachment_parts(payload: dict) -> list[dict]:
    parts: list[dict] = []
    stack = [payload]
    while stack:
        part = stack.pop()
        stack.extend(reversed(part.get("parts", [])))
        body = part.get("body", {})
        if part.get("filename") and (body.get("attachmentId") or body.get("data")):
            parts.append(part)
    return parts


_ALERT_REFERENCE = re.compile(r"reference\s*(?:no\.?|number)?\s*:?\s*(\d{12})", re.IGNORECASE)


# Gmail allows 250 quota units a minute per user and a full message read costs 5, so about 50 reads a minute.
_READ_PAUSE = 1.3


def _execute(request: Any, wait: float = 20.0, tries: int = 6) -> Any:
    """Run a Gmail request, waiting and retrying when the per-minute quota is exhausted."""
    from googleapiclient.errors import HttpError

    for _ in range(tries - 1):
        try:
            return request.execute()
        except HttpError as exc:
            if exc.resp.status not in (403, 429) or "rateLimitExceeded" not in str(exc):
                raise
            time.sleep(wait)
    return request.execute()


def fetch_alert_times(
    service: Any,
    query: str,
    max_messages: int = 500,
    *,
    pause: float = _READ_PAUSE,
    on_progress: Callable[[dict[str, str]], object] | None = None,
) -> dict[str, str]:
    """UPI reference -> local ``YYYY-MM-DD HH:MM`` the alert email arrived, for mail matching ``query``.

    Reads are paced to stay under Gmail's quota; ``on_progress`` gets the times found so far every 25 messages,
    so an interrupted run keeps what it has.
    """
    messages = service.users().messages()
    times: dict[str, str] = {}
    seen, token = 0, None
    while seen < max_messages:
        request = messages.list(userId="me", q=query, maxResults=min(100, max_messages - seen), pageToken=token)
        listing = _execute(request)
        for ref in listing.get("messages", []):
            seen += 1
            time.sleep(pause)
            message = _execute(messages.get(userId="me", id=ref["id"], format="full"))
            match = _ALERT_REFERENCE.search(message_text(message.get("payload", {})) or message.get("snippet", ""))
            if match:
                received = datetime.fromtimestamp(int(message["internalDate"]) / 1000).astimezone()
                times[match.group(1)] = received.strftime("%Y-%m-%d %H:%M")
            if on_progress and seen % 25 == 0:
                on_progress(times)
        token = listing.get("nextPageToken")
        if not token or not listing.get("messages"):
            break
    return times


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
        hints: dict[str, dict] = json.loads(Path(path).read_text())
    except FileNotFoundError:
        return {}
    return hints


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
            return str(header.get("value", ""))
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
