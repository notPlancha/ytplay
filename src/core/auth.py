"""YouTube API authentication utilities."""

import json
import os

from google.auth.external_account_authorized_user import (
  Credentials as externalCredentials,
)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as oauth2Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ..config import CLIENT_SECRETS_FILE, TOKEN_FILE
from ..types.youtube import YouTubeService

# If modifying these scopes, delete the token file.
SCOPES = ["https://www.googleapis.com/auth/youtube"]


def _load_credentials(
  token_file: str,
) -> oauth2Credentials | externalCredentials | None:
  """Load credentials from a token file if it exists."""
  if os.path.exists(token_file):
    with open(token_file) as f:
      token_data: dict[str, object] = json.load(f)
    return oauth2Credentials(
      token=token_data.get("access_token"),
      refresh_token=token_data.get("refresh_token"),
      token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
      client_id=token_data.get("client_id"),
      client_secret=token_data.get("client_secret"),
      scopes=SCOPES,
    )
  return None


def _refresh_credentials(
  creds: oauth2Credentials | externalCredentials, token_file: str
) -> oauth2Credentials | externalCredentials | None:
  """Refresh credentials if possible and save them."""
  try:
    creds.refresh(Request())
    with open(token_file) as f:
      existing_data: dict[str, object] = json.load(f)
    existing_data["access_token"] = creds.token
    if hasattr(creds, "expiry") and creds.expiry:
      existing_data["token_expiry"] = creds.expiry.isoformat() + "Z"
    with open(token_file, "w") as f:
      json.dump(existing_data, f, indent=2)
    return creds
  except Exception as e:
    print(f"Error refreshing token: {e}")
    return None


def _save_credentials(
  creds: oauth2Credentials | externalCredentials, token_file: str, replace: bool = False
) -> None:
  """Save credentials to a token file."""
  # creds.to_json() returns a JSON string, so parse it to dict before dumping
  creds_json = creds.to_json()
  if isinstance(creds_json, str):
    creds_json = json.loads(creds_json)
  if os.path.exists(token_file):
    if not replace:
      raise FileExistsError(
        f"Token file '{token_file}' already exists. Use replace=True to overwrite."
      )
    else:
      print(f"Warning: Overwriting existing token file '{token_file}'.")
  with open(token_file, "w") as f:
    json.dump(creds_json, f, indent=2)


def _auth_flow(token_out: str) -> oauth2Credentials | externalCredentials:
  """Create and return an OAuth 2.0 flow object."""
  flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
  creds = flow.run_local_server(port=0)
  return creds


def authenticate_youtube(force: bool = False) -> YouTubeService:
  """Authenticate with YouTube API and return the service object."""
  token_file: str = TOKEN_FILE
  creds: oauth2Credentials | externalCredentials | None = _load_credentials(token_file)

  # If there are no (valid) credentials available, let the user log in.
  if force:
    print("Forcing re-authentication...")
    creds = _auth_flow(token_file)
    _save_credentials(creds, token_file, replace=True)

  elif not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      print("Refreshing expired YouTube API credentials...")
      creds = _refresh_credentials(creds, token_file)
    if not creds:
      print("No valid credentials found. Starting fresh authentication flow...")
      creds = _auth_flow(token_file)

  else:
    print("Using cached YouTube API credentials...")

  return build("youtube", "v3", credentials=creds)
