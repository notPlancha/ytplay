"""Cache system for YouTube playlist data."""

import hashlib
import json
from pathlib import Path
from typing import Literal, TypeVar

from ..config import CONFIG_DIR
from ..types.youtube import EnhancedVideo, Playlist, PlaylistItem

# Cache directory
CACHE_DIR = Path(CONFIG_DIR) / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Cache file extensions
PLAYLIST_CACHE_EXT = ".playlist.json"
VIDEOS_CACHE_EXT = ".videos.json"
VIDEOS_WITH_DURATIONS_CACHE_EXT = ".videos_durations.json"

# Generic type for cached data
T = TypeVar("T")

# Cache type literal
CacheType = Literal["playlist", "videos", "videos_durations"]


def _get_cache_key(data: str) -> str:
  """Generate a consistent cache key from input data."""
  return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


def _get_cache_filepath(cache_type: CacheType, identifier: str) -> Path:
  """Get the cache file path for a given type and identifier."""
  cache_key = _get_cache_key(identifier)
  if cache_type == "playlist":
    filename = f"{cache_key}{PLAYLIST_CACHE_EXT}"
  elif cache_type == "videos":
    filename = f"{cache_key}{VIDEOS_CACHE_EXT}"
  elif cache_type == "videos_durations":
    filename = f"{cache_key}{VIDEOS_WITH_DURATIONS_CACHE_EXT}"
  else:
    raise ValueError(f"Unknown cache type: {cache_type}")

  return CACHE_DIR / filename


def get_cached_data(
  cache_type: CacheType, identifier: str
) -> list[Playlist] | list[PlaylistItem] | list[EnhancedVideo] | None:
  """Retrieve cached data if it exists."""
  cache_file = _get_cache_filepath(cache_type, identifier)

  if not cache_file.exists():
    return None

  try:
    with open(cache_file, encoding="utf-8") as f:
      return json.load(f)
  except (OSError, json.JSONDecodeError) as e:
    print(f"Warning: Failed to read cache file {cache_file}: {e}")
    # Remove corrupted cache file
    try:
      cache_file.unlink()
    except OSError:
      pass
    return None


def save_cached_data(
  cache_type: CacheType,
  identifier: str,
  data: list[Playlist] | list[PlaylistItem] | list[EnhancedVideo],
) -> bool:
  """Save data to cache."""
  cache_file = _get_cache_filepath(cache_type, identifier)

  try:
    with open(cache_file, "w", encoding="utf-8") as f:
      json.dump(data, f, indent=2, ensure_ascii=False)
    return True
  except (OSError, TypeError) as e:
    print(f"⚠️Warning: Failed to save cache file {cache_file}: {e}")
    return False


def clear_cache(cache_type: CacheType | None = None) -> int:
  """Clear cache files.

  Args:
      cache_type: Specific cache type to clear ('playlist', 'videos', 'videos_durations').
                 If None, clears all cache files.

  Returns:
      Number of files removed.
  """
  removed_count = 0

  if not CACHE_DIR.exists():
    return 0

  try:
    for cache_file in CACHE_DIR.iterdir():
      if cache_file.is_file():
        should_remove = False

        if cache_type is None:
          # Remove all cache files
          should_remove = cache_file.suffix in [
            PLAYLIST_CACHE_EXT,
            VIDEOS_CACHE_EXT,
            VIDEOS_WITH_DURATIONS_CACHE_EXT,
          ] or cache_file.name.endswith(
            (".playlist.json", ".videos.json", ".videos_durations.json")
          )
        else:
          # Remove specific cache type
          if cache_type == "playlist" and cache_file.name.endswith(PLAYLIST_CACHE_EXT):
            should_remove = True
          elif cache_type == "videos" and cache_file.name.endswith(VIDEOS_CACHE_EXT):
            should_remove = True
          elif cache_type == "videos_durations" and cache_file.name.endswith(
            VIDEOS_WITH_DURATIONS_CACHE_EXT
          ):
            should_remove = True

        if should_remove:
          cache_file.unlink()
          removed_count += 1

  except OSError as e:
    print(f"⚠️Warning: Error while clearing cache: {e}")

  return removed_count


def get_cache_stats() -> dict[str, int]:
  """Get statistics about the cache."""
  stats = {
    "playlist": 0,
    "videos": 0,
    "videos_durations": 0,
    "total_files": 0,
    "total_size_bytes": 0,
  }

  if not CACHE_DIR.exists():
    return stats

  try:
    for cache_file in CACHE_DIR.iterdir():
      if cache_file.is_file():
        stats["total_files"] += 1
        stats["total_size_bytes"] += cache_file.stat().st_size

        if cache_file.name.endswith(PLAYLIST_CACHE_EXT):
          stats["playlist"] += 1
        elif cache_file.name.endswith(VIDEOS_CACHE_EXT):
          stats["videos"] += 1
        elif cache_file.name.endswith(VIDEOS_WITH_DURATIONS_CACHE_EXT):
          stats["videos_durations"] += 1

  except OSError as e:
    print(f"⚠️Warning: Error while getting cache stats: {e}")

  return stats


def format_cache_size(size_bytes: int) -> str:
  """Format cache size in human-readable format."""
  if size_bytes < 1024:
    return f"{size_bytes} B"
  elif size_bytes < 1024 * 1024:
    return f"{size_bytes / 1024:.1f} KB"
  else:
    return f"{size_bytes / (1024 * 1024):.1f} MB"
