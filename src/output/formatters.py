"""Output functions for displaying and saving playlist/video information."""

import json

import click

from ..types.youtube import EnhancedVideo, Playlist, PlaylistItem


def display_playlists(playlists: list[Playlist]) -> None:
  """Display playlist information in a formatted way."""
  if not playlists:
    click.echo("No playlists found.")
    return

  click.echo(
    f"\nFound {click.style(str(len(playlists)), fg='cyan', bold=True)} playlist(s):"
  )
  click.echo("-" * 80)

  for i, playlist in enumerate(playlists, 1):
    snippet = playlist["snippet"]
    content_details = playlist["contentDetails"]
    privacy_status = playlist.get("status", {}).get("privacyStatus", "Unknown")
    video_count = content_details["itemCount"]

    # Color the privacy status
    if privacy_status == "private":
      privacy_color = "red"
    elif privacy_status == "public":
      privacy_color = "green"
    elif privacy_status == "unlisted":
      privacy_color = "yellow"
    else:
      privacy_color = "white"

    click.echo(
      f"{click.style(f'{i}.', fg='blue', bold=True)} Title: {click.style(snippet['title'], fg='white', bold=True)}"
    )
    click.echo(f"   ID: {click.style(playlist['id'], fg='cyan')}")
    click.echo(
      f"   Description: {snippet.get('description', 'No description')[:100]}..."
    )
    click.echo(
      f"   Video Count: {click.style(str(video_count), fg='magenta', bold=True)}"
    )
    click.echo(f"   Created: {click.style(snippet['publishedAt'], fg='blue')}")
    click.echo(
      f"   Privacy: {click.style(privacy_status, fg=privacy_color, bold=True)}"
    )
    click.echo("-" * 80)


def display_playlist_info(playlist: Playlist) -> None:
  """Display information for a single playlist in a formatted way."""
  if not playlist:
    click.echo("No playlist info to display.")
    return
  snippet = playlist["snippet"]
  content_details = playlist["contentDetails"]
  privacy_status = playlist.get("status", {}).get("privacyStatus", "Unknown")
  video_count = content_details["itemCount"]

  # Color the privacy status
  if privacy_status == "private":
    privacy_color = "red"
  elif privacy_status == "public":
    privacy_color = "green"
  elif privacy_status == "unlisted":
    privacy_color = "yellow"
  else:
    privacy_color = "white"

  click.echo(f"\n{click.style('Playlist Info:', fg='cyan', bold=True)}")
  click.echo("-" * 80)
  click.echo(f"Title: {click.style(snippet['title'], fg='white', bold=True)}")
  click.echo(f"ID: {click.style(playlist['id'], fg='cyan')}")
  click.echo(f"Description: {snippet.get('description', 'No description')[:300]}")
  click.echo(f"Video Count: {click.style(str(video_count), fg='magenta', bold=True)}")
  click.echo(f"Created: {click.style(snippet['publishedAt'], fg='blue')}")
  click.echo(f"Privacy: {click.style(privacy_status, fg=privacy_color, bold=True)}")
  click.echo("-" * 80)


def display_playlist_videos(videos: list[PlaylistItem]) -> None:
  """Display playlist videos in a formatted way."""
  if not videos:
    click.echo("No videos found in this playlist.")
    return

  click.echo(
    f"\nFound {click.style(str(len(videos)), fg='cyan', bold=True)} video(s) in playlist:"
  )
  click.echo("-" * 80)

  for i, video in enumerate(videos, 1):
    snippet = video["snippet"]
    video_id = snippet["resourceId"]["videoId"]

    click.echo(
      f"{click.style(f'{i}.', fg='blue', bold=True)} Title: {click.style(snippet['title'], fg='white', bold=True)}"
    )
    click.echo(f"   Video ID: {click.style(video_id, fg='cyan')}")
    click.echo(
      f"   Channel: {click.style(snippet.get('videoOwnerChannelTitle', snippet['channelTitle']), fg='yellow')}"
    )
    click.echo(f"   Position: {click.style(str(snippet['position']), fg='magenta')}")
    click.echo(f"   Published: {click.style(snippet['publishedAt'], fg='blue')}")
    click.echo(
      f"   URL: {click.style(f'https://www.youtube.com/watch?v={video_id}', fg='cyan', underline=True)}"
    )
    if description := snippet.get("description"):
      desc = description[:100]
      click.echo(f"   Description: {desc}{'...' if len(description) > 100 else ''}")
    click.echo("-" * 80)


def display_playlist_videos_with_durations(videos: list[EnhancedVideo]) -> None:
  """Display playlist videos with duration information in a formatted way."""
  if not videos:
    click.echo("No videos found in this playlist.")
    return

  click.echo(
    f"\nFound {click.style(str(len(videos)), fg='cyan', bold=True)} video(s) in playlist:"
  )
  click.echo("-" * 90)

  total_duration_seconds = 0
  for i, video in enumerate(videos, 1):
    snippet = video["snippet"]
    video_id = video["video_id"]
    duration = video["duration"]

    # Color duration based on length
    if duration != "Unknown" and ":" in duration:
      try:
        parts = duration.split(":")
        duration_seconds = 0
        if len(parts) == 2:  # MM:SS
          duration_seconds = int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:  # HH:MM:SS
          duration_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])

        # Color based on duration length
        if duration_seconds < 60:  # Less than 1 minute
          duration_color = "red"
        elif duration_seconds < 600:  # Less than 10 minutes
          duration_color = "yellow"
        elif duration_seconds < 3600:  # Less than 1 hour
          duration_color = "green"
        else:  # 1 hour or more
          duration_color = "cyan"
      except ValueError:
        duration_color = "white"
    else:
      duration_color = "white"

    click.echo(
      f"{click.style(f'{i}.', fg='blue', bold=True)} Title: {click.style(snippet['title'], fg='white', bold=True)}"
    )
    click.echo(f"   Video ID: {click.style(video_id, fg='cyan')}")
    click.echo(
      f"   Channel: {click.style(snippet.get('videoOwnerChannelTitle', snippet['channelTitle']), fg='yellow')}"
    )
    click.echo(f"   Duration: {click.style(duration, fg=duration_color, bold=True)}")
    click.echo(f"   Position: {click.style(str(snippet['position']), fg='magenta')}")
    click.echo(f"   Published: {click.style(snippet['publishedAt'], fg='blue')}")
    click.echo(
      f"   URL: {click.style(f'https://www.youtube.com/watch?v={video_id}', fg='cyan', underline=True)}"
    )
    if description := snippet.get("description"):
      desc = description[:100]
      click.echo(f"   Description: {desc}{'...' if len(description) > 100 else ''}")
    click.echo("-" * 90)

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
    click.echo(
      f"\n{click.style('Total playlist duration:', fg='green', bold=True)} {click.style(total_duration, fg='green', bold=True)}"
    )


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
