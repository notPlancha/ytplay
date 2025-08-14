# ytplay

A Python CLI tool to interact with the YouTube API and manage playlist information. Created to sort playlists by video time, but it has more stuff too.

## Installation
```sh
uv tool install ytplay
ytplay playlist sort
# or
uvx ytplay playlist sort
```

## Setup

### Set Up Google API Credentials

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project

2. **Enable YouTube Data API v3**:
   - Go to APIs & Services > Library
   - Search for "YouTube Data API v3" and enable it

3. **Create OAuth 2.0 Credentials**:
   - Go to APIs & Services > Credentials
   - Create OAuth client ID (Desktop application)
   - Download the JSON file and rename it to `client_secrets.json`
   - Use `ytplay auth config add /path/to/client_secrets.json` to copy it to the config directory

4. **Add Test User** (Important):
   - Go to APIs & Services > OAuth consent screen
   - Add your Gmail address as a test user

## Configuration

The tool supports flexible configuration through environment variables and command-line options:

### File Locations

**Default locations:**
- Config directory: Platform-specific application data directory:
  - Windows: `%APPDATA%\ytplay\` (e.g., `C:\Users\Username\AppData\Roaming\ytplay\`)
  - Linux: `~/.config/ytplay/` (or `$XDG_CONFIG_HOME/ytplay/` if set)
  - macOS: `~/.config/ytplay/` (or `$XDG_CONFIG_HOME/ytplay/` if set)
- Client secrets: `<config_dir>/client_secrets.json`
- Token file: `<config_dir>/youtube.dat`

**Environment Variables:**
```bash
export YTPLAY_CONFIG_DIR="/path/to/config"              # Set config directory
export YTPLAY_CLIENT_SECRETS="/path/to/secrets.json"    # Set client secrets path
export YTPLAY_TOKEN_FILE="/path/to/token.dat"           # Set token file path
```

**Command-line Options:**
```bash
ytplay --config-dir /path/to/config playlist list           # Set config directory
ytplay --client-secrets /path/to/secrets.json auth login    # Set client secrets path
ytplay --token-file /path/to/token.dat auth status         # Set token file path
```

**Check Current Configuration:**
```bash
ytplay auth config show    # Show current file locations and status
```

**Add Configuration Files:**
```bash
ytplay auth config add /path/to/client_secrets.json    # Copy client secrets to config directory
ytplay auth config add /path/to/file.json --name custom.json  # Copy with custom name
ytplay auth config add /path/to/file.json --force      # Overwrite existing file
```

**Configuration Priority:**
1. Command-line options (highest priority)
2. Environment variables  
3. Default locations (lowest priority)

### Troubleshooting

**Error: "client_secrets.json not found"**
- Make sure you've downloaded and renamed the OAuth credentials file
- Verify it's placed in the `config/` folder: `config/client_secrets.json`

**Error: "Access blocked: This app's request is invalid"**
- Make sure you've added your Gmail address as a test user in the OAuth consent screen
- Verify you're using the same Google account that you added as a test user

**Error: "The OAuth client was not found"**
- Double-check that you've enabled the YouTube Data API v3 in your Google Cloud project
- Make sure you're using the correct Google Cloud project

> [!NOTE]  
> - **API Quota Limits**: The YouTube Data API v3 has daily quota limits (10,000 units per day for free projects). Large playlists or frequent usage may hit these limits.
>
> **Watch Later Playlist**: Cannot access or manage the "Watch Later" playlist as it's not accessible via the YouTube API. For that you can pray and use a [browser script](https://greasyfork.org/en/scripts?q=watch+later+sort) or extension.
>
> **Playlist limits**: A playlist can have a maximum of 5,000 videos AFAIK.

## Usage

### Quick Start

```bash
# Authenticate with YouTube
ytplay auth login --force

# List all your playlists
ytplay playlist list

# Get detailed info about a playlist
ytplay playlist info PLAYLIST_ID_HERE

