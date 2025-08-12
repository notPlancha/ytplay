# sort-playlist-yt

A Python CLI tool to interact with the YouTube API and manage playlist information. Created to sort playlists by video time, but it has more stuff too.

## Setup

### Prerequisites

- Python 3.13 or higher
- [uv package manager](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip


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
   - Place it in the `config/` folder

4. **Add Test User** (Important):
   - Go to APIs & Services > OAuth consent screen
   - Add your Gmail address as a test user

### Installation

```bash
git clone https://github.com/notPlancha/sort-yt-playlist.git
cd sort-yt-playlist
uv sync
```

After installation, you can use either:
- `ytplay` (recommended - direct command)
- `python main.py` (development/fallback)

> **Note**: The `ytplay` command is available globally after running `uv sync`.

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
> **Watch Later Playlist**: Cannot access or manage the "Watch Later" playlist as it's not accessible via the YouTube API. For that you can pray and use a [browser script](https://greasyfork.org/en/scripts?q=watch+later+sort) or extension.
> **Playlist limits**: A playlist can have a maximum of 5,000 videos AFAIK.

## Usage

### Quick Start

```bash
# First time setup
ytplay auth login

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

### Finding Playlist IDs

To use commands that require a `[PLAYLIST_ID]`:

1. **From YouTube URL**: Copy the playlist ID from the URL
   - Example: `https://www.youtube.com/playlist?list=PLrAXtmRdnEQy6pNQS_rCH0jEIu23_v5wY`
   - Playlist ID: `PLrAXtmRdnEQy6pNQS_rCH0jEIu23_v5wY`

2. **Using this tool**: Run `ytplay playlist list` to see all your playlists with their IDs

## Project Structure

The project is organized into a clean, modular structure:

```
sort-wl/
├── main.py                    # Entry point for the CLI application
├── src/                       # Main source code
│   ├── cli/                   # CLI interface and commands
│   │   ├── __init__.py
│   │   └── commands.py        # Click command definitions
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
├── config/                    # Configuration files
│   ├── client_secrets.json   # OAuth client credentials
│   ├── youtube.dat           # Cached authentication tokens
│   └── cache/                # Playlist cache directory
└── README.md
```

### Module Overview

- **`src/cli/`** - Modular command-line interface using Click framework
  - `auth_commands.py` - Authentication commands (login, logout, status)
  - `playlist_commands.py` - Playlist management commands 
  - `cache_commands.py` - Cache management commands
  - `common.py` - Shared utilities and option groups
- **`src/core/`** - Core functionality (authentication, API calls, sorting, caching)
- **`src/types/`** - TypedDict definitions for API responses and internal data
- **`src/output/`** - Functions for displaying and saving data
- **`config/`** - Configuration and credential files (OAuth credentials, cached tokens, cache storage)

## TODO
- [ ] Make sorting resumable