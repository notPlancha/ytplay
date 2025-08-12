import json
import os
import time
from typing import Any, NotRequired, Protocol, TypedDict

import click
from google.auth.external_account_authorized_user import (
  Credentials as externalCredentials,
)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as oauth2Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tqdm import tqdm


class YouTubePlaylistsResource(Protocol):
  def list(
    self, *, part: str, mine: bool | None = None, id: str | None = None, maxResults: int, pageToken: str | None = None
  ) -> Any: ...


class YouTubePlaylistItemsResource(Protocol):
  def list(
    self, *, part: str, playlistId: str, maxResults: int, pageToken: str | None = None
  ) -> Any: ...


class YouTubeVideosResource(Protocol):
  def list(
    self, *, part: str, id: str, maxResults: int | None = None
  ) -> Any: ...


class YouTubeService(Protocol):
  def playlists(self) -> YouTubePlaylistsResource: ...
  def playlistItems(self) -> YouTubePlaylistItemsResource: ...
  def videos(self) -> YouTubeVideosResource: ...


class PlaylistSnippet(TypedDict):
  title: str
  publishedAt: str
  description: NotRequired[str]


class PlaylistContentDetails(TypedDict):
  itemCount: int

class PlaylistStatus(TypedDict):
  privacyStatus: NotRequired[str]

class Playlist(TypedDict):
  id: str
  snippet: PlaylistSnippet
  contentDetails: PlaylistContentDetails
  status: PlaylistStatus


class VideoSnippet(TypedDict):
  title: str
  description: NotRequired[str]
  publishedAt: str
  channelTitle: str
  videoOwnerChannelTitle: NotRequired[str]
  position: int


class VideoResourceId(TypedDict):
  kind: str
  videoId: str


class PlaylistItemSnippet(TypedDict):
  publishedAt: str
  channelId: str
  title: str
  description: NotRequired[str]
  channelTitle: str
  playlistId: str
  position: int
  resourceId: VideoResourceId
  videoOwnerChannelTitle: NotRequired[str]
  videoOwnerChannelId: NotRequired[str]


class PlaylistItem(TypedDict):
  id: str
  snippet: PlaylistItemSnippet


class VideoContentDetails(TypedDict):
  duration: str  # ISO 8601 duration format (e.g., "PT4M13S")
  definition: NotRequired[str]
  caption: NotRequired[str]


class Video(TypedDict):
  id: str
  snippet: PlaylistItemSnippet  # Reusing the snippet structure
  contentDetails: VideoContentDetails


# If modifying these scopes, delete the token file.
SCOPES = ["https://www.googleapis.com/auth/youtube"]


def parse_duration(duration: str) -> str:
  """Convert ISO 8601 duration (e.g., 'PT4M13S') to readable format (e.g., '4:13')."""
  import re

  # Pattern to match ISO 8601 duration format PT[H]H[M]M[S]S
  pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
  match = re.match(pattern, duration)

  if not match:
    return duration  # Return original if parsing fails

  hours, minutes, seconds = match.groups()
  hours = int(hours) if hours else 0
  minutes = int(minutes) if minutes else 0
  seconds = int(seconds) if seconds else 0

  if hours > 0:
    return f"{hours}:{minutes:02d}:{seconds:02d}"
  else:
    return f"{minutes}:{seconds:02d}"


