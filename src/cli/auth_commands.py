"""Authentication commands."""

import os
import shutil
from pathlib import Path

import click

from ..config import CONFIG_DIR, TOKEN_FILE, get_config_info
from ..core.auth import (
  authenticate_youtube,
  force_reauthentication,
  get_youtube_service_if_authenticated,
)
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

    if force:
      click.echo(
        f"🔑 {click.style('Forcing re-authentication...', fg='cyan', bold=True)}"
      )
      # Use specific force function
      service = force_reauthentication()
    elif os.path.exists(token_file):
      click.echo(
        f"🔑 Found existing credentials at: {click.style(token_file, fg='cyan')}"
      )
      click.echo(f"🔍 {click.style('Checking existing credentials...', fg='yellow')}")

      # Try existing credentials first
      service = get_youtube_service_if_authenticated()
      if service is None:
        # If existing credentials don't work, fall back to full authentication
        service = authenticate_youtube()
    else:
      click.echo(
        f"🔑 {click.style('Starting YouTube API authentication flow...', fg='cyan', bold=True)}"
      )
      # Use general authentication for fresh setup
      service = authenticate_youtube()

    # Verify authentication worked by testing API access
    click.echo(f"🔍 {click.style('Verifying authentication...', fg='yellow')}")
    playlists = get_playlists(service, max_results=1)

    if playlists is not None:
      if force:
        click.echo(
          f"✅ {click.style('Authentication successful! New credentials stored.', fg='green', bold=True)}"
        )
      elif os.path.exists(token_file):
        click.echo(
          f"✅ {click.style('Authentication verified! Using existing credentials.', fg='green', bold=True)}"
        )
      else:
        click.echo(
          f"✅ {click.style('Login successful! You are now authenticated.', fg='green', bold=True)}"
        )
    else:
      click.echo("❌ Authentication failed or no access to playlists.")

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

    # Use the non-triggering service getter for status check
    service = get_youtube_service_if_authenticated()

    if service is None:
      click.echo(
        f"❌ {click.style('Invalid or expired credentials.', fg='red', bold=True)} Try {click.style('ytplay auth login --force', fg='cyan', bold=True)}."
      )
      return

    # Test API access
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


@click.group()
def config() -> None:
  """Configuration management commands."""
  pass


@config.command("show")
def config_show() -> None:
  """Show current configuration paths."""
  try:
    config_info = get_config_info()

    click.echo(f"\n🔧 {click.style('Current Configuration:', fg='blue', bold=True)}")
    click.echo(
      f"   Config Directory: {click.style(config_info['config_dir'], fg='cyan')}"
    )
    if config_info["using_custom_config_dir"]:
      click.echo(f"     {click.style('(custom location)', fg='yellow')}")

    click.echo(f"\n📁 {click.style('File Locations:', fg='blue', bold=True)}")
    click.echo(
      f"   Client Secrets:  {click.style(config_info['client_secrets'], fg='cyan')}"
    )
    if config_info["using_custom_client_secrets"]:
      click.echo(f"     {click.style('(custom location)', fg='yellow')}")

    exists_secrets = os.path.exists(config_info["client_secrets"])
    status_secrets = click.style(
      "✅ exists" if exists_secrets else "❌ missing",
      fg="green" if exists_secrets else "red",
    )
    click.echo(f"     Status: {status_secrets}")

    click.echo(
      f"   Token File:      {click.style(config_info['token_file'], fg='cyan')}"
    )
    if config_info["using_custom_token_file"]:
      click.echo(f"     {click.style('(custom location)', fg='yellow')}")

    exists_token = os.path.exists(config_info["token_file"])
    status_token = click.style(
      "✅ exists" if exists_token else "❌ missing",
      fg="green" if exists_token else "red",
    )
    click.echo(f"     Status: {status_token}")

    click.echo(f"\n🌐 {click.style('Environment Variables:', fg='blue', bold=True)}")
    env_vars = [
      ("YTPLAY_CONFIG_DIR", "Configuration directory"),
      ("YTPLAY_CLIENT_SECRETS", "Client secrets file path"),
      ("YTPLAY_TOKEN_FILE", "Token file path"),
    ]

    for env_var, description in env_vars:
      value = os.getenv(env_var)
      if value:
        click.echo(
          f"   {click.style(env_var, fg='green')}: {click.style(value, fg='cyan')}"
        )
      else:
        click.echo(
          f"   {click.style(env_var, fg='white')}: {click.style('not set', fg='white', dim=True)}"
        )

    if not exists_secrets:
      click.echo(f"\n💡 {click.style('Next Steps:', fg='yellow', bold=True)}")
      click.echo("   1. Download client_secrets.json from Google Cloud Console")
      click.echo(
        f"   2. Run: {click.style('ytplay auth config add <path_to_secrets>', fg='green')}"
      )
      click.echo(f"   3. Run: {click.style('ytplay auth login', fg='green')}")

  except Exception as error:
    click.echo(f"❌ Failed to show configuration: {error}", err=True)


