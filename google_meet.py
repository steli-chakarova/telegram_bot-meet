"""Create Google Meet links (OPEN access — anyone with the link can join)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Meet space with accessType OPEN = join without "ask to join"
SCOPES = ["https://www.googleapis.com/auth/meetings.space.created"]
BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"


def _credentials_from_env_or_file() -> dict | None:
    raw = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
    if raw:
        return json.loads(raw)
    if CREDENTIALS_FILE.exists():
        return json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
    return None


def _token_from_env_or_file() -> dict | None:
    raw = os.getenv("GOOGLE_TOKEN_JSON", "").strip()
    if raw:
        return json.loads(raw)
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    return None


def _save_token(creds: Credentials) -> None:
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")


def _has_required_scopes(creds: Credentials) -> bool:
    granted = set(creds.scopes or [])
    return set(SCOPES).issubset(granted)


def get_credentials() -> Credentials:
    creds: Credentials | None = None
    token_data = _token_from_env_or_file()
    if token_data:
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        if not os.getenv("GOOGLE_TOKEN_JSON"):
            _save_token(creds)

    if not creds or not creds.valid or not _has_required_scopes(creds):
        client_config = _credentials_from_env_or_file()
        if not client_config:
            raise FileNotFoundError(
                "Missing Google credentials. Put credentials.json in the project "
                "folder or set GOOGLE_CREDENTIALS_JSON."
            )
        if os.getenv("GOOGLE_TOKEN_JSON"):
            raise RuntimeError(
                "Google token is missing Meet scope. Re-authorize locally "
                "(auth_google.py), then update GOOGLE_TOKEN_JSON on Railway."
            )
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent")
        _save_token(creds)

    return creds


def create_meet_link(title: str = "Telegram Meet") -> str:
    """Create a Meet space anyone with the link can join (no knock)."""
    creds = get_credentials()
    service = build("meet", "v2", credentials=creds, cache_discovery=False)

    space = (
        service.spaces()
        .create(
            body={
                "config": {
                    "accessType": "OPEN",
                    "entryPointAccess": "ALL",
                }
            }
        )
        .execute()
    )

    link = space.get("meetingUri")
    if not link:
        raise RuntimeError("Meet API created a space but returned no meetingUri.")

    return link
