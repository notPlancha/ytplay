"""YouTube Playlist CLI Tool."""

import os

import click

from .auth_commands import auth
from .cache_commands import cache
from .playlist_commands import playlist


@click.group()
@click.version_option(version="1.0.0-dev", prog_name="ytplay")
@click.option(
  "--config-dir",
  envvar="YTPLAY_CONFIG_DIR",
  help="Directory for configuration files (also: YTPLAY_CONFIG_DIR env var)",
  metavar="PATH",
)
@click.option(
  "--client-secrets",
  envvar="YTPLAY_CLIENT_SECRETS",
  help="Path to client_secrets.json file (also: YTPLAY_CLIENT_SECRETS env var)",
  metavar="PATH",
)
@click.option(
  "--token-file",
  envvar="YTPLAY_TOKEN_FILE",
  help="Path to token file for authentication (also: YTPLAY_TOKEN_FILE env var)",
  metavar="PATH",
)
@click.pass_context
def main(
  ctx: click.Context,
  config_dir: str | None,
  client_secrets: str | None,
  token_file: str | None,
) -> None:
  """
  YouTube Playlist CLI Tool

  A tool for managing and sorting YouTube playlists.

  \b
  Configuration:
  Use environment variables or command-line options to customize file locations:
  • YTPLAY_CONFIG_DIR: Directory for config files (default: OS app data dir + /ytplay/)
  • YTPLAY_CLIENT_SECRETS: Path to client_secrets.json (default: <config_dir>/client_secrets.json)
  • YTPLAY_TOKEN_FILE: Path to token file (default: <config_dir>/youtube.dat)

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
  # Ensure the context object exists
  ctx.ensure_object(dict)

  # Set environment variables if CLI options are provided
  # This allows the config module to pick up the values
  if config_dir:
    os.environ["YTPLAY_CONFIG_DIR"] = config_dir
  if client_secrets:
    os.environ["YTPLAY_CLIENT_SECRETS"] = client_secrets
  if token_file:
    os.environ["YTPLAY_TOKEN_FILE"] = token_file


# Add command groups
main.add_command(auth)
main.add_command(playlist)
main.add_command(cache)


# Export the main function
__all__ = ["main"]