@config.command("add")
@click.argument("source_path", type=click.Path(exists=True, path_type=Path))
@click.option(
  "--name",
  default="client_secrets.json",
  help="Name for the copied file (default: client_secrets.json)",
)
@click.option("--force", is_flag=True, help="Overwrite existing file if it exists")
def config_add(source_path: Path, name: str, force: bool) -> None:
  """Copy a configuration file to the default config directory.

  SOURCE_PATH: Path to the file to copy (e.g., your downloaded client_secrets.json)
  """
  try:
    # Ensure config directory exists
    Path(CONFIG_DIR).mkdir(parents=True, exist_ok=True)

    # Determine destination path
    dest_path = Path(CONFIG_DIR) / name

    # Check if destination already exists
    if dest_path.exists() and not force:
      click.echo(f"❌ File already exists at: {click.style(str(dest_path), fg='cyan')}")
      click.echo(f"   Use {click.style('--force', fg='yellow')} to overwrite")
      return

    # Copy the file
    shutil.copy2(source_path, dest_path)

    click.echo(
      f"✅ {click.style('Configuration file copied successfully!', fg='green', bold=True)}"
    )
    click.echo(f"   From: {click.style(str(source_path), fg='cyan')}")
    click.echo(f"   To:   {click.style(str(dest_path), fg='cyan')}")

    # Show next steps
    if name == "client_secrets.json":
      click.echo(f"\n💡 {click.style('Next Steps:', fg='yellow', bold=True)}")
      click.echo(
        f"   Run: {click.style('ytplay auth login', fg='green')} to authenticate"
      )

  except Exception as error:
    click.echo(f"❌ Failed to copy configuration file: {error}", err=True)


@config.command("remove")
@click.option(
  "--client-secrets",
  is_flag=True,
  help="Remove client secrets file",
)
@click.option(
  "--token",
  is_flag=True,
  help="Remove authentication token file",
)
@click.option(
  "--all",
  is_flag=True,
  help="Remove all configuration files",
)
@click.option(
  "--force",
  "-f",
  is_flag=True,
  help="Skip confirmation prompts",
)
def config_remove(client_secrets: bool, token: bool, all: bool, force: bool) -> None:
  """Remove configuration files.

  Remove specific configuration files or all configuration files.
  Use --client-secrets to remove client_secrets.json,
  --token to remove the authentication token file,
  or --all to remove all configuration files.
  """
  try:
    config_info = get_config_info()

    # Determine what to remove
    remove_secrets = client_secrets or all
    remove_token = token or all

    if not (remove_secrets or remove_token):
      click.echo("❌ No files specified for removal.")
      click.echo("   Use --client-secrets, --token, or --all")
      click.echo("   Run 'ytplay auth config remove --help' for more options")
      return

    # Collect files that exist
    files_to_remove = []
    if remove_secrets and os.path.exists(config_info["client_secrets"]):
      files_to_remove.append(("Client secrets", config_info["client_secrets"]))
    if remove_token and os.path.exists(config_info["token_file"]):
      files_to_remove.append(("Token file", config_info["token_file"]))

    if not files_to_remove:
      click.echo(
        f"ℹ️  {click.style('No configuration files found to remove.', fg='blue')}"
      )
      return

    # Show what will be removed
    click.echo(f"\n🗑️  {click.style('Files to be removed:', fg='red', bold=True)}")
    for description, file_path in files_to_remove:
      click.echo(f"   {description}: {click.style(file_path, fg='cyan')}")

    # Confirmation prompt unless --force is used
    if not force:
      click.echo(
        f"\n⚠️  {click.style('Warning:', fg='yellow', bold=True)} This action cannot be undone."
      )
      if not click.confirm("Are you sure you want to remove these files?"):
        click.echo("❌ Removal cancelled.")
        return

    # Remove the files
    removed_count = 0
    for description, file_path in files_to_remove:
      try:
        os.remove(file_path)
        click.echo(f"✅ Removed {description}: {click.style(file_path, fg='green')}")
        removed_count += 1
      except FileNotFoundError:
        click.echo(
          f"ℹ️  {description} was already removed: {click.style(file_path, fg='blue')}"
        )
      except PermissionError:
        click.echo(
          f"❌ Permission denied removing {description}: {click.style(file_path, fg='red')}"
        )
      except Exception as e:
        click.echo(f"❌ Error removing {description}: {click.style(str(e), fg='red')}")

    if removed_count > 0:
      click.echo(
        f"\n✅ {click.style(f'Successfully removed {removed_count} configuration file(s).', fg='green', bold=True)}"
      )

      # Show next steps if client secrets were removed
      if remove_secrets and removed_count > 0:
        click.echo(f"\n💡 {click.style('Next Steps:', fg='yellow', bold=True)}")
        click.echo("   To use ytplay again, you'll need to:")
        click.echo("   1. Download client_secrets.json from Google Cloud Console")
        click.echo(
          f"   2. Run: {click.style('ytplay auth config add <path_to_secrets>', fg='green')}"
        )
        click.echo(f"   3. Run: {click.style('ytplay auth login', fg='green')}")

  except Exception as error:
    click.echo(f"❌ Failed to remove configuration files: {error}", err=True)


# Add the config subgroup to auth
auth.add_command(config)
