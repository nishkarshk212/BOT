"""Pyrogram Client factory for Nova.

The bot framework is Pyrogram (https://docs.pyrogram.org). All chat/economy/game
logic lives in the other nova.* modules; this file only wires the Client.
"""
from __future__ import annotations

import logging

from pyrogram import Client, enums

from . import config

logger = logging.getLogger("nova")


def build_client() -> Client:
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN not set. Copy .env.example to .env and add your token.")
    # session name "nova" -> nova.session file in DATA_DIR
    app = Client(
        "nova",
        bot_token=config.BOT_TOKEN,
        workdir=config.DATA_DIR,
    )
    return app


def configure_logging() -> None:
    backend = (
        "OpenRouter"
        if config.OPENROUTER_API_KEY
        else ("local:" + config.LLM_BASE_URL.split("/")[-2].split(":")[0]
              if "openrouter" not in config.LLM_BASE_URL.lower() else "rule-based")
    )
    logger.info("Nova online. LLM=%s", backend)
