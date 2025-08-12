"""YouTube Playlist CLI Tool."""

import click

from .auth_commands import auth
from .cache_commands import cache
from .playlist_commands import playlist


@click.group()
@click.version_option(version="1.0.0-dev", prog_name="ytplay")
def main():
  """
  YouTube Playlist CLI Tool

  A tool for managing and sorting YouTube playlists.

  \b
  Quick Start:
  1. ytplay auth login        # Authenticate with YouTube
  2. ytplay playlist list     # See your playlists
  3. ytplay playlist sort     # Create a sorted playlist

  \b
  Common Commands:
  • ytplay playlist videos PLAYLIST_ID --durations
  • ytplay playlist sort PLAYLIST_ID --sort-by duration --reverse
  • ytplay cache info
  """
  pass


# Add command groups
main.add_command(auth)
main.add_command(playlist)
main.add_command(cache)


# Export the main function
__all__ = ["main"]