def get_video_durations(service: YouTubeService, video_ids: list[str]) -> dict[str, str]:
  """Get video durations for a list of video IDs."""
  if not video_ids:
    return {}

  try:
    # YouTube API allows up to 50 video IDs per request
    video_ids_str = ",".join(video_ids)
    request = service.videos().list(
      part="contentDetails",
      id=video_ids_str,
      maxResults=50
    )
    response = request.execute()

    durations = {}
    for item in response.get("items", []):
      video_id = item["id"]
      duration_iso = item["contentDetails"]["duration"]
      durations[video_id] = parse_duration(duration_iso)

    return durations
  except HttpError as error:
    print(f"Error fetching video durations: {error}")
    return {}


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
  service: YouTubeService, max_results: int = 50, show_progress: bool = False
) -> list[Playlist] | None:
  """Retrieve all playlists for the authenticated user."""
  playlists: list[Playlist] = []
  next_page_token: str | None = None
  page_count = 0

  # Initialize progress bar for playlists if requested
  pbar = None
  if show_progress:
    pbar = tqdm(desc="Fetching playlists", unit="playlists",
                bar_format="{desc}: {n_fmt} playlists [{elapsed}, {rate_fmt}]")

  try:
    while True:
      page_count += 1
      request = service.playlists().list(
        part="snippet,contentDetails,status",
        mine=True,
        maxResults=max_results,
        pageToken=next_page_token,
      )
      response = request.execute()

      new_playlists = response.get("items", [])
      playlists.extend(new_playlists)

      if pbar:
        pbar.update(len(new_playlists))

      next_page_token = response.get("nextPageToken")
      if not next_page_token:
        break

    if pbar:
      pbar.set_description(f"✓ Found {len(playlists)} playlists")
      pbar.close()

  except HttpError as error:
    if pbar:
      pbar.set_description("✗ Error occurred")
      pbar.close()
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


def get_playlist_info(service: YouTubeService, playlist_id: str) -> Playlist | None:
  """Retrieve information for a single playlist by ID."""
  try:
    request = service.playlists().list(
      part="snippet,contentDetails,status",
      id=playlist_id,
      maxResults=1,
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


def get_playlist_videos(
  service: YouTubeService, playlist_id: str, max_results: int = 50, show_progress: bool = True
) -> list[PlaylistItem] | None:
  """Retrieve all videos from a playlist."""
  videos: list[PlaylistItem] = []
  next_page_token: str | None = None
  page_count = 0
  start_time = time.time()

  # First, get the total count of videos in the playlist to show better progress
  total_videos = None
  if show_progress:
    try:
      playlist_info = service.playlists().list(
        part="contentDetails",
        id=playlist_id,
        maxResults=1,
      ).execute()
      items = playlist_info.get("items", [])
      if items:
        total_videos = items[0]["contentDetails"]["itemCount"]
        if total_videos > 0:
          print(f"Fetching {total_videos} videos from playlist...")
          if total_videos > 100:
            estimated_time = (total_videos / 50) * 1.5  # Rough estimate: 1.5 seconds per API call
            print(f"  (This may take ~{estimated_time:.0f} seconds for large playlists)")
    except HttpError:
      # If we can't get the count, just proceed without it
      pass

  # Initialize progress bar
  pbar = None
  if show_progress:
    if total_videos:
      pbar = tqdm(total=total_videos, desc="Fetching videos", unit="videos ",
                  bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]")
    else:
      pbar = tqdm(desc="Fetching videos", unit="videos ",
                  bar_format="{desc}: {n_fmt} videos [{elapsed}, {rate_fmt}]")

  try:
    while True:
      page_count += 1

      request = service.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=max_results,
        pageToken=next_page_token,
      )
      response = request.execute()

      new_videos = response.get("items", [])
      videos.extend(new_videos)

      # Update progress bar
      if pbar:
        pbar.update(len(new_videos))

      next_page_token = response.get("nextPageToken")
      if not next_page_token:
        break

    if pbar:
      elapsed = time.time() - start_time
      pbar.set_description(f"✓ Completed ({page_count} pages, {elapsed:.1f}s)")
      pbar.close()

  except HttpError as error:
    if pbar:
      pbar.set_description("✗ Error occurred")
      pbar.close()
    print(f"An HTTP error {error.resp.status} occurred: {error.content}")
    return None

