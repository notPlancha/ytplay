"""Authentication commands."""

import os

import click

from ..config import TOKEN_FILE
from ..core.auth import authenticate_youtube
from ..core.youtube_api import get_playlists


@click.group()
def auth():
  """Authentication commands."""
  pass


@auth.command()
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
      click.echo(f"🔑 Found existing credentials at: {token_file}")
      service = authenticate_youtube(force=force)
      if not force:  # Check if existing credentials are valid
        click.echo("🔍 Checking existing YouTube API credentials...")
        playlists = get_playlists(service, max_results=1)
        if playlists is not None:
          click.echo("✅ Authentication verified! Using cached credentials.")
        else:
          click.echo("❌ Authentication failed or no access to playlists.")
    else:
      click.echo("🔑 Starting YouTube API authentication flow...")
      service = authenticate_youtube()

  except Exception as error:
    click.echo(f"❌ An error occurred during authentication: {error}", err=True)


@auth.command()
def status() -> None:
  """Check authentication status."""
  try:
    token_file = TOKEN_FILE
    if not os.path.exists(token_file):
      click.echo("❌ Not authenticated. Run 'ytplay auth login' first.")
      return

    click.echo("🔍 Checking authentication status...")
    service = authenticate_youtube()
    playlists = get_playlists(service, max_results=1)

    if playlists is not None:
      click.echo("✅ Authentication is valid.")
    else:
      click.echo("❌ Authentication failed. Try 'ytplay auth login --force'.")

  except Exception as error:
    click.echo(f"❌ Authentication check failed: {error}", err=True)


@auth.command()
def logout() -> None:
  """Remove stored credentials."""
  try:
    token_file = TOKEN_FILE
    if os.path.exists(token_file):
      os.remove(token_file)
      click.echo("✅ Credentials removed successfully.")
    else:
      click.echo("ℹ️  No stored credentials found.")

  except Exception as error:
    click.echo(f"❌ Failed to remove credentials: {error}", err=True)