# List videos with durations 
ytplay playlist videos PLAYLIST_ID_HERE --durations

# Create a sorted playlist
ytplay playlist sort PLAYLIST_ID_HERE --sort-by duration --reverse
```

### Command Reference

**Authentication:**
```bash
ytplay auth login                    # Authenticate with YouTube
ytplay auth login --force            # Force reauthentication  
ytplay auth status                   # Check authentication status
ytplay auth logout                   # Remove stored credentials
ytplay auth config show             # Show current configuration paths
ytplay auth config add <path>       # Copy configuration file to config directory
ytplay auth config remove --help     # Show help for removing configuration files
```

**Playlist Management:**
```bash
ytplay playlist list                 # List all your playlists
ytplay playlist info [PLAYLIST_ID]  # Get detailed playlist info
ytplay playlist videos [PLAYLIST_ID]         # List videos in playlist
ytplay playlist videos [PLAYLIST_ID] -d     # List videos with durations
ytplay playlist sort [PLAYLIST_ID]  # Create sorted playlist copy
ytplay playlist delete [PLAYLIST_ID]        # Delete a playlist
```

**Cache Management:**
```bash
ytplay cache info                    # Show cache statistics
ytplay cache clear                   # Clear all cached data
ytplay cache clear --type videos    # Clear specific cache type
```

### Command Options

**Common Options:**
- `--output/-o FILE`: Save output to file
- `--format/-f FORMAT`: Choose output format (text/json)
- `--no-progress`: Disable progress bars
- `--no-cache`: Skip cache and fetch fresh data

**Sort Options:**
- `--sort-by/-s CRITERIA`: Sort by upload_date, duration, title, channel, or position
- `--reverse/-r`: Sort in descending order
- `--title/-t TITLE`: Custom title for sorted playlist
- `--privacy/-p LEVEL`: Set privacy (private/public/unlisted)

**Examples:**
```bash
# Interactive playlist selection (if PLAYLIST_ID omitted)
ytplay playlist videos

# Save playlist info as JSON
ytplay playlist info PLxxx --output playlist.json --format json

# Create reverse-sorted playlist by duration
ytplay playlist sort PLxxx --sort-by duration --reverse --title "My Sorted Playlist"

# List videos with durations, skip cache
ytplay playlist videos PLxxx --durations --no-cache
```

## Project Structure

The project is organized into a clean, modular structure:

```
sort-wl/
├── main.py                    # Entry point for the CLI application
├── pyproject.toml             # Project configuration and dependencies
├── uv.lock                    # Dependency lock file (uv sync --dev)
├── .pre-commit-config.yaml    # Pre-commit hooks configuration (uv run pre-commit install)
├── ruff.toml                  # Ruff linter/formatter configuration (uv run ruff format/check --fix)
├── src/                       # Main source code
│   ├── cli/                   # CLI interface and commands
│   │   ├── __init__.py
│   │   ├── auth_commands.py   # Authentication CLI commands
│   │   ├── cache_commands.py  # Cache management CLI commands
│   │   ├── playlist_commands.py # Playlist management CLI commands
│   │   └── common.py          # Common CLI utilities
│   ├── core/                  # Core business logic
│   │   ├── __init__.py
│   │   ├── auth.py           # YouTube API authentication
│   │   ├── cache.py          # Cache management system
│   │   ├── youtube_api.py    # YouTube API functions
│   │   └── sorting.py        # Video sorting utilities
│   ├── types/                 # Type definitions
│   │   ├── __init__.py
│   │   └── youtube.py        # YouTube API type definitions
│   ├── output/                # Output formatting
│   │   ├── __init__.py
│   │   └── formatters.py     # Display and file output functions
│   ├── config.py             # Configuration and paths
│   └── __init__.py
└── README.md
```

Overengineered for sure but whtv thats what happens with vibe coding.

## TODO
- [ ] Make sorting resumable
- [ ] Make login cancelable