def get_playlist_videos_with_durations(
  service: YouTubeService, playlist_id: str, max_results: int = 50, show_progress: bool = True
) -> list[dict[str, Any]] | None:
  """Retrieve all videos from a playlist with duration information."""
  videos: list[dict[str, Any]] = []
  next_page_token: str | None = None
  page_count = 0
  start_time = time.time()

  # First, get the total count of videos in the playlist to show better progress
  total_videos = None
  if show_progress:
    try:
      playlist_info = service.playlists().list(
        part="contentDetails",
        id=playlist_id,
        maxResults=1,
      ).execute()
      items = playlist_info.get("items", [])
      if items:
        total_videos = items[0]["contentDetails"]["itemCount"]
        if total_videos > 0:
          print(f"Fetching {total_videos} videos with durations from playlist...")
          if total_videos > 100:
            estimated_time = (total_videos / 50) * 2  # Slightly longer estimate due to extra API calls
            print(f"  (This may take ~{estimated_time:.0f} seconds for large playlists)")
    except HttpError:
      # If we can't get the count, just proceed without it
      pass

  # Initialize progress bar
  pbar = None
  if show_progress:
    if total_videos:
      pbar = tqdm(total=total_videos, desc="Fetching videos+durations", unit="videos",
                  bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]")
    else:
      pbar = tqdm(desc="Fetching videos+durations", unit="videos",
                  bar_format="{desc}: {n_fmt} videos [{elapsed}, {rate_fmt}]")

  try:
    while True:
      page_count += 1

      request = service.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=max_results,
        pageToken=next_page_token,
      )
      response = request.execute()

      new_videos = response.get("items", [])

      # Extract video IDs for duration lookup
      video_ids = [video["snippet"]["resourceId"]["videoId"] for video in new_videos]

      # Get durations for this batch of videos
      durations = get_video_durations(service, video_ids)

      # Combine playlist item data with duration information
      for video in new_videos:
        video_id = video["snippet"]["resourceId"]["videoId"]
        enhanced_video = {
          "id": video["id"],
          "snippet": video["snippet"],
          "duration": durations.get(video_id, "Unknown"),
          "video_id": video_id  # Add this for convenience
        }
        videos.append(enhanced_video)

      # Update progress bar
      if pbar:
        pbar.update(len(new_videos))

      next_page_token = response.get("nextPageToken")
      if not next_page_token:
        break

    if pbar:
      elapsed = time.time() - start_time
      pbar.set_description(f"✓ Completed ({page_count} pages, {elapsed:.1f}s)")
      pbar.close()

  except HttpError as error:
    if pbar:
      pbar.set_description("✗ Error occurred")
      pbar.close()
    print(f"An HTTP error {error.resp.status} occurred: {error.content}")
    return None

  return videos


def display_playlist_videos(videos: list[PlaylistItem]) -> None:
  """Display playlist videos in a formatted way."""
  if not videos:
    print("No videos found in this playlist.")
    return

  print(f"\nFound {len(videos)} video(s) in playlist:")
  print("-" * 80)

  for i, video in enumerate(videos, 1):
    snippet = video["snippet"]
    video_id = snippet["resourceId"]["videoId"]

    print(f"{i}. Title: {snippet['title']}")
    print(f"   Video ID: {video_id}")
    print(f"   Channel: {snippet.get('videoOwnerChannelTitle', snippet['channelTitle'])}")
    print(f"   Position: {snippet['position']}")
    print(f"   Published: {snippet['publishedAt']}")
    print(f"   URL: https://www.youtube.com/watch?v={video_id}")
    if description := snippet.get('description'):
      desc = description[:100]
      print(f"   Description: {desc}{'...' if len(description) > 100 else ''}")
    print("-" * 80)


def display_playlist_videos_with_durations(videos: list[dict[str, Any]]) -> None:
  """Display playlist videos with duration information in a formatted way."""
  if not videos:
    print("No videos found in this playlist.")
    return

  print(f"\nFound {len(videos)} video(s) in playlist:")
  print("-" * 90)

  total_duration_seconds = 0
  for i, video in enumerate(videos, 1):
    snippet = video["snippet"]
    video_id = video["video_id"]
    duration = video["duration"]

    print(f"{i}. Title: {snippet['title']}")
    print(f"   Video ID: {video_id}")
    print(f"   Channel: {snippet.get('videoOwnerChannelTitle', snippet['channelTitle'])}")
    print(f"   Duration: {duration}")
    print(f"   Position: {snippet['position']}")
    print(f"   Published: {snippet['publishedAt']}")
    print(f"   URL: https://www.youtube.com/watch?v={video_id}")
    if description := snippet.get('description'):
      desc = description[:100]
      print(f"   Description: {desc}{'...' if len(description) > 100 else ''}")
    print("-" * 90)

    # Try to calculate total duration (simple parsing for MM:SS format)
    if duration != "Unknown" and ":" in duration:
      try:
        parts = duration.split(":")
        if len(parts) == 2:  # MM:SS
          total_duration_seconds += int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:  # HH:MM:SS
          total_duration_seconds += int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
      except ValueError:
        pass  # Skip if parsing fails

  # Display total duration
  if total_duration_seconds > 0:
    hours = total_duration_seconds // 3600
    minutes = (total_duration_seconds % 3600) // 60
    seconds = total_duration_seconds % 60
    if hours > 0:
      total_duration = f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
      total_duration = f"{minutes}:{seconds:02d}"
    print(f"\nTotal playlist duration: {total_duration}")


