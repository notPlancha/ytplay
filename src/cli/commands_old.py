"""CLI commands for the YouTube Playlist Tool."""

import json
import os
from typing import cast

import click

from ..config import TOKEN_FILE
from ..core.auth import authenticate_youtube
from ..core.cache import clear_cache, format_cache_size, get_cache_stats
from ..core.youtube_api import (
  create_sorted_playlist,
  delete_playlist,
  get_playlist_info,
  get_playlist_videos,
  get_playlist_videos_with_durations,
  get_playlists,
)
from ..output.formatters import (
  display_playlist_info,
  display_playlist_info_to_file,
  display_playlist_videos,
  display_playlist_videos_to_file,
  display_playlist_videos_with_durations,
  display_playlist_videos_with_durations_to_file,
  display_playlists,
  display_playlists_to_file,
  save_playlist_info_json,
  save_playlist_videos_json,
  save_playlists_json,
)
from ..types.youtube import (
  Playlist,
  PrivacyStatus,
  SortCriteria,
  TextOrJson,
  YouTubeService,
)


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
    Flags: --output/-o (Output to file), --format/-f (text/json format), --no-progress (Disable progress tracking), --no-cache (Skip cache and fetch fresh data)
  - list-videos-with-durations: List videos with duration information
    Flags: --output/-o (Output to file), --format/-f (text/json format), --no-progress (Disable progress tracking), --no-cache (Skip cache and fetch fresh data)
  - create-sorted-playlist: Create a sorted copy of an existing playlist
    Flags: --sort-by/-s (upload_date/duration/title/channel/position, or interactive selection if omitted), --reverse/-r (Sort descending),
           --title/-t (Custom playlist title), --privacy/-p (private/public/unlisted),
           --no-progress (Disable progress tracking), --no-cache (Skip cache and fetch fresh data)
  - delete-playlist: Delete a playlist
    Flags: --force (Skip confirmation prompt)
  - cache-info: Show cache statistics
  - clear-cache: Clear cached playlist data
    Flags: --type/-t (Specific cache type to clear: playlist/videos/videos_durations)
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
    token_file = TOKEN_FILE
    if os.path.exists(token_file):
      print(f"🔑 Found existing credentials at: {token_file}")
      service = authenticate_youtube(force=force)
      if not force:  # Check if existing credentials are valid
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
def playlist_summary(
  playlist_id: str | None, output: str | None, format: TextOrJson
) -> None:
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
@click.option("--no-cache", is_flag=True, help="Skip cache and fetch fresh data")
def list_videos(
  playlist_id: str | None,
  output: str | None,
  format: TextOrJson,
  no_progress: bool,
  no_cache: bool,
) -> None:
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
    videos = get_playlist_videos(
      service, playlist_id, show_progress=not no_progress, use_cache=not no_cache
    )
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
@click.option("--no-cache", is_flag=True, help="Skip cache and fetch fresh data")
def list_videos_with_durations(
  playlist_id: str | None,
  output: str | None,
  format: TextOrJson,
  no_progress: bool,
  no_cache: bool,
) -> None:
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
      service, playlist_id, show_progress=not no_progress, use_cache=not no_cache
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
@click.option("--no-cache", is_flag=True, help="Skip cache and fetch fresh data")
def create_sorted_playlist_cmd(
  playlist_id: str | None,
  sort_by: str | None,
  reverse: bool,
  title: str | None,
  privacy: str,
  no_progress: bool,
  no_cache: bool,
) -> None:
  """Create a new sorted playlist from an existing playlist."""
  try:
    # Convert string parameters to literal types
    privacy_status = cast(
      PrivacyStatus, privacy
    )  # Click ensures this matches the choice constraint

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

      sort_idx = click.prompt(
        f"Select sorting method [1-{len(sorting_options)}]", type=int
      )
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
      use_cache=not no_cache,
    )

    if new_playlist_id:
      print("\n✓ Successfully created sorted playlist!")
      print(f"New playlist ID: {new_playlist_id}")
    else:
      print(
        "\n❌ Failed to create sorted playlist or process was terminated due to errors."
      )

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


@cli.command()
def cache_info() -> None:
  """Show cache statistics."""
  try:
    stats = get_cache_stats()
    total_size = format_cache_size(stats["total_size_bytes"])

    print("📊 Cache Statistics:")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Total size: {total_size}")
    print(f"  Playlist data: {stats['playlist']} files")
    print(f"  Video lists: {stats['videos']} files")
    print(f"  Videos with durations: {stats['videos_durations']} files")

    if stats["total_files"] == 0:
      print("  (Cache is empty)")

  except Exception as error:
    print(f"An error occurred: {error}")


@cli.command()
@click.option(
  "--type",
  "-t",
  type=click.Choice(["playlist", "videos", "videos_durations"], case_sensitive=False),
  help="Specific cache type to clear (if omitted, clears all cache)",
)
def clear_cache_cmd(type: str | None) -> None:
  """Clear cached playlist data."""
  try:
    # Get stats before clearing
    stats_before = get_cache_stats()

    if stats_before["total_files"] == 0:
      print("Cache is already empty.")
      return

    # Clear the cache
    removed_count = clear_cache(type)

    if removed_count > 0:
      if type:
        print(f"✓ Cleared {removed_count} {type} cache files.")
      else:
        print(f"✓ Cleared all {removed_count} cache files.")
    else:
      print("No cache files were removed.")

  except Exception as error:
    print(f"An error occurred: {error}")
