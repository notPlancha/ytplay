"""Configuration constants for the application."""

import os
import tempfile
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent


def get_default_config_dir() -> Path:
  """Get the default configuration directory based on the operating system."""
  if os.name == "nt":  # Windows
    appdata = os.getenv("APPDATA")
    if appdata:
      return Path(appdata) / "ytplay"
    # Fallback to temp if APPDATA is not available
    return Path(tempfile.gettempdir()) / "ytplay"
  else:  # Unix-like (Linux, macOS, etc.)
    # Use XDG_CONFIG_HOME if available, otherwise ~/.config
    xdg_config = os.getenv("XDG_CONFIG_HOME")
    if xdg_config:
      return Path(xdg_config) / "ytplay"
    home = os.path.expanduser("~")
    return Path(home) / ".config" / "ytplay"


# Default configuration paths - use platform-specific app data directory
DEFAULT_CONFIG_DIR = get_default_config_dir()

# Configuration directory with environment variable support
CONFIG_DIR = Path(os.getenv("YTPLAY_CONFIG_DIR", DEFAULT_CONFIG_DIR))

# Ensure directories exist
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# File paths with environment variable support
CLIENT_SECRETS_PATH = Path(
  os.getenv("YTPLAY_CLIENT_SECRETS", CONFIG_DIR / "client_secrets.json")
)
TOKEN_FILE_PATH = Path(os.getenv("YTPLAY_TOKEN_FILE", CONFIG_DIR / "youtube.dat"))

# Ensure parent directories exist for custom paths
CLIENT_SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
TOKEN_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Convert to strings for compatibility
CLIENT_SECRETS_FILE = str(CLIENT_SECRETS_PATH)
TOKEN_FILE = str(TOKEN_FILE_PATH)


# Configuration info for CLI display
def get_config_info() -> dict[str, str | bool]:
  """Get current configuration paths for display."""
  return {
    "config_dir": str(CONFIG_DIR),
    "client_secrets": CLIENT_SECRETS_FILE,
    "token_file": TOKEN_FILE,
    "using_custom_config_dir": str(CONFIG_DIR) != str(DEFAULT_CONFIG_DIR),
    "using_custom_client_secrets": str(CLIENT_SECRETS_PATH)
    != str(CONFIG_DIR / "client_secrets.json"),
    "using_custom_token_file": str(TOKEN_FILE_PATH) != str(CONFIG_DIR / "youtube.dat"),
  }
