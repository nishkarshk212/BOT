#!/usr/bin/env python3
"""Run Nova (Pyrogram). Usage: python run.py  (after setting BOT_TOKEN in .env)."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Log to stdout (captured by the process manager / nohup redirect)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from nova.main import run

if __name__ == "__main__":
    run()