def display_playlist_videos_with_durations_to_file(videos: list[dict[str, Any]], filename: str) -> None:
  """Save playlist videos with durations to a file."""
  with open(filename, 'w', encoding='utf-8') as f:
    if not videos:
      f.write("No videos found in this playlist.\n")
      return

    f.write(f"Found {len(videos)} video(s) in playlist:\n")
    f.write("-" * 90 + "\n")

    total_duration_seconds = 0
    for i, video in enumerate(videos, 1):
      snippet = video["snippet"]
      video_id = video["video_id"]
      duration = video["duration"]

      f.write(f"{i}. Title: {snippet['title']}\n")
      f.write(f"   Video ID: {video_id}\n")
      f.write(f"   Channel: {snippet.get('videoOwnerChannelTitle', snippet['channelTitle'])}\n")
      f.write(f"   Duration: {duration}\n")
      f.write(f"   Position: {snippet['position']}\n")
      f.write(f"   Published: {snippet['publishedAt']}\n")
      f.write(f"   URL: https://www.youtube.com/watch?v={video_id}\n")
      if description := snippet.get('description'):
        desc = description[:100]
        f.write(f"   Description: {desc}{'...' if len(description) > 100 else ''}\n")
      f.write("-" * 90 + "\n")

      # Calculate total duration
      if duration != "Unknown" and ":" in duration:
        try:
          parts = duration.split(":")
          if len(parts) == 2:  # MM:SS
            total_duration_seconds += int(parts[0]) * 60 + int(parts[1])
          elif len(parts) == 3:  # HH:MM:SS
            total_duration_seconds += int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except ValueError:
          pass

    # Display total duration
    if total_duration_seconds > 0:
      hours = total_duration_seconds // 3600
      minutes = (total_duration_seconds % 3600) // 60
      seconds = total_duration_seconds % 60
      if hours > 0:
        total_duration = f"{hours}:{minutes:02d}:{seconds:02d}"
      else:
        total_duration = f"{minutes}:{seconds:02d}"
      f.write(f"\nTotal playlist duration: {total_duration}\n")


def display_playlists_to_file(playlists: list[Playlist], filename: str) -> None:
  """Save playlist information to a file."""
  with open(filename, 'w', encoding='utf-8') as f:
    if not playlists:
      f.write("No playlists found.\n")
      return

    f.write(f"Found {len(playlists)} playlist(s):\n")
    f.write("-" * 80 + "\n")

    for i, playlist in enumerate(playlists, 1):
      snippet = playlist["snippet"]
      content_details = playlist["contentDetails"]

      f.write(f"{i}. Title: {snippet['title']}\n")
      f.write(f"   ID: {playlist['id']}\n")
      f.write(f"   Description: {snippet.get('description', 'No description')[:100]}...\n")
      f.write(f"   Video Count: {content_details['itemCount']}\n")
      f.write(f"   Created: {snippet['publishedAt']}\n")
      f.write(f"   Privacy: {playlist.get('status', {}).get('privacyStatus', 'Unknown')}\n")
      f.write("-" * 80 + "\n")


