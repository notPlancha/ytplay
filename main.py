import json
import os
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Literal, NotRequired, Protocol, TypedDict, cast

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


# YouTube API Response Types
class YouTubeListResponse(TypedDict):
  kind: str
  etag: str
  nextPageToken: NotRequired[str]
  prevPageToken: NotRequired[str]
  pageInfo: NotRequired[dict[str, int]]
  items: list[dict[str, object]]


class YouTubeInsertResponse(TypedDict):
  kind: str
  etag: str
  id: str


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


class YouTubePlaylistListResponse(TypedDict):
  kind: str
  etag: str
  nextPageToken: NotRequired[str]
  prevPageToken: NotRequired[str]
  pageInfo: NotRequired[dict[str, int]]
  items: list[Playlist]


class YouTubePlaylistItemListResponse(TypedDict):
  kind: str
  etag: str
  nextPageToken: NotRequired[str]
  prevPageToken: NotRequired[str]
  pageInfo: NotRequired[dict[str, int]]
  items: list[PlaylistItem]


class YouTubeVideoListResponse(TypedDict):
  kind: str
  etag: str
  nextPageToken: NotRequired[str]
  prevPageToken: NotRequired[str]
  pageInfo: NotRequired[dict[str, int]]
  items: list[Video]


# Enhanced video type with duration info for internal use
class EnhancedVideo(TypedDict):
  id: str
  snippet: PlaylistItemSnippet
  video_id: str
  duration: str


# Request objects that can be executed
class YouTubeRequest(Protocol):
  def execute(self) -> dict[str, object]: ...


class YouTubePlaylistRequest(Protocol):
  def execute(self) -> YouTubePlaylistListResponse: ...


class YouTubePlaylistItemRequest(Protocol):
  def execute(self) -> YouTubePlaylistItemListResponse: ...


class YouTubeVideoRequest(Protocol):
  def execute(self) -> YouTubeVideoListResponse: ...


class YouTubeInsertRequest(Protocol):
  def execute(self) -> YouTubeInsertResponse: ...


class YouTubeDeleteRequest(Protocol):
  def execute(self) -> dict[str, object]: ...


class YouTubePlaylistsResource(Protocol):
  def list(
    self,
    *,
    part: str,
    mine: bool | None = None,
    id: str | None = None,
    maxResults: int,
    pageToken: str | None = None,
  ) -> YouTubePlaylistRequest: ...
  def insert(self, *, part: str, body: Mapping[str, object]) -> YouTubeInsertRequest: ...
  def delete(self, *, id: str) -> YouTubeDeleteRequest: ...


class YouTubePlaylistItemsResource(Protocol):
  def list(
    self, *, part: str, playlistId: str, maxResults: int, pageToken: str | None = None
  ) -> YouTubePlaylistItemRequest: ...
  def insert(self, *, part: str, body: Mapping[str, object]) -> YouTubeInsertRequest: ...


class YouTubeVideosResource(Protocol):
  def list(self, *, part: str, id: str, maxResults: int | None = None) -> YouTubeVideoRequest: ...


class YouTubeService(Protocol):
  def playlists(self) -> YouTubePlaylistsResource: ...
  def playlistItems(self) -> YouTubePlaylistItemsResource: ...
  def videos(self) -> YouTubeVideosResource: ...


# If modifying these scopes, delete the token file.
SCOPES = ["https://www.googleapis.com/auth/youtube"]

# Type for sorting criteria
type SortCriteria = Literal["upload_date", "duration", "title", "channel", "position"]

# Type for privacy status
type PrivacyStatus = Literal["private", "public", "unlisted"]

# Type for output format
type TextOrJson = Literal["text", "json"]


def parse_duration(duration: str) -> str:
  """Convert ISO 8601 duration (e.g., 'PT4M13S') to readable format (e.g., '4:13')."""
  import re

  # Pattern to match ISO 8601 duration format PT[H]H[M]M[S]S
  pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
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


