#!/usr/bin/env python3
"""Run Nova (Pyrogram). Usage: python run.py  (after setting BOT_TOKEN in .env)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from nova.main import run

if __name__ == "__main__":
    run()
