"""Video sorting utilities."""

import re
from datetime import UTC, datetime

from googleapiclient.errors import HttpError

from ..types.youtube import EnhancedVideo, SortCriteria, YouTubeService


def parse_duration(duration: str) -> str:
  """Convert ISO 8601 duration (e.g., 'PT4M13S') to readable format (e.g., '4:13')."""
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
