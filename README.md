# sort-wl

A Python CLI tool to interact with the YouTube API and manage playlist information. Create sorted copies of playlists, list videos with durations, and more!

## Setup

1. Create OAuth client credentials in Google Cloud Console
2. Add yourself as test user: https://console.cloud.google.com/auth/audience
3. Install dependencies: `uv sync --dev`

## Usage

### Authentication
First, authenticate with YouTube:
```bash
python main.py login
```

### Available Commands

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
│   └── client_secrets.json   # OAuth client credentials
├── data/                      # Runtime data files
│   └── youtube.dat           # Cached authentication tokens
└── README.md
```

### Module Overview

- **`src/cli/`** - Command-line interface using Click framework
- **`src/core/`** - Core functionality (authentication, API calls, sorting)
- **`src/types/`** - TypedDict definitions for API responses and internal data
- **`src/output/`** - Functions for displaying and saving data
- **`config/`** - Configuration files (OAuth credentials)
- **`data/`** - Runtime data (cached tokens)

## Development

This project uses [Ruff](https://docs.astral.sh/ruff/) for code formatting and linting.

### Code Quality Commands

```bash
# Format code
.\ruff.bat format

# Lint and auto-fix issues
.\ruff.bat lint

# Check for linting issues (without fixing)
.\ruff.bat check
```

Or use Ruff directly:
```bash
# Format all Python files
.venv\Scripts\ruff.exe format .

# Check and fix linting issues
.venv\Scripts\ruff.exe check . --fix

# Just check for issues
.venv\Scripts\ruff.exe check .
```

## Configuration

Ruff configuration is in `.ruff.toml` and includes:
- Code formatting (similar to Black)
- Import sorting (isort)
- Modern Python syntax upgrades
- Error detection and warnings