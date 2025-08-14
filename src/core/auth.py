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
    return oauth2Credentials.from_authorized_user_file(token_file, SCOPES)
  return None


def _refresh_credentials(
  creds: oauth2Credentials | externalCredentials, token_file: str
) -> oauth2Credentials | externalCredentials:
  """Refresh credentials if possible and save them."""
  try:
    creds.refresh(Request())
    _save_credentials(creds, token_file, replace=True)
    return creds
  except Exception as e:
    print(f"Error refreshing token: {e}")
    raise


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
      print(f"⚠️Warning: Overwriting existing token file '{token_file}'.")
  with open(token_file, "w") as f:
    json.dump(creds_json, f, indent=2)


def _auth_flow(token_out: str) -> oauth2Credentials | externalCredentials:
  """Create and return an OAuth 2.0 flow object."""
  flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
  creds = flow.run_local_server(port=0)
  return creds


def check_valid_credentials() -> bool:
  """Check if valid credentials exist without triggering authentication."""
  creds: oauth2Credentials | externalCredentials | None = _load_credentials(TOKEN_FILE)

  if not creds:
    return False

  if creds.valid:
    return True

  # Try to refresh if we have a refresh token
  if creds.expired and creds.refresh_token:
    service = refresh_expired_credentials(creds)
    return service is not None

  return False


def get_youtube_service_if_authenticated() -> YouTubeService | None:
  """Get YouTube service if valid credentials exist, otherwise return None."""
  creds: oauth2Credentials | externalCredentials | None = _load_credentials(TOKEN_FILE)

  if not creds:
    return None

  if creds.valid:
    return use_existing_credentials(creds)

  # Try to refresh if we have a refresh token
  if creds.expired and creds.refresh_token:
    return refresh_expired_credentials(creds)

  return None


def create_fresh_authentication() -> YouTubeService:
  """Create fresh authentication by running OAuth flow."""
  token_file: str = TOKEN_FILE
  creds = _auth_flow(token_file)
  _save_credentials(creds, token_file, replace=True)
  return build("youtube", "v3", credentials=creds)


def use_existing_credentials(
  creds: oauth2Credentials | externalCredentials,
) -> YouTubeService:
  """Use existing valid credentials to create YouTube service."""
  return build("youtube", "v3", credentials=creds)


def refresh_expired_credentials(
  creds: oauth2Credentials | externalCredentials,
) -> YouTubeService | None:
  """Try to refresh expired credentials. Returns None if refresh fails."""
  token_file: str = TOKEN_FILE
  try:
    refreshed_creds = _refresh_credentials(creds, token_file)
    _save_credentials(refreshed_creds, token_file, replace=True)
    return build("youtube", "v3", credentials=refreshed_creds)
  except Exception:
    return None


def force_reauthentication() -> YouTubeService:
  """Force a complete re-authentication by running fresh OAuth flow."""
  return create_fresh_authentication()


def authenticate_youtube(force: bool = False) -> YouTubeService:
  """Authenticate with YouTube API and return the service object."""
  # Force re-authentication if requested
  if force:
    return force_reauthentication()

  # Load existing credentials
  creds = _load_credentials(TOKEN_FILE)

  # No credentials found - start fresh authentication
  if creds is None:
    return create_fresh_authentication()

  # Valid credentials found - use them
  if creds.valid:
    return use_existing_credentials(creds)

  # Expired credentials - try to refresh
  if creds.expired and creds.refresh_token:
    service = refresh_expired_credentials(creds)
    if service is not None:
      return service

  # Fallback - start fresh authentication
  return create_fresh_authentication()
