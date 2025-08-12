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

Then just clone it and run

```bash
git clone https://github.com/notPlancha/sort-yt-playlist.git
cd sort-yt-playlist
uv sync --dev
uv run main.py create-sorted-playlist
```

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



## Usage

### Quick-start

```bash
# List all your playlists
python main.py list-playlists

# Get detailed info about a specific playlist
python main.py playlist-summary PLAYLIST_ID_HERE

# List all videos in a playlist with their durations
python main.py list-videos-with-durations PLAYLIST_ID_HERE
```

### Available Commands

**See available commands**
```bash
python main.py --help
```

**List your playlists:**
```bash
python main.py list-playlists
```

**Get playlist summary:**
```bash
python main.py playlist-summary [PLAYLIST_ID]
```

**List videos in a playlist:**
```bash
python main.py list-videos [PLAYLIST_ID]
```

**List videos with durations:**
```bash
python main.py list-videos-with-durations [PLAYLIST_ID]
```

**Create a sorted copy of a playlist:**
```bash
python main.py create-sorted-playlist [PLAYLIST_ID] --sort-by duration --reverse
```

**Delete a playlist:**
```bash
python main.py delete-playlist [PLAYLIST_ID]
```

### Options
- `--output/-o`: Save output to a file
- `--format/-f`: Choose output format (text or json)
- `--no-progress`: Disable progress bars
- Use `--help` with any command for detailed options

### Finding Playlist IDs

To use commands that require a `[PLAYLIST_ID]`:

1. **From YouTube URL**: Copy the playlist ID from the URL
   - Example: `https://www.youtube.com/playlist?list=PLrAXtmRdnEQy6pNQS_rCH0jEIu23_v5wY`
   - Playlist ID: `PLrAXtmRdnEQy6pNQS_rCH0jEIu23_v5wY`

2. **Using this tool**: Run `python main.py list-playlists` to see all your playlists with their IDs

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
│   └── youtube.dat           # Cached authentication tokens
└── README.md
```

### Module Overview

- **`src/cli/`** - Command-line interface using Click framework
- **`src/core/`** - Core functionality (authentication, API calls, sorting)
- **`src/types/`** - TypedDict definitions for API responses and internal data
- **`src/output/`** - Functions for displaying and saving data
- **`config/`** - Configuration and credential files (OAuth credentials, cached tokens)