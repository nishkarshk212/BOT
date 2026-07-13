"""Nova bot configuration and constants."""
from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

# --- Telegram / LLM credentials (only BOT_TOKEN is required) ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("MODEL", "meta-llama/llama-3.3-70b-instruct:free")
FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv(
        "FALLBACK_MODELS",
        "google/gemma-2-9b-it:free,meta-llama/llama-3.1-8b-instruct:free,"
        "nousresearch/hermes-3-llama-3.1-8b:free",
    ).split(",")
    if m.strip()
]

# --- Behaviour tuning ---
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "18"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "25"))
DB_PATH = os.getenv("DB_PATH", "nova.db")
DATA_DIR = os.getenv("DATA_DIR", "data")

# --- Economy constants ---
START_COINS = 250
START_GEMS = 5
DAILY_BASE = 120
WEEKLY_BASE = 600
CHAT_COOLDOWN = 3  # seconds between earning coins from chatting
CHAT_REWARD_MIN, CHAT_REWARD_MAX = 1, 4
MAX_LEVEL = 100

# Leveling: XP needed for *next* level = BASE * level**EXP
LEVEL_XP_BASE = 50
LEVEL_XP_EXP = 1.35

# Lucky wheel prizes (value in coins, weight)
WHEEL_PRIZES = [
    ("💰 500 coins", 500, 6),
    ("💎 10 gems", 10, 3),
    ("⭐ 300 XP", 300, 8),
    ("🎁 Mystery box", 1, 4),
    ("🪙 100 coins", 100, 14),
    ("😅 Nothing", 0, 10),
    ("🏆 50 gems", 50, 1),
]

# Affordability guard for risky casino bets
CASINO_MAX_BET = 100_000

# Nova persona (used for the LLM system prompt AND the rule-based fallback tone)
SYSTEM_PROMPT = (
    "You are Nova, a fun, witty Telegram companion bot that also runs a virtual "
    "world of games, economy, properties, pets and events. You speak in a friendly, "
    "engaging, humorous tone but stay CONCISE (1-4 sentences) and always end with an "
    "interactive nudge or a suggested command like /games, /daily or /spin. "
    "You NEVER invent real-world facts, prices, or user stats — if asked about a game "
    "or command, briefly explain it and point to the command. You keep the magic-world "
    "fiction (coins, gems, pets) clearly playful. You do not discuss being an AI model "
    "unless asked. Keep emoji light and replies snappy."
)


def level_from_xp(xp: int) -> int:
    """Return level (1-based) for a given total XP."""
    lvl = 1
    while lvl < MAX_LEVEL and xp >= LEVEL_XP_BASE * (lvl ** LEVEL_XP_EXP):
        xp -= int(LEVEL_XP_BASE * (lvl ** LEVEL_XP_EXP))
        lvl += 1
    return lvl


def xp_for_level(level: int) -> int:
    """Total XP required to *reach* the start of `level` (level>=1)."""
    total = 0
    for l in range(1, level):
        total += int(LEVEL_XP_BASE * (l ** LEVEL_XP_EXP))
    return total


def xp_to_next(level: int) -> int:
    if level >= MAX_LEVEL:
        return 0
    return int(LEVEL_XP_BASE * (level ** LEVEL_XP_EXP))
