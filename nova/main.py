"""Nova bot entry-point helpers (Pyrogram framework).

Builds the Client and registers all command + callback handlers via Pyrogram's
decorator-style `app.on_message` / `app.on_callback_query` registration.
"""
from __future__ import annotations

import logging

from pyrogram import filters

from .bot import build_client, configure_logging
from . import handlers

logger = logging.getLogger("nova")

COMMANDS = {
    "start", "help", "profile", "wallet", "balance", "daily", "weekly", "spin",
    "quests", "missions", "leaderboard", "achievements", "redeem", "refer",
    "settings", "support", "shop", "market", "trade", "auction", "property",
    "buy", "sell", "rent", "upgrade", "bank", "invest", "inventory", "garage",
    "travel", "guild", "friends", "gift", "events", "rpg", "battle", "boss",
    "pet", "fishing", "mining", "farming", "craft", "casino", "blackjack",
    "poker", "slots", "dice", "chess", "quiz", "ttt", "chat", "persona",
}

# command name -> handler function
HANDLER_MAP = {
    "start": handlers.start, "help": handlers.help_cmd, "profile": handlers.profile,
    "wallet": handlers.wallet, "balance": handlers.balance, "daily": handlers.daily,
    "weekly": handlers.weekly, "spin": handlers.spin, "quests": handlers.quests,
    "missions": handlers.missions, "leaderboard": handlers.leaderboard,
    "achievements": handlers.achievements, "redeem": handlers.redeem,
    "refer": handlers.refer, "settings": handlers.settings, "support": handlers.support,
    "shop": handlers.shop, "market": handlers.market, "trade": handlers.trade,
    "auction": handlers.auction, "property": handlers.property_menu, "buy": handlers.buy_prop,
    "sell": handlers.sell_prop, "rent": handlers.rent_prop, "upgrade": handlers.upgrade_prop,
    "bank": handlers.bank, "invest": handlers.invest, "inventory": handlers.inventory,
    "garage": handlers.garage, "travel": handlers.travel, "guild": handlers.guild,
    "friends": handlers.friends, "gift": handlers.gift, "events": handlers.events,
    "rpg": handlers.rpg, "battle": handlers.battle, "boss": handlers.boss,
    "pet": handlers.pet_menu, "fishing": handlers.simple_game, "mining": handlers.simple_game,
    "farming": handlers.simple_game, "craft": handlers.simple_game, "casino": handlers.games_menu,
    "blackjack": handlers.games_menu, "poker": handlers.games_menu, "slots": handlers.cb_slots,
    "dice": handlers.cb_dice, "chess": handlers.games_menu, "quiz": handlers.quiz_start,
    "ttt": handlers.ttt_start, "chat": handlers.chat_cmd, "persona": handlers.persona,
}


def register(app) -> None:
    """Attach every command and the callback router to the Client."""
    for name, fn in HANDLER_MAP.items():
        # simple cooldown mini-games + slots/dice reuse the message.command arg
        app.on_message(filters.command(name) & filters.private)(fn)
    # group chats: also respond (best-effort). Pyrogram dispatches groups too.
    app.on_message(filters.command(list(COMMANDS)) & filters.group)(_group_dispatch)
    # free-text chat (non-command) in private chats -> companion reply
    app.on_message(filters.text & ~filters.command([]) & filters.private)(handlers.chat)
    # callback queries
    app.on_callback_query()(handlers.callback)


async def _group_dispatch(client, message):
    # Only handle the command actually present (avoid double-handling when also private)
    if not message.command:
        return
    name = message.command[0].lower()
    fn = HANDLER_MAP.get(name)
    if fn:
        await fn(client, message)


def build_application():
    """Build (not run) the Pyrogram Client with handlers registered.

    Mirrors the old `build_application` name so run.py / tests stay simple.
    """
    app = build_client()
    register(app)
    configure_logging()
    return app


def run() -> None:
    app = build_application()
    app.run()
