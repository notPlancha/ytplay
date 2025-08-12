"""YouTube Playlist CLI Tool - Main Entry Point

This file provides backwards compatibility for running the tool directly.
In production, use: ytplay [command]
For development: python main.py [command]
"""

from src.cli import main

if __name__ == "__main__":
  main()
