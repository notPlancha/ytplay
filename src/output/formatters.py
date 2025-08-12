"""Output functions for displaying and saving playlist/video information."""

import json

from ..types.youtube import EnhancedVideo, Playlist, PlaylistItem


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


# File output functions
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


# JSON save functions
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
