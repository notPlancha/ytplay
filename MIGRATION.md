# CLI Command Migration Guide

This document shows how old commands map to the new organized CLI structure.

## Command Mapping

| Old Command | New Command | Notes |
|-------------|-------------|--------|
| `login` | `auth login` | Authentication moved to auth group |
| `login --force` | `auth login --force` | Same options available |
| - | `auth status` | New: Check auth status |
| - | `auth logout` | New: Remove credentials |
| `list-playlists` | `playlist list` | Simplified name |
| `playlist-summary` | `playlist info` | Cleaner name |
| `list-videos` | `playlist videos` | Shorter, clearer |
| `list-videos-with-durations` | `playlist videos --durations` | Combined with flag |
| `create-sorted-playlist` | `playlist sort` | Much shorter! |
| `delete-playlist` | `playlist delete` | Consistent naming |
| `cache-info` | `cache info` | Moved to cache group |
| `clear-cache` | `cache clear` | Consistent naming |

## Key Improvements

### 1. **Logical Grouping**
Commands are now organized into logical groups:
- `auth` - Authentication management
- `playlist` - Playlist operations  
- `cache` - Cache management

### 2. **Shorter Commands**
- `create-sorted-playlist` → `playlist sort`
- `list-videos-with-durations` → `playlist videos --durations`
- `playlist-summary` → `playlist info`

### 3. **Consistent Naming**
All commands now follow a consistent `<group> <action>` pattern.

### 4. **Better Help**
- `ytplay --help` - Overview with quick start guide
- `ytplay playlist --help` - All playlist commands
- `ytplay playlist videos --help` - Specific command help

### 5. **Console Script**
After installation: `ytplay` instead of `python main.py`

## Examples

### Before:
```bash
python main.py login --force
python main.py list-playlists --output playlists.json --format json  
python main.py list-videos-with-durations PLxxx --no-cache --reverse
python main.py create-sorted-playlist PLxxx --sort-by duration --reverse
python main.py delete-playlist PLxxx --force
python main.py cache-info
```

### After:
```bash
ytplay auth login --force
ytplay playlist list --output playlists.json --format json
ytplay playlist videos PLxxx --durations --no-cache 
ytplay playlist sort PLxxx --sort-by duration --reverse
ytplay playlist delete PLxxx --force
ytplay cache info
```
