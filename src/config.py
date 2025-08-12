"""Configuration constants for the application."""

from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Configuration paths
CONFIG_DIR = PROJECT_ROOT / "config"

# Ensure directories exist
CONFIG_DIR.mkdir(exist_ok=True)

# File paths
CLIENT_SECRETS_PATH = CONFIG_DIR / "client_secrets.json"
TOKEN_FILE_PATH = CONFIG_DIR / "youtube.dat"

# Convert to strings for compatibility
CLIENT_SECRETS_FILE = str(CLIENT_SECRETS_PATH)
TOKEN_FILE = str(TOKEN_FILE_PATH)