def get_video_durations(
  service: YouTubeService, video_ids: list[str]
) -> dict[str, str]:
  """Get video durations for a list of video IDs."""
  if not video_ids:
    return {}

  try:
    # YouTube API allows up to 50 video IDs per request
    video_ids_str = ",".join(video_ids)
    request = service.videos().list(
      part="contentDetails", id=video_ids_str, maxResults=50
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


def duration_to_seconds(duration_str: str) -> int:
  """Convert duration string (e.g., '4:13' or '1:04:30') to total seconds."""
  try:
    parts = duration_str.split(":")
    if len(parts) == 2:  # MM:SS
      return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:  # H:MM:SS
      return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    else:
      return 0
  except (ValueError, IndexError):
    return 0


def sort_videos_by_criteria(
  videos: list[EnhancedVideo], sort_by: SortCriteria, reverse: bool = False
) -> list[EnhancedVideo]:
  """Sort videos by different criteria."""
  if not videos:
    return videos

  if sort_by == "upload_date":
    # Sort by video publish date
    def get_publish_date(video: EnhancedVideo) -> datetime:
      try:
        date_str = video["snippet"]["publishedAt"]
        # Parse ISO 8601 date format
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
      except (KeyError, ValueError, TypeError):
        # Return a timezone-aware minimum datetime for invalid/missing dates
        return datetime.min.replace(tzinfo=UTC)

    return sorted(videos, key=get_publish_date, reverse=reverse)

  elif sort_by == "duration":
    # Sort by video duration (requires duration data)
    def get_duration_seconds(video: EnhancedVideo) -> int:
      try:
        duration_str = video.get("duration", "0:00")
        if duration_str == "Unknown":
          return 0
        return duration_to_seconds(duration_str)
      except (KeyError, ValueError):
        return 0

    return sorted(videos, key=get_duration_seconds, reverse=reverse)

  elif sort_by == "title":
    # Sort by video title
    def get_title(video: EnhancedVideo) -> str:
      try:
        return video["snippet"]["title"].lower()
      except KeyError:
        return ""

    return sorted(videos, key=get_title, reverse=reverse)

  elif sort_by == "channel":
    # Sort by channel name
    def get_channel(video: EnhancedVideo) -> str:
      try:
        return (
          video["snippet"]
          .get("videoOwnerChannelTitle", video["snippet"]["channelTitle"])
          .lower()
        )
      except KeyError:
        return ""

    return sorted(videos, key=get_channel, reverse=reverse)

  elif sort_by == "position":
    # Sort by original playlist position
    def get_position(video: EnhancedVideo) -> int:
      try:
        return video["snippet"]["position"]
      except KeyError:
        return 0

    return sorted(videos, key=get_position, reverse=reverse)

  else:
    # Default: return original order
    return videos


def create_playlist(
  youtube: YouTubeService,
  title: str,
  description: str = "",
  privacy_status: PrivacyStatus = "private",
) -> str | None:
  """Create a new YouTube playlist and return its ID."""
  try:
    request_body = {
      "snippet": {"title": title, "description": description},
      "status": {"privacyStatus": privacy_status},
    }

    request = youtube.playlists().insert(part="snippet,status", body=request_body)
    response = request.execute()

    playlist_id = response.get("id")
    print(f"Created playlist: '{title}' (ID: {playlist_id})")
    return playlist_id

  except HttpError as error:
    print(f"Error creating playlist: {error}")
    return None


def delete_playlist(youtube: YouTubeService, playlist_id: str) -> bool:
  """Delete a YouTube playlist by ID."""
  try:
    request = youtube.playlists().delete(id=playlist_id)
    request.execute()
    print(f"Successfully deleted playlist (ID: {playlist_id})")
    return True

  except HttpError as error:
    print(f"Error deleting playlist: {error}")
    return False


def add_video_to_playlist(
  service: YouTubeService, playlist_id: str, video_id: str, position: int | None = None
) -> bool:
  """Add a video to a playlist at a specific position."""
  try:
    request_body = {
      "snippet": {
        "playlistId": playlist_id,
        "resourceId": {"kind": "youtube#video", "videoId": video_id},
      }
    }

    # Add position if specified
    if position is not None:
      request_body["snippet"]["position"] = position

    request = service.playlistItems().insert(part="snippet", body=request_body)
    request.execute()
    return True

  except HttpError as error:
    print(f"Error adding video {video_id} to playlist: {error}")
    return False





def add_videos_to_playlist_sequential(
  service: YouTubeService,
  playlist_id: str,
  video_ids: list[str],
  start_position: int = 0,
  show_progress: bool = True,
) -> tuple[int, int]:
  """Add multiple videos to a playlist using individual requests.

  IMPORTANT: This function stops execution on the first failed video insertion.

  Args:
    service: YouTube service instance
    playlist_id: Target playlist ID
    video_ids: List of video IDs to add
    start_position: Starting position in playlist
    show_progress: Whether to show progress bar

  Returns:
    Tuple of (successful_count, failed_count) - execution stops on first failure
  """
  if not video_ids:
    return 0, 0

  successful_count = 0
  failed_count = 0

  # Initialize progress bar
  pbar = None
  if show_progress:
    pbar = tqdm(
      total=len(video_ids),
      desc="Adding videos",
      unit="videos",
      bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
    )

  for i, video_id in enumerate(video_ids):
    position = start_position + i
    success = add_video_to_playlist(service, playlist_id, video_id, position)

    if success:
      successful_count += 1
    else:
      failed_count += 1
      if pbar:
        pbar.close()
      print(f"\n❌ Stopping execution due to failed video insertion for video: {video_id}")
      print(f"Successfully added {successful_count} videos before failure.")
      return successful_count, failed_count

    if pbar:
      pbar.update(1)

    # Small delay to avoid rate limiting
    time.sleep(0.1)

  if pbar:
    pbar.close()

  return successful_count, failed_count


def create_sorted_playlist(
  service: YouTubeService,
  source_playlist_id: str,
  sort_by: SortCriteria,
  reverse: bool = False,
  new_playlist_title: str | None = None,
  privacy_status: PrivacyStatus = "private",
  show_progress: bool = True,
) -> str | None:
  """Create a new sorted playlist from an existing playlist."""

  # Get the original playlist info
  source_playlist = get_playlist_info(service, source_playlist_id)
  if not source_playlist:
    print(f"Could not find source playlist: {source_playlist_id}")
    return None

  source_title = source_playlist["snippet"]["title"]

  # Determine new playlist title
  if not new_playlist_title:
    sort_desc = "desc" if reverse else "asc"
    new_playlist_title = f"{source_title} (sorted by {sort_by} {sort_desc})"

  # Get videos from source playlist
  if sort_by == "duration":
    # Need duration data for sorting by duration
    print("Fetching videos with durations from source playlist...")
    videos = get_playlist_videos_with_durations(
      service, source_playlist_id, show_progress=show_progress
    )
  else:
    # Regular video data is sufficient
    print("Fetching videos from source playlist...")
    regular_videos = get_playlist_videos(
      service, source_playlist_id, show_progress=show_progress
    )
    if regular_videos:
      # Convert to the enhanced format expected by sorting function
      videos = []
      for video in regular_videos:
        try:
          enhanced_video: EnhancedVideo = {
            "id": video["id"],
            "snippet": video["snippet"],
            "video_id": video["snippet"]["resourceId"]["videoId"],
            "duration": "0:00",  # Default duration for non-duration sorting
          }
          videos.append(enhanced_video)
        except KeyError as e:
          print(f"Warning: Skipping video due to missing key: {e}")
          continue
    else:
      videos = None

  if not videos:
    print("Could not fetch videos from source playlist")
    return None

  print(f"Found {len(videos)} videos to sort")

  # Sort videos
  print(f"Sorting videos by {sort_by} ({'descending' if reverse else 'ascending'})")
  sorted_videos = sort_videos_by_criteria(videos, sort_by, reverse)

  # Create new playlist
  description = f"Sorted copy of '{source_title}' by {sort_by} ({'descending' if reverse else 'ascending'})"
  new_playlist_id = create_playlist(
    service, new_playlist_title, description, privacy_status
  )

  if not new_playlist_id:
    print("Failed to create new playlist")
    return None

  # Add videos to new playlist in sorted order
  print(f"Adding {len(sorted_videos)} videos to new playlist...")

  # Use sequential processing (batch processing is not available)
  video_ids = [video["video_id"] for video in sorted_videos]
  successful_count, failed_count = add_videos_to_playlist_sequential(
    service, new_playlist_id, video_ids, show_progress=show_progress
  )

  if failed_count > 0:
    print("❌ Process terminated due to video insertion failure.")
    print(f"Partial playlist created with {successful_count} videos.")
    return None  # Return None to indicate partial failure
  else:
    print(f"✓ Successfully created sorted playlist: '{new_playlist_title}'")
    print(f"Added all {successful_count} videos successfully")
    print(f"Playlist URL: https://www.youtube.com/playlist?list={new_playlist_id}")

  return new_playlist_id


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


def _refresh_credentials(creds: oauth2Credentials | externalCredentials, token_file: str) -> oauth2Credentials | externalCredentials | None:
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


def _save_credentials(creds: oauth2Credentials | externalCredentials, token_file: str, replace = False) -> None:
  """Save credentials to a token file."""
  # creds.to_json() returns a JSON string, so parse it to dict before dumping
  creds_json = creds.to_json()
  if isinstance(creds_json, str):
    creds_json = json.loads(creds_json)
  if os.path.exists(token_file):
    if not replace:
      raise FileExistsError(f"Token file '{token_file}' already exists. Use replace=True to overwrite.")
    else:
      print(f"Warning: Overwriting existing token file '{token_file}'.")
  with open(token_file, "w") as f:
    json.dump(creds_json, f, indent=2)


def _auth_flow(token_out: str) -> oauth2Credentials | externalCredentials:
  """Create and return an OAuth 2.0 flow object."""
  flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
  creds = flow.run_local_server(port=0)
  return creds


def authenticate_youtube(force: bool = False) -> YouTubeService:
  """Authenticate with YouTube API and return the service object."""
  token_file: str = "youtube.dat"
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
    pbar = tqdm(
      desc="Fetching playlists",
      unit="playlists",
      bar_format="{desc}: {n_fmt} playlists [{elapsed}, {rate_fmt}]",
    )

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
  service: YouTubeService,
  playlist_id: str,
  max_results: int = 50,
  show_progress: bool = True,
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
      playlist_info = (
        service.playlists()
        .list(
          part="contentDetails",
          id=playlist_id,
          maxResults=1,
        )
        .execute()
      )
      items = playlist_info.get("items", [])
      if items:
        total_videos = items[0]["contentDetails"]["itemCount"]
        if total_videos > 0:
          print(f"Fetching {total_videos} videos from playlist...")
          if total_videos > 100:
            estimated_time = (
              total_videos / 50
            ) * 1.5  # Rough estimate: 1.5 seconds per API call
            print(
              f"  (This may take ~{estimated_time:.0f} seconds for large playlists)"
            )
    except HttpError:
      # If we can't get the count, just proceed without it
      pass

  # Initialize progress bar
  pbar = None
  if show_progress:
    if total_videos:
      pbar = tqdm(
        total=total_videos,
        desc="Fetching videos",
        unit="videos ",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
      )
    else:
      pbar = tqdm(
        desc="Fetching videos",
        unit="videos ",
        bar_format="{desc}: {n_fmt} videos [{elapsed}, {rate_fmt}]",
      )

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

  return videos


def get_playlist_videos_with_durations(
  service: YouTubeService,
  playlist_id: str,
  max_results: int = 50,
  show_progress: bool = True,
) -> list[EnhancedVideo] | None:
  """Retrieve all videos from a playlist with duration information."""
  videos: list[EnhancedVideo] = []
  next_page_token: str | None = None
  page_count = 0
  start_time = time.time()

  # First, get the total count of videos in the playlist to show better progress
  total_videos = None
  if show_progress:
    try:
      playlist_info = (
        service.playlists()
        .list(
          part="contentDetails",
          id=playlist_id,
          maxResults=1,
        )
        .execute()
      )
      items = playlist_info.get("items", [])
      if items:
        total_videos = items[0]["contentDetails"]["itemCount"]
        if total_videos > 0:
          print(f"Fetching {total_videos} videos with durations from playlist...")
          if total_videos > 100:
            estimated_time = (
              total_videos / 50
            ) * 2  # Slightly longer estimate due to extra API calls
            print(
              f"  (This may take ~{estimated_time:.0f} seconds for large playlists)"
            )
    except HttpError:
      # If we can't get the count, just proceed without it
      pass

  # Initialize progress bar
  pbar = None
  if show_progress:
    if total_videos:
      pbar = tqdm(
        total=total_videos,
        desc="Fetching videos+durations",
        unit="videos",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
      )
    else:
      pbar = tqdm(
        desc="Fetching videos+durations",
        unit="videos",
        bar_format="{desc}: {n_fmt} videos [{elapsed}, {rate_fmt}]",
      )

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
        enhanced_video: EnhancedVideo = {
          "id": video["id"],
          "snippet": video["snippet"],
          "duration": durations.get(video_id, "Unknown"),
          "video_id": video_id,  # Add this for convenience
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
    print(
      f"   Channel: {snippet.get('videoOwnerChannelTitle', snippet['channelTitle'])}"
    )
    print(f"   Position: {snippet['position']}")
    print(f"   Published: {snippet['publishedAt']}")
    print(f"   URL: https://www.youtube.com/watch?v={video_id}")
    if description := snippet.get("description"):
      desc = description[:100]
      print(f"   Description: {desc}{'...' if len(description) > 100 else ''}")
    print("-" * 80)


def display_playlist_videos_with_durations(videos: list[EnhancedVideo]) -> None:
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
    print(
      f"   Channel: {snippet.get('videoOwnerChannelTitle', snippet['channelTitle'])}"
    )
    print(f"   Duration: {duration}")
    print(f"   Position: {snippet['position']}")
    print(f"   Published: {snippet['publishedAt']}")
    print(f"   URL: https://www.youtube.com/watch?v={video_id}")
    if description := snippet.get("description"):
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
          total_duration_seconds += (
            int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
          )
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


def display_playlist_videos_with_durations_to_file(
  videos: list[EnhancedVideo], filename: str
) -> None:
  """Save playlist videos with durations to a file."""
  with open(filename, "w", encoding="utf-8") as f:
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
      f.write(
        f"   Channel: {snippet.get('videoOwnerChannelTitle', snippet['channelTitle'])}\n"
      )
      f.write(f"   Duration: {duration}\n")
      f.write(f"   Position: {snippet['position']}\n")
      f.write(f"   Published: {snippet['publishedAt']}\n")
      f.write(f"   URL: https://www.youtube.com/watch?v={video_id}\n")
      if description := snippet.get("description"):
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
            total_duration_seconds += (
              int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            )
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
  with open(filename, "w", encoding="utf-8") as f:
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
      f.write(
        f"   Description: {snippet.get('description', 'No description')[:100]}...\n"
      )
      f.write(f"   Video Count: {content_details['itemCount']}\n")
      f.write(f"   Created: {snippet['publishedAt']}\n")
      f.write(
        f"   Privacy: {playlist.get('status', {}).get('privacyStatus', 'Unknown')}\n"
      )
      f.write("-" * 80 + "\n")


def display_playlist_info_to_file(playlist: Playlist, filename: str) -> None:
  """Save playlist information to a file."""
  with open(filename, "w", encoding="utf-8") as f:
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
  with open(filename, "w", encoding="utf-8") as f:
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
      f.write(
        f"   Channel: {snippet.get('videoOwnerChannelTitle', snippet['channelTitle'])}\n"
      )
      f.write(f"   Position: {snippet['position']}\n")
      f.write(f"   Published: {snippet['publishedAt']}\n")
      f.write(f"   URL: https://www.youtube.com/watch?v={video_id}\n")
      if description := snippet.get("description"):
        desc = description[:100]
        f.write(f"   Description: {desc}{'...' if len(description) > 100 else ''}\n")
      f.write("-" * 80 + "\n")


def save_playlists_json(playlists: list[Playlist], filename: str) -> None:
  """Save playlists to a JSON file."""
  with open(filename, "w", encoding="utf-8") as f:
    json.dump(playlists, f, indent=2, ensure_ascii=False)


def save_playlist_info_json(playlist: Playlist, filename: str) -> None:
  """Save playlist info to a JSON file."""
  with open(filename, "w", encoding="utf-8") as f:
    json.dump(playlist, f, indent=2, ensure_ascii=False)


def save_playlist_videos_json(videos: list[PlaylistItem], filename: str) -> None:
  """Save playlist videos to a JSON file."""
  with open(filename, "w", encoding="utf-8") as f:
    json.dump(videos, f, indent=2, ensure_ascii=False)


# --- CLI using click ---
@click.group()
def cli() -> None:
  """YouTube Playlist CLI Tool

  Available commands:
  - login: --force (Force reauthentication by removing existing credentials)
  - list-playlists: Show your YouTube playlists
    Flags: --output/-o (Output to file), --format/-f (text/json format)
  - playlist-summary: Get summary info for a playlist
    Flags: --output/-o (Output to file), --format/-f (text/json format)
  - list-videos: List all videos in a playlist
    Flags: --output/-o (Output to file), --format/-f (text/json format), --no-progress (Disable progress tracking)
  - list-videos-with-durations: List videos with duration information
    Flags: --output/-o (Output to file), --format/-f (text/json format), --no-progress (Disable progress tracking)
  - create-sorted-playlist: Create a sorted copy of an existing playlist
    Flags: --sort-by/-s (upload_date/duration/title/channel/position, or interactive selection if omitted), --reverse/-r (Sort descending),
           --title/-t (Custom playlist title), --privacy/-p (private/public/unlisted),
           --no-progress (Disable progress tracking)
  - delete-playlist: Delete a playlist
    Flags: --force (Skip confirmation prompt)
  """
  pass


@cli.command()
@click.option(
  "--force",
  is_flag=True,
  help="Force reauthentication by removing existing credentials",
)
def login(force: bool) -> None:
  """Authenticate with YouTube and store credentials."""
  try:
    token_file = "youtube.dat"
    if os.path.exists(token_file):
      print(f"🔑 Found existing credentials at: {token_file}")
      service = authenticate_youtube(force=force)
      if not force: # Check if existing credentials are valid
        print("🔍 Checking existing YouTube API credentials...")
        playlists = get_playlists(service, max_results=1)
        if playlists is not None:
          print("✅ Authentication verified! Using cached credentials.")
        else:
          print("❌ Authentication failed or no access to playlists.")
    else:
      print("🔑 Starting YouTube API authentication flow...")
      service = authenticate_youtube()

  except Exception as error:
    print(f"❌ An error occurred during authentication: {error}")


@cli.command()
@click.option("--output", "-o", type=click.Path(), help="Output results to a file")
@click.option(
  "--format",
  "-f",
  type=click.Choice(["text", "json"], case_sensitive=False),
  default="text",
  help="Output format (text or json)",
)
def list_playlists(output: str | None, format: TextOrJson) -> None:
  """List all playlists for the authenticated user."""
  try:
    service: YouTubeService = authenticate_youtube()
    print("Retrieving your playlists...")
    playlists: list[Playlist] | None = get_playlists(service)
    if playlists is not None:
      if output:
        if format == "json":
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
@click.option("--output", "-o", type=click.Path(), help="Output results to a file")
@click.option(
  "--format",
  "-f",
  type=click.Choice(["text", "json"], case_sensitive=False),
  default="text",
  help="Output format (text or json)",
)
def playlist_summary(playlist_id: str | None, output: str | None, format: TextOrJson) -> None:
  """Show info for a single playlist by ID, or choose from your playlists interactively."""
  try:
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
    assert playlist_id is not None  # We ensure this above
    playlist = get_playlist_info(service, playlist_id)
    if playlist:
      if output:
        if format == "json":
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
@click.option("--output", "-o", type=click.Path(), help="Output results to a file")
@click.option(
  "--format",
  "-f",
  type=click.Choice(["text", "json"], case_sensitive=False),
  default="text",
  help="Output format (text or json)",
)
@click.option("--no-progress", is_flag=True, help="Disable progress tracking")
def list_videos(playlist_id: str | None, output: str | None, format: TextOrJson, no_progress: bool) -> None:
  """List all videos in a playlist by ID, or choose from your playlists interactively."""
  try:
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
    assert playlist_id is not None  # We ensure this above
    videos = get_playlist_videos(service, playlist_id, show_progress=not no_progress)
    if videos is not None:
      if output:
        if format == "json":
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
@click.option("--output", "-o", type=click.Path(), help="Output results to a file")
@click.option(
  "--format",
  "-f",
  type=click.Choice(["text", "json"], case_sensitive=False),
  default="text",
  help="Output format (text or json)",
)
@click.option("--no-progress", is_flag=True, help="Disable progress tracking")
def list_videos_with_durations(playlist_id: str | None, output: str | None, format: TextOrJson, no_progress: bool) -> None:
  """List all videos in a playlist with duration information."""
  try:
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
    assert playlist_id is not None  # We ensure this above
    videos = get_playlist_videos_with_durations(
      service, playlist_id, show_progress=not no_progress
    )
    if videos is not None:
      if output:
        if format == "json":
          with open(output, "w", encoding="utf-8") as f:
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


@cli.command()
@click.argument("playlist_id", required=False)
@click.option(
  "--sort-by",
  "-s",
  type=click.Choice(
    ["upload_date", "duration", "title", "channel", "position"], case_sensitive=False
  ),
  help="Sort criteria: upload_date, duration, title, channel, or position (if omitted, you'll be prompted to choose interactively)",
)
@click.option("--reverse", "-r", is_flag=True, help="Sort in descending order")
@click.option("--title", "-t", help="Title for the new sorted playlist")
@click.option(
  "--privacy",
  "-p",
  type=click.Choice(["private", "public", "unlisted"], case_sensitive=False),
  default="private",
  help="Privacy setting for the new playlist",
)
@click.option("--no-progress", is_flag=True, help="Disable progress tracking")
def create_sorted_playlist_cmd(
  playlist_id: str | None, sort_by: str | None, reverse: bool, title: str | None, privacy: str, no_progress: bool
) -> None:
  """Create a new sorted playlist from an existing playlist."""
  try:
    # Convert string parameters to literal types
    privacy_status = cast(PrivacyStatus, privacy)  # Click ensures this matches the choice constraint

    service: YouTubeService = authenticate_youtube()

    if not playlist_id:
      print("Retrieving your playlists...")
      playlists = get_playlists(service)
      if not playlists:
        print("No playlists found.")
        return

      # Show a numbered list for selection
      print("\nSelect a playlist to sort:")
      for i, playlist in enumerate(playlists, 1):
        title_text = playlist["snippet"]["title"]
        pid = playlist["id"]
        video_count = playlist["contentDetails"]["itemCount"]
        print(f"{i}. {title_text} ({video_count} videos) (ID: {pid})")

      idx = click.prompt(f"Select a playlist [1-{len(playlists)}]", type=int)
      if not (1 <= idx <= len(playlists)):
        print("Invalid selection.")
        return
      playlist_id = playlists[idx - 1]["id"]

    # Interactive sorting method selection if not provided
    if not sort_by:
      print("\nSelect sorting method:")
      sorting_options = [
        ("upload_date", "Sort by upload/publish date"),
        ("duration", "Sort by video duration"),
        ("title", "Sort by video title (alphabetical)"),
        ("channel", "Sort by channel name (alphabetical)"),
        ("position", "Sort by original playlist position"),
      ]

      for i, (key, description) in enumerate(sorting_options, 1):
        print(f"{i}. {description}")

      sort_idx = click.prompt(f"Select sorting method [1-{len(sorting_options)}]", type=int)
      if not (1 <= sort_idx <= len(sorting_options)):
        print("Invalid selection.")
        return
      sort_by = sorting_options[sort_idx - 1][0]

    sort_criteria = cast(SortCriteria, sort_by)  # Click/selection ensures this is valid

    print("\nCreating sorted playlist...")
    print(f"Sort by: {sort_criteria}")
    print(f"Order: {'Descending' if reverse else 'Ascending'}")
    print(f"Privacy: {privacy_status}")

    assert playlist_id is not None  # We ensured this is not None above
    new_playlist_id = create_sorted_playlist(
      service=service,
      source_playlist_id=playlist_id,
      sort_by=sort_criteria,
      reverse=reverse,
      new_playlist_title=title,
      privacy_status=privacy_status,
      show_progress=not no_progress,
    )

    if new_playlist_id:
      print("\n✓ Successfully created sorted playlist!")
      print(f"New playlist ID: {new_playlist_id}")
    else:
      print("\n❌ Failed to create sorted playlist or process was terminated due to errors.")

  except Exception as error:
    print(f"An error occurred: {error}")


@cli.command()
@click.argument("playlist_id", required=False)
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
def delete_playlist_cmd(playlist_id: str | None, force: bool) -> None:
  """Delete a playlist by ID, or choose from your playlists interactively."""
  try:
    service: YouTubeService = authenticate_youtube()

    if not playlist_id:
      print("Retrieving your playlists...")
      playlists = get_playlists(service)
      if not playlists:
        print("No playlists found.")
        return

      # Show a numbered list for selection
      print("\nSelect a playlist to delete:")
      for i, playlist in enumerate(playlists, 1):
        title_text = playlist["snippet"]["title"]
        pid = playlist["id"]
        video_count = playlist["contentDetails"]["itemCount"]
        privacy = playlist.get("status", {}).get("privacyStatus", "Unknown")
        print(f"{i}. {title_text} ({video_count} videos, {privacy}) (ID: {pid})")

      idx = click.prompt(f"Select a playlist [1-{len(playlists)}]", type=int)
      if not (1 <= idx <= len(playlists)):
        print("Invalid selection.")
        return

      selected_playlist = playlists[idx - 1]
      playlist_id = selected_playlist["id"]
      playlist_title = selected_playlist["snippet"]["title"]
    else:
      # Get playlist info for confirmation
      playlist_info = get_playlist_info(service, playlist_id)
      if not playlist_info:
        print(f"Playlist with ID {playlist_id} not found.")
        return
      playlist_title = playlist_info["snippet"]["title"]

    # Confirmation prompt
    if not force:
      print("\n⚠️ WARNING: You are about to delete the playlist:")
      print(f"   Title: {playlist_title}")
      print(f"   ID: {playlist_id}")
      print("\n   This action cannot be undone!")

      if not click.confirm("Are you sure you want to delete this playlist?"):
        print("Deletion cancelled.")
        return

    print(f"\nDeleting playlist: '{playlist_title}'...")
    assert playlist_id is not None  # We ensured this is not None above
    success = delete_playlist(service, playlist_id)

    if success:
      print("✓ Playlist deleted successfully!")
    else:
      print("❌ Failed to delete playlist.")

  except Exception as error:
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  cli()
