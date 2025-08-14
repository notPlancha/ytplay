"""Common utilities for CLI commands."""

from collections.abc import Callable, Sequence
from typing import Any, TypeVar

import click

from ..core.auth import get_youtube_service_if_authenticated
from ..core.youtube_api import get_playlists
from ..types.youtube import YouTubeService


def get_authenticated_service() -> YouTubeService:
  """Get authenticated YouTube service, handling errors."""
  service = get_youtube_service_if_authenticated()
  if service is None:
    click.echo(
      f"❌ {click.style('Not authenticated.', fg='red', bold=True)} "
      f"Run {click.style('ytplay auth login', fg='cyan', bold=True)} first."
    )
    raise click.Abort()
  return service


def select_playlist_interactive(
  service: YouTubeService, prompt: str = "Select a playlist"
) -> str:
  """
  Allow user to interactively select a playlist from their playlists.

  Args:
      service: Authenticated YouTube service
      prompt: Custom prompt message

  Returns:
      Selected playlist ID

  Raises:
      click.Abort: If no playlists found or invalid selection
  """
  try:
    click.echo(f"📥 {click.style('Retrieving your playlists...', fg='cyan')}")
    playlists = get_playlists(service)

    if not playlists:
      click.echo("❌ No playlists found.")
      raise click.Abort()

    # Display playlists with numbers
    click.echo(f"\n{prompt}:")
    for i, playlist in enumerate(playlists, 1):
      title = playlist["snippet"]["title"]
      pid = playlist["id"]
      video_count = playlist["contentDetails"]["itemCount"]
      privacy = playlist.get("status", {}).get("privacyStatus", "Unknown")

      # Color the privacy status
      if privacy == "private":
        privacy_color = "red"
      elif privacy == "public":
        privacy_color = "green"
      elif privacy == "unlisted":
        privacy_color = "yellow"
      else:
        privacy_color = "white"

      click.echo(
        f"{click.style(f'{i:2}.', fg='blue', bold=True)} {click.style(title, fg='white', bold=True)} "
        f"({click.style(str(video_count), fg='magenta', bold=True)} videos, "
        f"{click.style(privacy, fg=privacy_color, bold=True)}) "
        f"(ID: {click.style(pid, fg='cyan')})"
      )

    # Get user selection
    try:
      idx = click.prompt(f"Enter choice [1-{len(playlists)}]", type=int)
    except click.Abort:
      click.echo("Selection cancelled.")
      raise

    if not (1 <= idx <= len(playlists)):
      click.echo(f"❌ Invalid selection. Please choose 1-{len(playlists)}.")
      raise click.Abort()

    return playlists[idx - 1]["id"]

  except Exception as error:
    if isinstance(error, click.Abort):
      raise
    click.echo(f"❌ Failed to retrieve playlists: {error}", err=True)
    raise click.Abort()


# Common option groups
output_options = [
  click.option("--output", "-o", type=click.Path(), help="Save output to file"),
  click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="Output format (text or json)",
  ),
]

cache_options = [
  click.option("--no-progress", is_flag=True, help="Disable progress tracking"),
  click.option("--no-cache", is_flag=True, help="Skip cache and fetch fresh data"),
]

# Type variable for function decorators
F = TypeVar("F", bound=Callable[..., Any])


def add_options(options: Sequence[Callable[[F], F]]) -> Callable[[F], F]:
  """Decorator to add multiple options to a command."""

  def decorator(func: F) -> F:
    for option in reversed(options):
      func = option(func)
    return func

  return decorator


def handle_playlist_id_or_select(
  service: YouTubeService,
  playlist_id: str | None,
  action_description: str = "work with",
) -> str:
  """
  Handle playlist ID parameter - either use provided ID or let user select interactively.

  Args:
      service: Authenticated YouTube service
      playlist_id: Playlist ID from command line (optional)
      action_description: Description of what we're doing with the playlist

  Returns:
      Playlist ID to use
  """
  if playlist_id:
    return playlist_id

  return select_playlist_interactive(
    service, f"Select a playlist to {action_description}"
  )


def confirm_action(message: str, force: bool = False) -> bool:
  """
  Ask for user confirmation unless force flag is set.

  Args:
      message: Confirmation message
      force: Skip confirmation if True

  Returns:
      True if user confirmed or force is True
  """
  if force:
    return True

  try:
    return click.confirm(message)
  except click.Abort:
    return False
