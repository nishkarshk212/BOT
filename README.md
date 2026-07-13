# ⚡ Nova — Telegram AI Companion & Virtual-World Bot

Nova is a fun, humorous Telegram bot that runs a complete virtual world:
an **economy** (coins, gems, XP, levels), **properties** with passive income,
**pets**, **games & casino**, **daily rewards**, **leaderboards**, **guilds**,
and a conversational AI brain.

It works **out of the box with zero config** (built-in rule-based companion),
and upgrades to an **LLM-powered persona** automatically when you supply an
OpenRouter key.

---

## ✨ Features

- **Economy & progression** — coins, gems, XP, levels, daily/weekly bonuses,
  login streaks, lucky wheel, passive property income, a bank with interest.
- **Virtual properties** — buy / upgrade / sell / rent 17 property types
  (house → apartment → villa → castle → space station …) each earning income.
- **Pets** — catch & collect pets by rarity (Common → Mythic); they power battles.
- **Games & casino** — coin flip, dice, rock-paper-scissors, number guess,
  blackjack, slots, trivia quiz, plus cooldown mini-games (fishing, mining,
  farming, crafting) and a stock-investment sim.
- **Social** — global leaderboard, guilds (create/join), friends, gifting,
  player-to-player trading, redeemable promo codes.
- **Achievements** — 6 unlockable badges (first coins, high roller, collector,
  tycoon, level 10, gambler) awarded automatically as you play, each with a bonus.
- **Tic-Tac-Toe** — play ❌ vs the bot's ⭕ on an inline board (`/ttt`).
- **Referrals** — `/refer` gives you a personal code + link; when a friend starts
  the bot with it, you both get coins.
- **Chat companions** — switch between **Nova** ⚡ (game master) and **Luna** 🌸
  (cheerful girl AI assistant) via `/persona`; free-text chat uses the selected one.
- **Persistent** — SQLite store (no external services needed).

---

## 🚀 Quick start

### 1. Get a bot token
Talk to [@BotFather](https://t.me/BotFather) on Telegram → `New Bot` → copy the token.

### 2. Configure
```bash
cp .env.example .env
# edit .env and paste your BOT_TOKEN
```
Optional: add `OPENROUTER_API_KEY` for the LLM brain (free key at
<https://openrouter.ai/keys>). Without it, Nova uses the built-in responder.

### 3. Run
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python run.py
```

That's it — message your bot `/start` 🎉

---

## 🕹️ Commands

| Group | Commands |
|-------|----------|
| Economy | `/start` `/profile` `/wallet` `/balance` `/daily` `/weekly` `/spin` `/quests` `/missions` `/leaderboard` `/achievements` `/redeem` `/refer` `/settings` `/support` |
| World | `/shop` `/market` `/trade` `/auction` `/property` `/buy` `/sell` `/rent` `/upgrade` `/bank` `/invest` `/inventory` `/garage` `/travel` |
| Social | `/guild` `/friends` `/gift` |
| Games | `/games` `/ttt` `/quiz` `/rpg` `/battle` `/boss` `/pet` `/fishing` `/mining` `/farming` `/craft` `/casino` `/blackjack` `/poker` `/slots` `/dice` `/chess` `/events` |
| Chat | `/chat` `/persona` |

Quick casino bets via text:
```
/coinflip 100 heads
/dice 50
/rps rock
/blackjack 200
/slots 50
/guess 7
```

Just **chat** with Nova to earn coins and get tips — it's a companion, not just a menu.

---

## 🧱 Project layout

```
nova-bot/
├── run.py              # entrypoint
├── nova/
│   ├── config.py       # constants, leveling math
│   ├── db.py           # SQLite persistence (users, history, meta)
│   ├── content.py      # properties, shop, pets, trivia, missions, promos
│   ├── economy.py      # coins/gems/XP, daily/weekly, passive income
│   ├── games.py        # all game logic (pure functions)
│   ├── ai.py           # LLM responder + rule-based fallback
│   ├── handlers.py     # every Telegram command + callback router
│   └── main.py         # builds the Application, wires handlers
├── tests/verify.py     # offline verification (no token needed)
└── .env.example
```

---

## ✅ Verify without a token

The test exercises economy, games, AI fallback, and app construction:

```bash
. .venv/bin/activate
python tests/verify.py
```

---

## 🐳 Docker (optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "run.py"]
```
Build/run: `docker build -t nova . && docker run -d --env-file .env nova`

---

## 🔧 Notes & roadmap

- State lives in `data/nova.db` (SQLite). Back that file up to preserve progress.
- Several advanced features (auction house, full RPG turn-based combat, vehicle
  travel map, live marketplace) are scaffolded and labeled 🚧 — the economy,
  games, properties, pets, and AI are fully functional now.
- Anti-cheat: coin math is server-authoritative; betting is bounded by balance.
