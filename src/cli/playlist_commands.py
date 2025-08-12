"""Playlist management commands."""

import json
from typing import cast

import click

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
  PrivacyStatus,
  SortCriteria,
  TextOrJson,
)
from .common import (
  add_options,
  cache_options,
  confirm_action,
  get_authenticated_service,
  handle_playlist_id_or_select,
  output_options,
)


@click.group()
def playlist() -> None:
  """Playlist management commands."""
  pass


@playlist.command()
@add_options(output_options)
def list(output: str | None, format: TextOrJson) -> None:
  """List all your playlists."""
  try:
    service = get_authenticated_service()
    click.echo("Retrieving your playlists...")

    playlists = get_playlists(service)
    if playlists is not None:
      if output:
        if format == "json":
          save_playlists_json(playlists, output)
        else:
          display_playlists_to_file(playlists, output)
        click.echo(f"✅ Playlist information saved to: {output}")
      else:
        display_playlists(playlists)
    else:
      click.echo("❌ Failed to retrieve playlists.", err=True)

  except Exception as error:
    click.echo(f"❌ An error occurred: {error}", err=True)


@playlist.command()
@click.argument("playlist_id", required=False)
@add_options(output_options)
def info(playlist_id: str | None, output: str | None, format: TextOrJson) -> None:
  """Show detailed information for a playlist."""
  try:
    service = get_authenticated_service()
    playlist_id = handle_playlist_id_or_select(service, playlist_id, "get info for")

    click.echo(f"Retrieving info for playlist: {playlist_id}")
    playlist_info = get_playlist_info(service, playlist_id)

    if playlist_info:
      if output:
        if format == "json":
          save_playlist_info_json(playlist_info, output)
        else:
          display_playlist_info_to_file(playlist_info, output)
        click.echo(f"✅ Playlist summary saved to: {output}")
      else:
        display_playlist_info(playlist_info)
    else:
      click.echo("❌ Playlist not found or failed to retrieve info.", err=True)

  except Exception as error:
    click.echo(f"❌ An error occurred: {error}", err=True)


@playlist.command()
@click.argument("playlist_id", required=False)
@click.option(
  "--durations", "-d", is_flag=True, help="Include video duration information"
)
@add_options(output_options)
@add_options(cache_options)
def videos(
  playlist_id: str | None,
  durations: bool,
  output: str | None,
  format: TextOrJson,
  no_progress: bool,
  no_cache: bool,
) -> None:
  """List all videos in a playlist."""
  try:
    service = get_authenticated_service()
    playlist_id = handle_playlist_id_or_select(service, playlist_id, "list videos from")

    if durations:
      click.echo(f"Retrieving videos with durations for playlist: {playlist_id}")
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
          click.echo(f"✅ Playlist videos with durations saved to: {output}")
        else:
          display_playlist_videos_with_durations(videos)
      else:
        click.echo("❌ Failed to retrieve playlist videos.", err=True)
    else:
      click.echo(f"Retrieving videos for playlist: {playlist_id}")
      videos = get_playlist_videos(
        service, playlist_id, show_progress=not no_progress, use_cache=not no_cache
      )

      if videos is not None:
        if output:
          if format == "json":
            save_playlist_videos_json(videos, output)
          else:
            display_playlist_videos_to_file(videos, output)
          click.echo(f"✅ Playlist videos saved to: {output}")
        else:
          display_playlist_videos(videos)
      else:
        click.echo("❌ Failed to retrieve playlist videos.", err=True)

  except Exception as error:
    click.echo(f"❌ An error occurred: {error}", err=True)


@playlist.command()
@click.argument("playlist_id", required=False)
@click.option(
  "--sort-by",
  "-s",
  type=click.Choice(
    ["upload_date", "duration", "title", "channel", "position"], case_sensitive=False
  ),
  help="Sort criteria (if omitted, you'll be prompted to choose)",
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
@add_options(cache_options)
def sort(
  playlist_id: str | None,
  sort_by: str | None,
  reverse: bool,
  title: str | None,
  privacy: str,
  no_progress: bool,
  no_cache: bool,
) -> None:
  """Create a sorted copy of an existing playlist."""
  try:
    service = get_authenticated_service()
    playlist_id = handle_playlist_id_or_select(service, playlist_id, "sort")

    # Convert string parameters to literal types
    privacy_status = cast(PrivacyStatus, privacy)

    # Interactive sorting method selection if not provided
    if not sort_by:
      click.echo("\nSelect sorting method:")
      sorting_options = [
        ("upload_date", "Sort by upload/publish date"),
        ("duration", "Sort by video duration"),
        ("title", "Sort by video title (alphabetical)"),
        ("channel", "Sort by channel name (alphabetical)"),
        ("position", "Sort by original playlist position"),
      ]

      for i, (key, description) in enumerate(sorting_options, 1):
        click.echo(f"{i}. {description}")

      try:
        sort_idx = click.prompt(
          f"Select sorting method [1-{len(sorting_options)}]", type=int
        )
      except click.Abort:
        click.echo("Operation cancelled.")
        return

      if not (1 <= sort_idx <= len(sorting_options)):
        click.echo("❌ Invalid selection.")
        return
      sort_by = sorting_options[sort_idx - 1][0]

    sort_criteria = cast(SortCriteria, sort_by)

    click.echo("\n📋 Creating sorted playlist...")
    click.echo(f"   Sort by: {sort_criteria}")
    click.echo(f"   Order: {'Descending' if reverse else 'Ascending'}")
    click.echo(f"   Privacy: {privacy_status}")

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
      click.echo("\n✅ Successfully created sorted playlist!")
      click.echo(f"   New playlist ID: {new_playlist_id}")
      click.echo(f"   URL: https://www.youtube.com/playlist?list={new_playlist_id}")
    else:
      click.echo(
        "\n❌ Failed to create sorted playlist or process was terminated.", err=True
      )

  except Exception as error:
    click.echo(f"❌ An error occurred: {error}", err=True)


@playlist.command()
@click.argument("playlist_id", required=False)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
def delete(playlist_id: str | None, force: bool) -> None:
  """Delete a playlist."""
  try:
    service = get_authenticated_service()

    # Handle playlist selection
    if not playlist_id:
      from .common import select_playlist_interactive

      click.echo("⚠️  Select a playlist to DELETE:")
      playlist_id = select_playlist_interactive(service, "Select playlist to DELETE")

    # Get playlist info for confirmation
    playlist_info = get_playlist_info(service, playlist_id)
    if not playlist_info:
      click.echo(f"❌ Playlist with ID {playlist_id} not found.", err=True)
      return

    playlist_title = playlist_info["snippet"]["title"]
    video_count = playlist_info["contentDetails"]["itemCount"]

    # Confirmation
    if not force:
      click.echo("\n⚠️  WARNING: You are about to delete the playlist:")
      click.echo(f"   Title: {playlist_title}")
      click.echo(f"   Videos: {video_count}")
      click.echo(f"   ID: {playlist_id}")
      click.echo("\n   This action cannot be undone!")

      if not confirm_action("Are you sure you want to delete this playlist?"):
        click.echo("❌ Deletion cancelled.")
        return

    click.echo(f"\n🗑️  Deleting playlist: '{playlist_title}'...")
    success = delete_playlist(service, playlist_id)

    if success:
      click.echo("✅ Playlist deleted successfully!")
    else:
      click.echo("❌ Failed to delete playlist.", err=True)

  except Exception as error:
    click.echo(f"❌ An error occurred: {error}", err=True)