def display_playlist_info_to_file(playlist: Playlist, filename: str) -> None:
  """Save playlist information to a file."""
  with open(filename, 'w', encoding='utf-8') as f:
    if not playlist:
      f.write("No playlist info to display.\n")
      return
    snippet = playlist["snippet"]
    content_details = playlist["contentDetails"]
    f.write("Playlist Info:\n")
    f.write("-" * 80 + "\n")
    f.write(f"Title: {snippet['title']}\n")
    f.write(f"ID: {playlist['id']}\n")
    f.write(f"Description: {snippet.get('description', 'No description')[:300]}\n")
    f.write(f"Video Count: {content_details['itemCount']}\n")
    f.write(f"Created: {snippet['publishedAt']}\n")
    f.write(f"Privacy: {playlist.get('status', {}).get('privacyStatus', 'Unknown')}\n")
    f.write("-" * 80 + "\n")


def display_playlist_videos_to_file(videos: list[PlaylistItem], filename: str) -> None:
  """Save playlist videos information to a file."""
  with open(filename, 'w', encoding='utf-8') as f:
    if not videos:
      f.write("No videos found in this playlist.\n")
      return

    f.write(f"Found {len(videos)} video(s) in playlist:\n")
    f.write("-" * 80 + "\n")

    for i, video in enumerate(videos, 1):
      snippet = video["snippet"]
      video_id = snippet["resourceId"]["videoId"]

      f.write(f"{i}. Title: {snippet['title']}\n")
      f.write(f"   Video ID: {video_id}\n")
      f.write(f"   Channel: {snippet.get('videoOwnerChannelTitle', snippet['channelTitle'])}\n")
      f.write(f"   Position: {snippet['position']}\n")
      f.write(f"   Published: {snippet['publishedAt']}\n")
      f.write(f"   URL: https://www.youtube.com/watch?v={video_id}\n")
      if description := snippet.get('description'):
        desc = description[:100]
        f.write(f"   Description: {desc}{'...' if len(description) > 100 else ''}\n")
      f.write("-" * 80 + "\n")


def save_playlists_json(playlists: list[Playlist], filename: str) -> None:
  """Save playlists to a JSON file."""
  with open(filename, 'w', encoding='utf-8') as f:
    json.dump(playlists, f, indent=2, ensure_ascii=False)


def save_playlist_info_json(playlist: Playlist, filename: str) -> None:
  """Save playlist info to a JSON file."""
  with open(filename, 'w', encoding='utf-8') as f:
    json.dump(playlist, f, indent=2, ensure_ascii=False)


def save_playlist_videos_json(videos: list[PlaylistItem], filename: str) -> None:
  """Save playlist videos to a JSON file."""
  with open(filename, 'w', encoding='utf-8') as f:
    json.dump(videos, f, indent=2, ensure_ascii=False)



# --- CLI using click ---
@click.group()
def cli():
  """YouTube Playlist CLI Tool
  
  Available commands:
  - auth: Authenticate with YouTube API
  - list-playlists: Show your YouTube playlists
  - playlist-summary: Get summary info for a playlist
  - list-videos: List all videos in a playlist
  - list-videos-with-durations: List videos with duration information
  """
  pass


@cli.command()
@click.option('--force', is_flag=True, help='Force reauthentication by removing existing credentials')
def auth(force):
  """Authenticate with YouTube and store credentials."""
  try:
    if force:
      token_file = "youtube.dat"
      if os.path.exists(token_file):
        os.remove(token_file)
        print("Existing credentials removed. Forcing reauthentication...")

    print("Starting authentication flow...")
    service = authenticate_youtube()
    # Try a simple API call to verify authentication
    playlists = get_playlists(service, max_results=1)
    if playlists is not None:
      print("Authentication successful! Credentials saved.")
    else:
      print("Authentication failed or no access to playlists.")
  except Exception as error:
    print(f"An error occurred during authentication: {error}")


