"""Cache management commands."""

import click

from ..core.cache import clear_cache, format_cache_size, get_cache_stats


@click.group()
def cache():
  """Cache management commands."""
  pass


@cache.command()
def info() -> None:
  """Show cache statistics."""
  try:
    stats = get_cache_stats()
    total_size = format_cache_size(stats["total_size_bytes"])

    click.echo("📊 Cache Statistics:")
    click.echo(f"  Total files: {stats['total_files']}")
    click.echo(f"  Total size: {total_size}")
    click.echo(f"  Playlist data: {stats['playlist']} files")
    click.echo(f"  Video lists: {stats['videos']} files")
    click.echo(f"  Videos with durations: {stats['videos_durations']} files")

    if stats["total_files"] == 0:
      click.echo("  (Cache is empty)")

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
      click.echo("ℹ️  Cache is already empty.")
      return

    # Clear the cache
    removed_count = clear_cache(type)

    if removed_count > 0:
      if type:
        click.echo(f"✅ Cleared {removed_count} {type} cache files.")
      else:
        click.echo(f"✅ Cleared all {removed_count} cache files.")
    else:
      click.echo("ℹ️  No cache files were removed.")

  except Exception as error:
    click.echo(f"❌ An error occurred: {error}", err=True)
