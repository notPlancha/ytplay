"""Cache management commands."""

import click

from ..core.cache import clear_cache, format_cache_size, get_cache_stats


@click.group()
def cache() -> None:
  """Cache management commands."""
  pass


@cache.command()
def info() -> None:
  """Show cache statistics."""
  try:
    stats = get_cache_stats()
    total_size = format_cache_size(stats["total_size_bytes"])

    click.echo(f"📊 {click.style('Cache Statistics:', fg='cyan', bold=True)}")
    click.echo(
      f"  Total files: {click.style(str(stats['total_files']), fg='magenta', bold=True)}"
    )
    click.echo(f"  Total size: {click.style(total_size, fg='yellow', bold=True)}")
    click.echo(
      f"  Playlist data: {click.style(str(stats['playlist']), fg='blue', bold=True)} files"
    )
    click.echo(
      f"  Video lists: {click.style(str(stats['videos']), fg='green', bold=True)} files"
    )
    click.echo(
      f"  Videos with durations: {click.style(str(stats['videos_durations']), fg='red', bold=True)} files"
    )

    if stats["total_files"] == 0:
      click.echo(f"  {click.style('(Cache is empty)', fg='blue', italic=True)}")

  except Exception as error:
    click.echo(f"❌ An error occurred: {error}", err=True)


@cache.command()
@click.option(
  "--type",
  "-t",
  type=click.Choice(["playlist", "videos", "videos_durations"], case_sensitive=False),
  help="Specific cache type to clear (if omitted, clears all cache)",
)
def clear(type: str | None) -> None:
  """Clear cached playlist data."""
  try:
    # Get stats before clearing
    stats_before = get_cache_stats()

    if stats_before["total_files"] == 0:
      click.echo(f"ℹ️  {click.style('Cache is already empty.', fg='blue')}")
      return

    # Clear the cache
    removed_count = clear_cache(type)

    if removed_count > 0:
      if type:
        click.echo(
          f"✅ {click.style(f'Cleared {removed_count} {type} cache files.', fg='green', bold=True)}"
        )
      else:
        click.echo(
          f"✅ {click.style(f'Cleared all {removed_count} cache files.', fg='green', bold=True)}"
        )
    else:
      click.echo(f"ℹ️  {click.style('No cache files were removed.', fg='blue')}")

  except Exception as error:
    click.echo(f"❌ An error occurred: {error}", err=True)
