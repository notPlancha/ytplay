"""YouTube API functions for playlists and videos."""

import time
from typing import Literal

from googleapiclient.errors import HttpError
from tqdm import tqdm

from ..types.youtube import (
  EnhancedVideo,
  Playlist,
  PlaylistItem,
  PrivacyStatus,
  SortCriteria,
  YouTubeService,
)
from .cache import get_cached_data, save_cached_data
from .sorting import get_video_durations, sort_videos_by_criteria


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
) -> tuple[
  bool, Literal["success", "unavailable", "permission", "quota_exceeded", "other"]
]:
  """Add a video to a playlist at a specific position.

  Returns:
    Tuple of (success: bool, error_type: str)
    error_type can be: 'success', 'unavailable', 'permission', 'quota_exceeded', 'other'
  """
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
    return True, "success"

  except HttpError as error:
    # Parse error details to determine the type of error
    try:
      error_details = error.error_details[0] if error.error_details else {}
      error_reason = (
        error_details.get("reason", "") if isinstance(error_details, dict) else ""
      )
    except (AttributeError, IndexError):
      error_reason = ""

    if error_reason == "failedPrecondition" or error.resp.status == 404:
      # This typically means the video is private, deleted, or unavailable
      return False, "unavailable"
    elif error.resp.status == 403:
      # Permission denied
      # check if it's a quota issue or permission error
      if "quotaExceeded" in error_reason:
        return False, "quota_exceeded"
      return False, "permission"

    else:
      print(f"Error adding video {video_id} to playlist: {error}")
      return False, "other"


def add_videos_to_playlist_sequential(
  service: YouTubeService,
  playlist_id: str,
  video_ids: list[str],
  start_position: int = 0,
  show_progress: bool = True,
) -> tuple[int, int, int]:
  """Add multiple videos to a playlist using individual requests.

  This function now continues processing even when videos fail to be added,
  specifically handling unavailable/private videos gracefully.

  Args:
      service: YouTube service instance
      playlist_id: Target playlist ID
      video_ids: List of video IDs to add
      start_position: Starting position in playlist
      show_progress: Whether to show progress bar

  Returns:
      Tuple of (successful_count, unavailable_count, other_failures_count)
  """
  if not video_ids:
    return 0, 0, 0

  successful_count = 0
  unavailable_count = 0
  other_failures_count = 0
  unavailable_videos = []

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
    position = start_position + successful_count  # Adjust position for skipped videos
    success, error_type = add_video_to_playlist(
      service, playlist_id, video_id, position
    )

    if success:
      successful_count += 1
    elif error_type == "unavailable":
      unavailable_count += 1
      unavailable_videos.append(video_id)
    # quota
    elif error_type == "quota_exceeded":
      print("❌ Quota exceeded, try again tomorrow")
      if pbar:
        pbar.close()
      break
    else:
      other_failures_count += 1
      if other_failures_count > 5:  # Stop if too many non-unavailable errors occur
        if pbar:
          pbar.close()
        print(
          "\n❌ Stopping execution due to too many serious errors (non-unavailable failures)"
        )
        break

    if pbar:
      pbar.update(1)

    # Small delay to avoid rate limiting
    time.sleep(0.1)

  if pbar:
    pbar.close()

  # Report skipped videos
  if unavailable_videos:
    print(f"\n⚠️  Skipped {unavailable_count} unavailable/private video(s):")
    for video_id in unavailable_videos:
      print(f"   - https://www.youtube.com/watch?v={video_id}")

  return successful_count, unavailable_count, other_failures_count


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


def get_playlist_videos(
  service: YouTubeService,
  playlist_id: str,
  max_results: int = 50,
  show_progress: bool = True,
  use_cache: bool = True,
) -> list[PlaylistItem] | None:
  """Retrieve all videos from a playlist."""

  # Check cache first if enabled
  if use_cache:
    cached_videos = get_cached_data("videos", playlist_id)
    if cached_videos is not None:
      if show_progress:
        print(f"✓ Loaded {len(cached_videos)} videos from cache")
      return cached_videos

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

    # Save to cache if enabled
    if use_cache and videos:
      if save_cached_data("videos", playlist_id, videos):
        if show_progress:
          print(f"✓ Cached {len(videos)} videos for future use")

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
  use_cache: bool = True,
) -> list[EnhancedVideo] | None:
  """Retrieve all videos from a playlist with duration information."""

  # Check cache first if enabled
  if use_cache:
    cached_videos = get_cached_data("videos_durations", playlist_id)
    if cached_videos is not None:
      if show_progress:
        print(f"✓ Loaded {len(cached_videos)} videos with durations from cache")
      return cached_videos

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

    # Save to cache if enabled
    if use_cache and videos:
      if save_cached_data("videos_durations", playlist_id, videos):
        if show_progress:
          print(f"✓ Cached {len(videos)} videos with durations for future use")

  except HttpError as error:
    if pbar:
      pbar.set_description("✗ Error occurred")
      pbar.close()
    print(f"An HTTP error {error.resp.status} occurred: {error.content}")
    return None

  return videos


def create_sorted_playlist(
  service: YouTubeService,
  source_playlist_id: str,
  sort_by: SortCriteria,
  reverse: bool = False,
  new_playlist_title: str | None = None,
  privacy_status: PrivacyStatus = "private",
  show_progress: bool = True,
  use_cache: bool = True,
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
      service, source_playlist_id, show_progress=show_progress, use_cache=use_cache
    )
  else:
    # Regular video data is sufficient
    print("Fetching videos from source playlist...")
    regular_videos = get_playlist_videos(
      service, source_playlist_id, show_progress=show_progress, use_cache=use_cache
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
  description = (
    f"Sorted copy of '{source_title}' by {sort_by} "
    f"({'descending' if reverse else 'ascending'})"
  )
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
  successful_count, unavailable_count, other_failures_count = (
    add_videos_to_playlist_sequential(
      service, new_playlist_id, video_ids, show_progress=show_progress
    )
  )

  total_processed = successful_count + unavailable_count + other_failures_count

  if other_failures_count > 0:
    print(
      f"⚠️  Encountered {other_failures_count} serious error(s) during playlist creation."
    )
    if other_failures_count > 5:
      print("❌ Process terminated due to too many serious errors.")
      print(f"Partial playlist created with {successful_count} videos.")
      return None  # Return None to indicate partial failure

  if successful_count == 0:
    print("❌ No videos were successfully added to the playlist.")
    return None

  success_message = f"✓ Successfully created sorted playlist: '{new_playlist_title}'"
  if unavailable_count > 0:
    success_message += f"\nAdded {successful_count} videos successfully, skipped {unavailable_count} unavailable video(s)"
  else:
    success_message += f"\nAdded all {successful_count} videos successfully"

  print(success_message)
  print(f"Playlist URL: https://www.youtube.com/playlist?list={new_playlist_id}")

  return new_playlist_id