@cli.command()
@click.option('--output', '-o', type=click.Path(), help='Output results to a file')
@click.option('--format', '-f', type=click.Choice(['text', 'json'], case_sensitive=False), default='text', help='Output format (text or json)')
def list_playlists(output, format):
  """List all playlists for the authenticated user."""
  try:
    print("Authenticating with YouTube API...")
    service: YouTubeService = authenticate_youtube()
    print("Retrieving your playlists...")
    playlists: list[Playlist] | None = get_playlists(service)
    if playlists is not None:
      if output:
        if format.lower() == 'json':
          save_playlists_json(playlists, output)
        else:
          display_playlists_to_file(playlists, output)
        print(f"Playlist information saved to: {output}")
      else:
        display_playlists(playlists)
    else:
      print("Failed to retrieve playlists.")
  except Exception as error:
    print(f"An error occurred: {error}")




@cli.command()
@click.argument("playlist_id", required=False)
@click.option('--output', '-o', type=click.Path(), help='Output results to a file')
@click.option('--format', '-f', type=click.Choice(['text', 'json'], case_sensitive=False), default='text', help='Output format (text or json)')
def playlist_summary(playlist_id, output, format):
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
      if output:
        if format.lower() == 'json':
          save_playlist_info_json(playlist, output)
        else:
          display_playlist_info_to_file(playlist, output)
        print(f"Playlist summary saved to: {output}")
      else:
        display_playlist_info(playlist)
    else:
      print("Playlist not found or failed to retrieve info.")
  except Exception as error:
    print(f"An error occurred: {error}")


@cli.command()
@click.argument("playlist_id", required=False)
@click.option('--output', '-o', type=click.Path(), help='Output results to a file')
@click.option('--format', '-f', type=click.Choice(['text', 'json'], case_sensitive=False), default='text', help='Output format (text or json)')
@click.option('--no-progress', is_flag=True, help='Disable progress tracking')
def list_videos(playlist_id, output, format, no_progress):
  """List all videos in a playlist by ID, or choose from your playlists interactively."""
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
        video_count = playlist["contentDetails"]["itemCount"]
        print(f"{i}. {title} ({video_count} videos) (ID: {pid})")
      idx = click.prompt(f"Select a playlist [1-{len(playlists)}]", type=int)
      if not (1 <= idx <= len(playlists)):
        print("Invalid selection.")
        return
      playlist_id = playlists[idx - 1]["id"]
    print(f"Retrieving videos for playlist: {playlist_id}")
    videos = get_playlist_videos(service, playlist_id, show_progress=not no_progress)
    if videos is not None:
      if output:
        if format.lower() == 'json':
          save_playlist_videos_json(videos, output)
        else:
          display_playlist_videos_to_file(videos, output)
        print(f"Playlist videos saved to: {output}")
      else:
        display_playlist_videos(videos)
    else:
      print("Failed to retrieve playlist videos.")
  except Exception as error:
    print(f"An error occurred: {error}")


@cli.command()
@click.argument("playlist_id", required=False)
@click.option('--output', '-o', type=click.Path(), help='Output results to a file')
@click.option('--format', '-f', type=click.Choice(['text', 'json'], case_sensitive=False), default='text', help='Output format (text or json)')
@click.option('--no-progress', is_flag=True, help='Disable progress tracking')
def list_videos_with_durations(playlist_id, output, format, no_progress):
  """List all videos in a playlist with duration information."""
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
        video_count = playlist["contentDetails"]["itemCount"]
        print(f"{i}. {title} ({video_count} videos) (ID: {pid})")
      idx = click.prompt(f"Select a playlist [1-{len(playlists)}]", type=int)
      if not (1 <= idx <= len(playlists)):
        print("Invalid selection.")
        return
      playlist_id = playlists[idx - 1]["id"]
    print(f"Retrieving videos with durations for playlist: {playlist_id}")
    videos = get_playlist_videos_with_durations(service, playlist_id, show_progress=not no_progress)
    if videos is not None:
      if output:
        if format.lower() == 'json':
          with open(output, 'w', encoding='utf-8') as f:
            json.dump(videos, f, indent=2, ensure_ascii=False)
        else:
          display_playlist_videos_with_durations_to_file(videos, output)
        print(f"Playlist videos with durations saved to: {output}")
      else:
        display_playlist_videos_with_durations(videos)
    else:
      print("Failed to retrieve playlist videos.")
  except Exception as error:
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  cli()
