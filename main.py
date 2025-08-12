
import json
import os
import click
from typing import Any, NotRequired, Protocol, TypedDict

from google.auth.external_account_authorized_user import (
  Credentials as externalCredentials,
)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as oauth2Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# TypedDicts for better type safety


# Protocol for YouTubeService to match the Google API client
class YouTubePlaylistsResource(Protocol):
  def list(
    self, *, part: str, mine: bool, maxResults: int, pageToken: str | None = None
  ) -> Any: ...


class YouTubeService(Protocol):
  def playlists(self) -> YouTubePlaylistsResource: ...


# TypedDicts for playlist fields


# Required: title, publishedAt; Optional: description
class PlaylistSnippet(TypedDict):
  title: str
  publishedAt: str
  description: NotRequired[str]


# Required: itemCount
class PlaylistContentDetails(TypedDict):
  itemCount: int


# Optional: privacyStatus (accessed with .get)
class PlaylistStatus(TypedDict):
  privacyStatus: NotRequired[str]


class Playlist(TypedDict):
  id: str
  snippet: PlaylistSnippet
  contentDetails: PlaylistContentDetails
  status: PlaylistStatus


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


def _refresh_credentials(creds, token_file: str) -> oauth2Credentials | None:
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


def _save_credentials(creds, token_file: str) -> None:
  """Save credentials to a token file."""
  # creds.to_json() returns a JSON string, so parse it to dict before dumping
  creds_json = creds.to_json()
  if isinstance(creds_json, str):
    creds_json = json.loads(creds_json)
  with open(token_file, "w") as f:
    json.dump(creds_json, f, indent=2)


def authenticate_youtube() -> YouTubeService:
  """Authenticate with YouTube API and return the service object."""
  token_file: str = "youtube.dat"
  creds: oauth2Credentials | externalCredentials | None = _load_credentials(token_file)

  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds = _refresh_credentials(creds, token_file)
    if not creds:
      flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
      creds = flow.run_local_server(port=0)
      _save_credentials(creds, token_file)

  return build("youtube", "v3", credentials=creds)


def get_playlists(
  service: YouTubeService, max_results: int = 50
) -> list[Playlist] | None:
  """Retrieve all playlists for the authenticated user."""
  playlists: list[Playlist] = []
  next_page_token: str | None = None
  try:
    while True:
      request = service.playlists().list(
        part="snippet,contentDetails,status",
        mine=True,
        maxResults=max_results,
        pageToken=next_page_token,
      )
      response = request.execute()

      playlists.extend(response.get("items", []))

      next_page_token = response.get("nextPageToken")
      if not next_page_token:
        break

  except HttpError as error:
    print(f"An HTTP error {error.resp.status} occurred: {error.content}")
    return None

  return playlists


def display_playlists(playlists: list[Playlist]) -> None:
  """Display playlist information in a formatted way."""
  if not playlists:
    print("No playlists found.")
    return

  print(f"\nFound {len(playlists)} playlist(s):")
  print("-" * 80)

  for i, playlist in enumerate(playlists, 1):
    snippet = playlist["snippet"]
    content_details = playlist["contentDetails"]

    print(f"{i}. Title: {snippet['title']}")
    print(f"   ID: {playlist['id']}")
    print(f"   Description: {snippet.get('description', 'No description')[:100]}...")
    print(f"   Video Count: {content_details['itemCount']}")
    print(f"   Created: {snippet['publishedAt']}")
    print(f"   Privacy: {playlist.get('status', {}).get('privacyStatus', 'Unknown')}")
    print("-" * 80)


# --- New functions for single playlist info ---
def get_playlist_info(service: YouTubeService, playlist_id: str) -> Playlist | None:
  """Retrieve information for a single playlist by ID."""
  try:
    request = service.playlists().list(
      part="snippet,contentDetails,status",
      id=playlist_id,
      maxResults=1
    )
    response = request.execute()
    items = response.get("items", [])
    if not items:
      print(f"No playlist found with ID: {playlist_id}")
      return None
    return items[0]
  except HttpError as error:
    print(f"An HTTP error {error.resp.status} occurred: {error.content}")
    return None


def display_playlist_info(playlist: Playlist) -> None:
  """Display information for a single playlist in a formatted way."""
  if not playlist:
    print("No playlist info to display.")
    return
  snippet = playlist["snippet"]
  content_details = playlist["contentDetails"]
  print("\nPlaylist Info:")
  print("-" * 80)
  print(f"Title: {snippet['title']}")
  print(f"ID: {playlist['id']}")
  print(f"Description: {snippet.get('description', 'No description')[:300]}")
  print(f"Video Count: {content_details['itemCount']}")
  print(f"Created: {snippet['publishedAt']}")
  print(f"Privacy: {playlist.get('status', {}).get('privacyStatus', 'Unknown')}")
  print("-" * 80)



# --- CLI using click ---
@click.group()
def cli():
  """YouTube Playlist CLI Tool"""
  pass


@cli.command()
def list():
  """List all playlists for the authenticated user."""
  try:
    print("Authenticating with YouTube API...")
    service: YouTubeService = authenticate_youtube()
    print("Retrieving your playlists...")
    playlists: list[Playlist] | None = get_playlists(service)
    if playlists is not None:
      display_playlists(playlists)
    else:
      print("Failed to retrieve playlists.")
  except Exception as error:
    print(f"An error occurred: {error}")




@cli.command()
@click.argument("playlist_id", required=False)
def info(playlist_id):
  """Show info for a single playlist by ID, or choose from your playlists interactively."""
  try:
    print("Authenticating with YouTube API...")
    service: YouTubeService = authenticate_youtube()
    if not playlist_id:
      print("Retrieving your playlists...")
      playlists = get_playlists(service)
      if not playlists:
        print("No playlists found.")
        return
      # Show a numbered list for selection
      for i, playlist in enumerate(playlists, 1):
        title = playlist["snippet"]["title"]
        pid = playlist["id"]
        print(f"{i}. {title} (ID: {pid})")
      idx = click.prompt(f"Select a playlist [1-{len(playlists)}]", type=int)
      if not (1 <= idx <= len(playlists)):
        print("Invalid selection.")
        return
      playlist_id = playlists[idx - 1]["id"]
    print(f"Retrieving info for playlist: {playlist_id}")
    playlist = get_playlist_info(service, playlist_id)
    if playlist:
      display_playlist_info(playlist)
    else:
      print("Playlist not found or failed to retrieve info.")
  except Exception as error:
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  cli()
