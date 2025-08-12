"""Authentication commands."""

import os

import click

from ..config import TOKEN_FILE
from ..core.auth import authenticate_youtube
from ..core.youtube_api import get_playlists


@click.group()
def auth() -> None:
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
      click.echo(
        f"🔑 Found existing credentials at: {click.style(token_file, fg='cyan')}"
      )
      service = authenticate_youtube(force=force)
      if not force:  # Check if existing credentials are valid
        click.echo(
          f"🔍 {click.style('Checking existing YouTube API credentials...', fg='yellow')}"
        )
        playlists = get_playlists(service, max_results=1)
        if playlists is not None:
          click.echo(
            f"✅ {click.style('Authentication verified! Using cached credentials.', fg='green', bold=True)}"
          )
        else:
          click.echo("❌ Authentication failed or no access to playlists.")
    else:
      click.echo(
        f"🔑 {click.style('Starting YouTube API authentication flow...', fg='cyan', bold=True)}"
      )
      service = authenticate_youtube()

  except Exception as error:
    click.echo(f"❌ An error occurred during authentication: {error}", err=True)


@auth.command()
def status() -> None:
  """Check authentication status."""
  try:
    token_file = TOKEN_FILE
    if not os.path.exists(token_file):
      click.echo(
        f"❌ {click.style('Not authenticated.', fg='red', bold=True)} Run {click.style('ytplay auth login', fg='cyan', bold=True)} first."
      )
      return

    click.echo(f"🔍 {click.style('Checking authentication status...', fg='yellow')}")
    service = authenticate_youtube()
    playlists = get_playlists(service, max_results=1)

    if playlists is not None:
      click.echo(f"✅ {click.style('Authentication is valid.', fg='green', bold=True)}")
    else:
      click.echo(
        f"❌ Authentication failed. Try {click.style('ytplay auth login --force', fg='cyan', bold=True)}."
      )

  except Exception as error:
    click.echo(f"❌ Authentication check failed: {error}", err=True)


@auth.command()
def logout() -> None:
  """Remove stored credentials."""
  try:
    token_file = TOKEN_FILE
    if os.path.exists(token_file):
      os.remove(token_file)
      click.echo(
        f"✅ {click.style('Credentials removed successfully.', fg='green', bold=True)}"
      )
    else:
      click.echo(f"ℹ️  {click.style('No stored credentials found.', fg='blue')}")

  except Exception as error:
    click.echo(f"❌ Failed to remove credentials: {error}", err=True)
