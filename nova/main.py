"""Nova bot entrypoint — builds the python-telegram-bot Application and runs polling."""
from __future__ import annotations

import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from . import config, db, handlers

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("nova")

# Map command name -> handler (so /balance, /redeem etc. are all wired)
COMMANDS = {
    "start": handlers.start,
    "help": handlers.help_cmd,
    "profile": handlers.profile,
    "wallet": handlers.wallet,
    "balance": handlers.balance,
    "daily": handlers.daily,
    "weekly": handlers.weekly,
    "spin": handlers.spin,
    "quests": handlers.quests,
    "missions": handlers.missions,
    "inventory": handlers.inventory,
    "shop": handlers.shop,
    "market": handlers.market,
    "trade": handlers.trade,
    "auction": handlers.auction,
    "leaderboard": handlers.leaderboard,
    "games": handlers.games_menu,
    "rpg": handlers.rpg,
    "battle": handlers.battle,
    "boss": handlers.boss,
    "pet": handlers.pet_menu,
    "property": handlers.property_menu,
    "buy": handlers.property_menu,
    "sell": handlers.property_menu,
    "rent": handlers.rent_prop,
    "upgrade": handlers.property_menu,
    "bank": handlers.bank,
    "invest": handlers.invest,
    "casino": handlers.games_menu,
    "blackjack": handlers.games_menu,
    "poker": handlers.games_menu,
    "slots": handlers.games_menu,
    "dice": handlers.games_menu,
    "chess": handlers.games_menu,
    "quiz": handlers.games_menu,
    "fishing": handlers.games_menu,
    "mining": handlers.games_menu,
    "farming": handlers.games_menu,
    "craft": handlers.games_menu,
    "travel": handlers.travel,
    "garage": handlers.garage,
    "guild": handlers.guild,
    "friends": handlers.friends,
    "gift": handlers.gift,
    "refer": handlers.refer,
    "achievements": handlers.achievements,
    "ttt": handlers.ttt_start,
    "events": handlers.events,
    "redeem": handlers.redeem,
    "settings": handlers.settings,
    "support": handlers.support,
    "chat": handlers.chat_cmd,
    "persona": handlers.persona,
}


def build_application() -> Application:
    if not config.BOT_TOKEN:
        raise SystemExit(
            "❌ BOT_TOKEN not set. Copy .env.example to .env and add your token."
        )
    db.init()
    app = Application.builder().token(config.BOT_TOKEN).build()
    for name, fn in COMMANDS.items():
        app.add_handler(CommandHandler(name, fn))
    app.add_handler(CallbackQueryHandler(handlers.callback))
    # free-text chat (must be last)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.chat)
    )
    logger.info("Nova online. LLM=%s",
                "OpenRouter" if config.OPENROUTER_API_KEY else "rule-based")
    return app


def main() -> None:
    app = build_application()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
