# sort-wl

A Python tool to interact with the YouTube API and retrieve playlist information.

## Setup

1. Create OAuth client credentials in Google Cloud Console
2. Add yourself as test user: https://console.cloud.google.com/auth/audience
3. Install dependencies: `uv sync --dev`

## Usage

Run the main script to retrieve your YouTube playlists:
```bash
python main.py
```

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