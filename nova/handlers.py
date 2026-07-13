"""All Nova command + callback handlers (Pyrogram framework).

The business logic (economy/games/content/db/ai) is framework-agnostic and lives
in sibling modules. Here we only adapt to Pyrogram's API:
  - command handlers receive (client, message)
  - callback handlers receive (client, callback_query)
  - per-user transient state (quiz answer, secrets, TTT board) lives in STATE
    keyed by user_id / chat_id, replacing python-telegram-bot's context.user_data.
"""
from __future__ import annotations

import random
import time

from pyrogram import enums, filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)

from . import config, content, db, economy, games
from . import ai as ai

# Markdown mode used for all replies (pyrogram.enums.ParseMode.MARKDOWN = legacy md)
MD = enums.ParseMode.MARKDOWN

# ---- per-user transient state (replaces context.user_data) ----
STATE: dict[int, dict] = {}
TTT: dict[int, dict] = {}        # chat_id -> board state


# --------------------------- helpers ---------------------------
def kbd(rows):
    """rows: list of [ (text, data), ... ]  -> InlineKeyboardMarkup"""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t, callback_data=d) for t, d in r] for r in rows]
    )


def uid(message) -> int:
    return message.from_user.id


def uname(message) -> tuple:
    u = message.from_user
    return (u.username, u.first_name or getattr(u, "full_name", None) or "Player")


def _st(user_id: int) -> dict:
    return STATE.setdefault(user_id, {})


async def _reply(message: Message, text: str, markup=None):
    """Reply to a Message (plain chat). Try markdown, fall back to plain."""
    try:
        await message.reply_text(text, reply_markup=markup, parse_mode=MD)
    except Exception:
        await message.reply_text(text, reply_markup=markup)


async def _cb(message: Message, text: str, markup=None):
    """Edit a callback-query's message. Try markdown, fall back to plain."""
    try:
        await message.edit_text(text, reply_markup=markup, parse_mode=MD)
    except Exception:
        await message.edit_text(text, reply_markup=markup)


# ============================ /start ============================
async def start(client, message):
    user = db.get_user(uid(message), *uname(message))
    lvl = config.level_from_xp(user["xp"])
    ref_note = ""
    if message.command and len(message.command) > 1:
        code = message.command[1].strip().upper()
        with db._lock, db._conn() as c:
            rows = c.execute("SELECT id, stats FROM users").fetchall()
        matched = None
        for r in rows:
            st = db.get_json(dict(r), "stats", {})
            if st.get("ref_code") == code and r["id"] != uid(message):
                matched = r["id"]; break
        if matched:
            res = economy.apply_referral(matched, uid(message))
            if res.get("ok"):
                ref_note = (
                    f"\n🎁 *Referral bonus!* +{res['referee_bonus']}🪙 thanks to your friend! "
                    f"(they got +{res['referrer_bonus']}🪙)\n"
                )
    txt = (
        f"👋 *Welcome to Nova*, {user['first_name'] or 'Player'}! ⚡\n\n"
        "I'm your fun companion, game master & virtual-world manager. "
        "Earn coins, collect pets, own properties, and climb the leaderboard!\n\n"
        f"🪙 *{user['coins']} coins*  💎 *{user['gems']} gems*  ⭐ *Level {lvl}*"
        f"{ref_note}\n\n"
        "Tap a button or type /help for the full command list."
    )
    await _reply(message, txt, kbd([
        [("🎁 Daily", "daily"), ("🎡 Spin", "spin"), ("🎮 Games", "games")],
        [("🛒 Shop", "shop"), ("🏠 Property", "property"), ("🐾 Pet", "pet")],
        [("💬 Chat", "chat"), ("🧑‍🤝‍🧑 Persona", "persona"), ("🏆 Leaderboard", "leaderboard")],
        [("❓ Help", "help")],
    ]))


# ============================ /help ============================
async def help_cmd(client, message):
    txt = (
        "*📖 Nova Command Guide*\n\n"
        "*Economy & Profile*\n"
        "/start · /profile · /wallet · /balance · /daily · /weekly · /spin\n"
        "/quests · /missions · /leaderboard · /achievements · /redeem · /refer · /settings · /support\n\n"
        "*World & Ownership*\n"
        "/shop · /market · /trade · /auction · /property · /buy · /sell · /rent · /upgrade\n"
        "/bank · /invest · /inventory · /garage · /travel · /guild · /friends · /gift\n\n"
        "*Games & Fun*\n"
        "/games · /ttt · /quiz · /rpg · /battle · /boss · /pet · /fishing · /mining · /farming\n"
        "/craft · /casino · /blackjack · /poker · /slots · /dice · /chess · /events\n\n"
        "*Chat companions*\n"
        "/chat · /persona  (switch between Nova ⚡ and Luna 🌸)\n\n"
        "*Quick bets (casino)*\n"
        "`/coinflip 100 heads` · `/dice 50` · `/rps rock`\n"
        "`/blackjack 200` · `/slots 50` · `/guess 7`\n\n"
        "💡 Just chat with me to earn coins and get tips!"
    )
    await _reply(message, txt, kbd([[("🏠 Menu", "start")]]))


# ============================ /profile ============================
async def profile(client, message):
    u = db.get_user(uid(message), *uname(message))
    lvl = config.level_from_xp(u["xp"])
    props = db.get_json(u, "properties", [])
    pets = db.get_json(u, "pets", [])
    inv = db.get_json(u, "inventory", {})
    need = config.xp_to_next(lvl)
    cur = u["xp"] - config.xp_for_level(lvl)
    bar = "█" * int(cur / need * 10) if need else "█" * 10
    bar = bar.ljust(10, "░")
    txt = (
        f"👤 *{u['first_name'] or 'Player'}* "
        f"(@{u['username'] or 'no_username'})\n"
        f"⭐ Level *{lvl}*  `{bar}` {cur}/{need} XP\n"
        f"🪙 Coins: *{u['coins']}*   💎 Gems: *{u['gems']}*\n"
        f"🔥 Daily streak: *{u['streak']}*\n"
        f"🏠 Properties: *{len(props)}*   🐾 Pets: *{len(pets)}*\n"
        f"🎒 Inventory items: *{sum(inv.values()) if isinstance(inv, dict) else len(inv)}*\n\n"
        "Use /property, /pet, /inventory or /shop to build your empire!"
    )
    await _reply(message, txt, kbd([
        [("🏠 Property", "property"), ("🐾 Pets", "pet"), ("🎒 Bag", "inv")],
        [("🏆 Rank", "leaderboard"), ("🎁 Daily", "daily")],
    ]))


async def wallet(client, message):
    u = db.get_user(uid(message), *uname(message))
    stats = db.get_json(u, "stats", {})
    banked = stats.get("bank", 0)
    txt = (
        f"💰 *Your Wallet*\n\n"
        f"🪙 Coins: *{u['coins']}*\n"
        f"💎 Gems: *{u['gems']}*\n"
        f"🏦 Bank: *{banked}* coins\n"
        f"⭐ XP: *{u['xp']}* (Level {config.level_from_xp(u['xp'])})\n\n"
        "/daily for free coins · /spin for surprises · /casino to gamble!"
    )
    await _reply(message, txt, kbd([[("🏦 Bank", "bank"), ("🎡 Spin", "spin")]]))


async def balance(client, message):
    await wallet(client, message)


# ===================== Daily / Weekly / Spin ======================
async def daily(client, message):
    res = economy.claim_daily(uid(message))
    if not res["ok"]:
        st = economy.daily_status(uid(message))
        await _reply(message,
            f"⏳ You already claimed today's bonus!\n"
            f"🔥 Streak: *{st['streak']}* · come back tomorrow for *{st['reward']}* coins.",
            kbd([[("🎡 Spin", "spin"), ("🎮 Games", "games")]]))
        return
    await _reply(message,
        f"🎁 *Daily bonus claimed!*\n\n"
        f"🔥 Streak: *{res['streak']}*\n"
        f"🪙 +*{res['reward']}* coins & +25 XP!\n\n"
        "Keep your streak alive for bigger rewards!",
        kbd([[("🎡 Spin", "spin"), ("🏆 Quests", "quests")]]))


async def weekly(client, message):
    res = economy.claim_weekly(uid(message))
    if not res["ok"]:
        await _reply(message, "⏳ You already grabbed this week's reward. See you next week!")
        return
    await _reply(message, f"📅 *Weekly reward!* +*{res['reward']}* coins & +120 XP! 🎉")


async def spin(client, message):
    res = games.spin_wheel(uid(message))
    u = db.get_user(uid(message))
    await _reply(message,
        f"🎡 *SPIN!* 🎡\n\n"
        f"You won: *{res['label']}* 🎉\n"
        f"🪙 {u['coins']} coins · 💎 {u['gems']} gems",
        kbd([[("🔄 Spin again", "spin"), ("🎁 Daily", "daily"), ("🛒 Shop", "shop")]]))


# ============================ Shop ============================
async def shop(client, message):
    rows = []
    for key, (name, typ, price, emo, desc) in content.SHOP_ITEMS.items():
        rows.append([(f"{emo} {name} — {price}🪙", f"shopbuy:{key}")])
    txt = "🛒 *Nova Shop* — tap an item to buy:\n_(coins are deducted from your wallet)_"
    await _reply(message, txt, kbd(rows + [[("🎒 Inventory", "inv"), ("🏠 Menu", "start")]]))


async def shop_buy(client, message, key: str):
    if key not in content.SHOP_ITEMS:
        await _reply(message, "❌ Unknown item.")
        return
    name, typ, price, emo, desc = content.SHOP_ITEMS[key]
    u = db.get_user(uid(message))
    if u["coins"] < price:
        await _reply(message, f"❌ Not enough coins for {name} ({price}🪙). You have {u['coins']}🪙.")
        return
    economy.add_coins(uid(message), -price)
    inv = db.get_json(u, "inventory", {})
    inv[key] = inv.get(key, 0) + 1
    db.set_json(uid(message), "inventory", inv)
    if key == "gem_pouch":
        economy.add_gems(uid(message), 5)
    await _reply(message, f"✅ Bought *{emo} {name}*! {desc}\n🎒 Check /inventory.",
                 kbd([[("🛒 Back to Shop", "shop")]]))


# ============================ Inventory ============================
async def inventory(client, message):
    u = db.get_user(uid(message))
    inv = db.get_json(u, "inventory", {})
    pets = db.get_json(u, "pets", [])
    props = db.get_json(u, "properties", [])
    lines = []
    for k, v in inv.items():
        if v:
            emo = content.SHOP_ITEMS.get(k, (k, "", 0, "📦", ""))[3]
            lines.append(f"{emo} {k.replace('_',' ').title()}: {v}")
    if not lines:
        lines.append("_Your bag is empty — visit /shop!_")
    pet_line = ", ".join(f"{p['emoji']}{p['name']}" for p in pets) or "_none_"
    prop_line = ", ".join(f"{content.PROPERTIES[p['key']][3]}{content.PROPERTIES[p['key']][0]} L{p['level']}" for p in props) or "_none_"
    txt = (
        f"🎒 *Inventory*\n" + "\n".join(lines) + "\n\n"
        f"🐾 *Pets:* {pet_line}\n"
        f"🏠 *Properties:* {prop_line}"
    )
    await _reply(message, txt, kbd([[("🛒 Shop", "shop"), ("🏠 Property", "property")]]))


# ============================ Property ============================
async def property_menu(client, message):
    u = db.get_user(uid(message))
    props = db.get_json(u, "properties", [])
    earned = economy.collect_income(uid(message))
    txt = "🏠 *Your Properties*\n"
    if earned:
        txt += f"💸 Collected *{earned}* passive coins!\n"
    if props:
        for p in props:
            name, _, _, emo, _ = content.PROPERTIES[p["key"]]
            inc = content.property_income_per_min(p["key"], p["level"])
            txt += f"{emo} {name} L{p['level']} — {inc}/min\n"
    else:
        txt += "_You don't own any yet! Buy your first below._\n"
    txt += "\n*Buy new:*"
    buy_rows = [[(f"{content.PROPERTIES[k][3]} {content.PROPERTIES[k][0]} ({content.property_cost(k,1)}🪙)", f"buy:{k}")]
                for k in content.PROPERTIES]
    await _reply(message, txt, kbd(buy_rows + [[("🛒 Shop", "shop"), ("🏠 Menu", "start")]]))


async def buy_prop(client, message, key=None):
    if key is None and message.command and len(message.command) > 1:
        key = message.command[1].lower()
    if key is None:
        await property_menu(client, message); return
    res = games.buy_property(uid(message), key)
    if "error" in res:
        await _reply(message, f"❌ {res['error']}")
        return
    await _reply(message, f"🏡 Bought *{res['emoji']} {res['name']}* for {res['cost']}🪙! It now earns passive income. Use /property to manage.",
                 kbd([[("⬆️ Upgrade", f"upgrade:{key}"), ("🏠 Property", "property")]]))


async def upgrade_prop(client, message, key=None):
    if key is None and message.command and len(message.command) > 1:
        key = message.command[1].lower()
    if key is None:
        await property_menu(client, message); return
    res = games.upgrade_property(uid(message), key)
    if "error" in res:
        await _reply(message, f"❌ {res['error']}")
        return
    await _reply(message, f"⬆️ {res['name']} upgraded to *Level {res['level']}*! ({res['cost']}🪙)",
                 kbd([[("🏠 Property", "property")]]))


async def sell_prop(client, message, key=None):
    if key is None and message.command and len(message.command) > 1:
        key = message.command[1].lower()
    if key is None:
        await property_menu(client, message); return
    res = games.sell_property(uid(message), key)
    if "error" in res:
        await _reply(message, f"❌ {res['error']}")
        return
    await _reply(message, f"💱 Sold *{res['name']}* for *{res['refund']}*🪙.",
                 kbd([[("🏠 Property", "property")]]))


async def rent_prop(client, message):
    await _reply(message,
        "🏷️ *Rent & Trade* — list a property for others to rent!\n_Feature preview:_ use /trade to propose swaps with friends. Full marketplace coming soon! 🚧",
        kbd([[("🏠 Property", "property")]]))


# ============================ Pet ============================
async def pet_menu(client, message):
    u = db.get_user(uid(message))
    pets = db.get_json(u, "pets", [])
    txt = "🐾 *Pets* — catch & collect! They gain XP and help on adventures.\n\n"
    if pets:
        for p in pets:
            txt += f"{p['emoji']} {p['name']} ({p['rarity']}) — Lv{p['level']} ⚔{p['power']}\n"
    else:
        txt += "_No pets yet! Catch one below._\n"
    catch_rows = [[(f"🎯 Catch a pet ({content.PET_CATCH_COST}🪙)", "catch")]]
    await _reply(message, txt, kbd(catch_rows + [[("🛒 Shop", "shop"), ("🏠 Menu", "start")]]))


async def catch(client, message):
    res = games.catch_pet(uid(message))
    if "error" in res:
        await _reply(message, f"❌ {res['error']}")
        return
    name, emo, rarity = res["pet"]
    if res["success"]:
        await _reply(message, f"🎉 *Gotcha!* You caught {emo} {name} ({rarity})! Check /pet.",
                     kbd([[("🐾 Pets", "pet")]]))
    else:
        await _reply(message, f"😅 So close! The {emo} {name} escaped. Try again with /pet.",
                     kbd([[("🎯 Try again", "catch")]]))


# ============================ Games ============================
async def games_menu(client, message):
    txt = "🎮 *Nova Games* — pick your challenge!"
    rows = [
        [("🟡 Coin Flip", "g:coinflip"), ("🟣 Dice", "g:dice"), ("⚪ RPS", "g:rps")],
        [("🔵 Blackjack", "g:blackjack"), ("🟢 Slots", "g:slots"), ("🔴 Quiz", "g:quiz")],
        [("🟠 Guess", "g:guess"), ("🐟 Fishing", "g:fishing"), ("⛏️ Mining", "g:mining")],
        [("🌾 Farming", "g:farming"), ("🛠️ Craft", "g:craft"), ("📈 Invest", "g:invest")],
        [("⭕❌ Tic-Tac-Toe", "g:ttt"), ("🏆 Quests", "quests"), ("⭐ Achievements", "achievements")],
    ]
    await _reply(message, txt, kbd(rows + [[("🏠 Menu", "start")]]))


BET_CHOICES = [10, 50, 200, 500]


async def game_pick(client, message, g):
    if g == "coinflip":
        rows = [[(f"Heads {b}🪙", f"cf:heads:{b}") for b in BET_CHOICES[:2]],
                [(f"Tails {b}🪙", f"cf:tails:{b}") for b in BET_CHOICES[2:]]]
        await _reply(message, "🪙 *Coin Flip* — pick a side & bet:", kbd(rows + [[("⬅️ Back", "games")]]))
    elif g == "dice":
        rows = [[(f"Bet {b}🪙", f"dice:{b}") for b in BET_CHOICES]]
        await _reply(message, "🎲 *Dice* — roll 4-6 to win 1.8× (or guess exact for 5×):", kbd(rows + [[("⬅️ Back", "games")]]))
    elif g == "rps":
        rows = [[("✊ Rock", "rps:rock"), ("✋ Paper", "rps:paper"), ("✌️ Scissors", "rps:scissors")]]
        await _reply(message, "✊✋✌️ *Rock Paper Scissors* — 30🪙 per win:", kbd(rows + [[("⬅️ Back", "games")]]))
    elif g == "blackjack":
        rows = [[(f"Bet {b}🪙", f"bj:{b}") for b in BET_CHOICES]]
        await _reply(message, "🃏 *Blackjack* — beat the dealer (closest to 21):", kbd(rows + [[("⬅️ Back", "games")]]))
    elif g == "slots":
        rows = [[(f"Bet {b}🪙", f"sl:{b}") for b in BET_CHOICES]]
        await _reply(message, "🎰 *Slots* — 3 matching = big payout!", kbd(rows + [[("⬅️ Back", "games")]]))
    elif g == "guess":
        rows = [[(str(n), f"guess:{n}") for n in range(1, 6)],
                [(str(n), f"guess:{n}") for n in range(6, 11)]]
        await _reply(message, "🔢 *Number Guess* — pick 1-10 (100🪙 if right):", kbd(rows + [[("⬅️ Back", "games")]]))
    elif g == "quiz":
        await quiz_start(client, message)
    elif g in ("fishing", "mining", "farming", "craft"):
        await simple_game(client, message, g)
    elif g == "invest":
        await invest(client, message)
    elif g == "ttt":
        await ttt_start(client, message)


# ---- casino handlers ----
def _after_game(message, out):
    """Record a game play and append any newly-unlocked achievements to `out`."""
    newly = economy.record_game(uid(message))
    if newly:
        names = ", ".join(content.ACHIEVEMENTS[k][0] for k in newly)
        out += f"\n\n🏅 *Unlocked:* {names}!"
    return out


async def cb_coinflip(client, message, side, bet):
    res = games.coinflip(uid(message), int(bet), side)
    if "error" in res:
        await _reply(message, f"❌ {res['error']}")
        return
    icon = "🪙" if res["result"] == "heads" else "🔥"
    out = f"{icon} *Coin Flip*: it was *{res['result']}* — you {'WON' if res['win'] else 'lost'} " \
          f"{'+' if res['win'] else '-'}{bet}🪙!"
    out = _after_game(message, out)
    await _reply(message, out, kbd([[("🔁 Again", "g:coinflip"), ("🎮 Games", "games")]]))


async def cb_dice(client, message, bet):
    res = games.dice(uid(message), int(bet))
    if "error" in res:
        await _reply(message, f"❌ {res['error']}")
        return
    out = f"🎲 Rolled *{res['rolled']}* — you {'WON' if res['win'] else 'lost'} " \
          f"{'+' if res['win'] else '-'}{res['bet'] if not res['win'] else int(res['bet']*0.8)}🪙"
    out = _after_game(message, out)
    await _reply(message, out, kbd([[("🔁 Again", "g:dice"), ("🎮 Games", "games")]]))


async def cb_rps(client, message, choice):
    res = games.rps(uid(message), choice)
    emoji = {"rock": "✊", "paper": "✋", "scissors": "✌️"}
    verdict = {"win": "🏆 You WIN +30🪙!", "lose": "😞 You lost!", "tie": "🤝 Tie!"}
    out = f"{emoji[res['you']]} vs {emoji[res['bot']]}\n{verdict[res['outcome']]}"
    out = _after_game(message, out)
    await _reply(message, out, kbd([[("🔁 Again", "g:rps"), ("🎮 Games", "games")]]))


async def cb_blackjack(client, message, bet):
    res = games.blackjack(uid(message), int(bet))
    if "error" in res:
        await _reply(message, f"❌ {res['error']}")
        return
    if res["win"] is True:
        v = "🏆 You WIN!"
    elif res["win"] is None:
        v = "🤝 Push (bet returned)"
    else:
        v = "😞 Dealer wins"
    out = (f"🃏 *Blackjack*\nYour hand: {res['player']} = {res['player_val']}\n"
           f"Dealer: {res['dealer']} = {res['dealer_val']}\n{v}")
    out = _after_game(message, out)
    await _reply(message, out, kbd([[("🔁 Again", "g:blackjack"), ("🎮 Games", "games")]]))


async def cb_slots(client, message, bet):
    res = games.slots(uid(message), int(bet))
    if "error" in res:
        await _reply(message, f"❌ {res['error']}")
        return
    reels = " ".join(res["reels"])
    out = f"🎰 {reels}\n" + ("🏆 JACKPOT! +%d🪙" % res["payout"] if res["win"]
          else f"😞 No match, -{bet}🪙")
    out = _after_game(message, out)
    await _reply(message, out, kbd([[("🔁 Again", "g:slots"), ("🎮 Games", "games")]]))


async def cb_guess(client, message, n):
    secret = _st(uid(message)).get("secret", None)
    res = games.number_guess(uid(message), int(n), secret)
    if res.get("done"):
        _st(uid(message)).pop("secret", None)
        out = f"🎯 Correct! The number was {res['secret']}. +100🪙!"
    else:
        _st(uid(message))["secret"] = res["secret"]
        out = f"❌ Not {n}… it's {res['hint']}! Try /guess again."
    out = _after_game(message, out)
    await _reply(message, out, kbd([[("🔁 Again", "g:guess"), ("🎮 Games", "games")]]))


# ---- quiz ----
async def quiz_start(client, message):
    q, a, cat = games.quiz_question()
    _st(uid(message))["quiz_answer"] = a
    opts = [a, *random.sample([o[1] for o in content.TRIVIA if o[1] != a], 2)]
    random.shuffle(opts)
    rows = [[(o[:18], f"quiz:{o}")] for o in opts]
    await _reply(message, f"❓ *Quiz* ({cat})\n{q}", kbd(rows + [[("🎮 Games", "games")]]))


async def quiz_answer_cb(client, message, ans):
    correct = _st(uid(message)).get("quiz_answer")
    res = games.quiz_answer(uid(message), ans, correct or "")
    if res["win"]:
        out = "✅ Correct! +50🪙 🎉"
    else:
        out = f"❌ Not quite — the answer was: *{correct}*"
    _st(uid(message)).pop("quiz_answer", None)
    out = _after_game(message, out)
    await _reply(message, out, kbd([[("➡️ Next", "g:quiz"), ("🎮 Games", "games")]]))


# ---- simple cooldown mini-games ----
CD = {"fishing": 30, "mining": 45, "farming": 60, "craft": 90}
REWARD = {"fishing": (40, 120), "mining": (60, 180), "farming": (30, 100), "craft": (80, 200)}


async def simple_game(client, message, g):
    u = db.get_user(uid(message))
    stats = db.get_json(u, "stats", {})
    last = stats.get(f"cd_{g}", 0)
    now = int(time.time())
    if now - last < CD[g]:
        left = CD[g] - (now - last)
        await _reply(message, f"⏳ Your {g} session is on cooldown. Try again in {left}s.")
        return
    lo, hi = REWARD[g]
    amt = random.randint(lo, hi)
    economy.add_coins(uid(message), amt)
    economy.add_xp(uid(message), 10)
    stats[f"cd_{g}"] = now
    db.set_json(uid(message), "stats", stats)
    emoji = {"fishing": "🐟", "mining": "⛏️", "farming": "🌾", "craft": "🛠️"}[g]
    label = {"fishing": "Caught a big one", "mining": "Mined ore", "farming": "Harvested crops", "craft": "Crafted an item"}[g]
    out = f"{emoji} *{label}!* +{amt}🪙 & +10 XP.\nCooldown {CD[g]}s."
    out = _after_game(message, out)
    await _reply(message, out, kbd([[("🎮 Games", "games")]]))


# ---- invest (stock sim) ----
async def invest(client, message):
    u = db.get_user(uid(message))
    bet = 100
    if message.command and len(message.command) > 1:
        try:
            bet = max(10, min(config.CASINO_MAX_BET, int(message.command[1])))
        except ValueError:
            pass
    if u["coins"] < bet:
        await _reply(message, "❌ Not enough coins to invest.")
        return
    mult = random.uniform(0.4, 2.2)
    out = int(bet * mult) - bet
    economy.add_coins(uid(message), out)
    economy.add_xp(uid(message), 5)
    arrow = "📈" if out >= 0 else "📉"
    await _reply(message, f"{arrow} *Investment* of {bet}🪙 → {'+' if out>=0 else ''}{out}🪙 "
                  f"(×{mult:.2f})\n💡 Tip: /bank to keep coins safe!",
                 kbd([[("🎮 Games", "games")]]))


# ---- tic-tac-toe vs bot ----
def _ttt_keyboard(board):
    rows = []
    for r in range(3):
        row = []
        for c in range(3):
            i = r * 3 + c
            cell = board[i] if board[i] != " " else "·"
            row.append((cell, f"ttt:{i}"))
        rows.append(row)
    return rows


async def ttt_start(client, message):
    chat_id = message.chat.id
    TTT[chat_id] = games.ttt_new()
    st = TTT[chat_id]
    await _reply(message, "⭕❌ *Tic-Tac-Toe!* You're ❌, I'm ⭕. You go first!\n\n" +
                 games.ttt_render(st["board"]),
                 kbd(_ttt_keyboard(st["board"]) + [[("🎮 Games", "games")]]))


async def ttt_move_cb(client, message, pos):
    chat_id = message.chat.id
    st = TTT.get(chat_id)
    if st is None:
        await ttt_start(client, message)
        return
    games.ttt_move(st, int(pos))
    board = st["board"]
    if st["over"]:
        result = st["result"]
        if result == "win":
            economy.add_coins(uid(message), 40); economy.add_xp(uid(message), 12)
            verdict = "🏆 You WIN! +40🪙"
        elif result == "draw":
            economy.add_coins(uid(message), 10); economy.add_xp(uid(message), 5)
            verdict = "🤝 Draw!"
        else:
            verdict = "😞 I win this round!"
        newly = economy.record_game(uid(message))
        txt = f"⭕❌ *Tic-Tac-Toe*\n\n{games.ttt_render(board)}\n\n{verdict}"
        if newly:
            names = ", ".join(content.ACHIEVEMENTS[k][0] for k in newly)
            txt += f"\n\n🏅 *Unlocked:* {names}!"
        TTT.pop(chat_id, None)
        await _reply(message, txt, kbd([[("🔁 Play again", "g:ttt"), ("🎮 Games", "games")]]))
    else:
        txt = "⭕❌ *Your move!* (You're ❌)\n\n" + games.ttt_render(board)
        await _reply(message, txt, kbd(_ttt_keyboard(board) + [[("🎮 Games", "games")]]))


# ============================ Leaderboard ============================
async def leaderboard(client, message):
    with db._lock, db._conn() as c:
        rows = c.execute(
            "SELECT id, first_name, coins, xp FROM users ORDER BY coins DESC LIMIT 10"
        ).fetchall()
    if not rows:
        await _reply(message, "No players yet — be the first! 🏆")
        return
    txt = "🏆 *Top Players (by coins)*\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, r in enumerate(rows):
        m = medals[i] if i < 3 else f"{i+1}."
        txt += f"{m} {r['first_name'] or 'Player'}: {r['coins']}🪙 (Lv{config.level_from_xp(r['xp'])})\n"
    me = db.get_user(uid(message))
    txt += f"\n— You: {me['coins']}🪙 (Lv{config.level_from_xp(me['xp'])}) —"
    await _reply(message, txt, kbd([[("🎮 Games", "games"), ("🏠 Menu", "start")]]))


# ============================ Quests / Missions ============================
async def quests(client, message):
    u = db.get_user(uid(message))
    stats = db.get_json(u, "stats", {})
    claimed = set(stats.get("missions_done", []))
    txt = "📋 *Daily Missions* — complete & claim rewards!\n\n"
    rows = []
    for mid, text, rc, rx in content.DAILY_MISSIONS:
        done = mid in claimed
        txt += f"{'✅' if done else '▫️'} {text} — {rc}🪙 / {rx}XP\n"
        if not done:
            rows.append([(f"Claim: {text[:20]}…", f"quest:{mid}")])
    if not rows:
        txt += "\n🎉 All done! Come back tomorrow."
    await _reply(message, txt, kbd(rows + [[("🎁 Daily", "daily")]]))


async def claim_quest(client, message, mid):
    mission = next((m for m in content.DAILY_MISSIONS if m[0] == mid), None)
    if not mission:
        await _reply(message, "❌ Unknown mission.")
        return
    u = db.get_user(uid(message))
    stats = db.get_json(u, "stats", {})
    done = set(stats.get("missions_done", []))
    if mid in done:
        await _reply(message, "✅ Already claimed that mission.")
        return
    economy.add_coins(uid(message), mission[2])
    economy.add_xp(uid(message), mission[3])
    done.add(mid)
    stats["missions_done"] = list(done)
    db.set_json(uid(message), "stats", stats)
    await _reply(message, f"✅ *{mission[1]}* complete! +{mission[2]}🪙 / +{mission[3]}XP",
                 kbd([[("📋 Missions", "quests")]]))


async def missions(client, message):
    await quests(client, message)


# ============================ Market / Trade / Auction ============================
async def market(client, message):
    await _reply(message,
        "🏪 *Marketplace* — browse player listings & auction rare items!\n"
        "🚧 Live trading is in beta. Use /trade to propose a swap and /auction to list an item.",
        kbd([[("🎒 Inventory", "inv")]]))


async def trade(client, message):
    args = message.command[1:] if message.command and len(message.command) > 1 else []
    if len(args) >= 2:
        try:
            target = int(args[0]); amt = int(args[1])
        except ValueError:
            await _reply(message, "Usage: /trade <user_id> <amount>")
            return
        u = db.get_user(uid(message))
        if u["coins"] < amt or amt <= 0:
            await _reply(message, "❌ Invalid amount or not enough coins.")
            return
        economy.add_coins(uid(message), -amt)
        economy.add_coins(target, amt)
        await _reply(message, f"💸 Traded *{amt}🪙* to user `{target}`. (Demo: trust-based)")
        return
    await _reply(message, "💱 *Trade & Auction*\nUsage: `/trade <user_id> <amount>`\n"
                  "Full player-to-player marketplace + auctions coming soon! 🚧")


async def auction(client, message):
    await _reply(message, "🔨 *Auctions* — list rare pets/items for bidding!\n🚧 Auction house launching soon. Meanwhile /trade works for direct swaps.")


# ============================ Bank ============================
async def bank(client, message):
    u = db.get_user(uid(message))
    stats = db.get_json(u, "stats", {})
    banked = stats.get("bank", 0)
    args = message.command[1:] if message.command and len(message.command) > 1 else []
    if args:
        cmd = args[0].lower()
        if cmd == "deposit" and len(args) > 1:
            try: amt = int(args[1])
            except ValueError: amt = 0
            if 0 < amt <= u["coins"]:
                economy.add_coins(uid(message), -amt)
                stats["bank"] = banked + amt
                db.set_json(uid(message), "stats", stats)
                await _reply(message, f"🏦 Deposited *{amt}🪙*. Safe & sound!")
                return
            await _reply(message, "❌ Invalid deposit amount.")
            return
        if cmd == "withdraw" and len(args) > 1:
            try: amt = int(args[1])
            except ValueError: amt = 0
            if 0 < amt <= banked:
                economy.add_coins(uid(message), amt)
                stats["bank"] = banked - amt
                db.set_json(uid(message), "stats", stats)
                await _reply(message, f"🏦 Withdrew *{amt}🪙*.")
                return
            await _reply(message, "❌ Invalid withdrawal amount.")
            return
        if cmd == "collect":
            interest = max(1, int(banked * 0.01))
            economy.add_coins(uid(message), interest)
            await _reply(message, f"🏦 Collected *{interest}🪙* interest!")
            return
    await _reply(message, f"🏦 *Bank* — your vault: *{banked}🪙*\n"
                  "Commands: `/bank deposit <amt>` · `/bank withdraw <amt>` · `/bank collect` (1% daily interest)",
                  kbd([[("💰 Wallet", "wallet")]]))


# ============================ Guild / Friends / Gift ============================
async def guild(client, message):
    g = db.meta_get("guilds", {})
    args = message.command[1:] if message.command and len(message.command) > 1 else []
    if args:
        cmd = args[0].lower()
        u = uid(message)
        if cmd == "create" and len(args) > 1:
            name = " ".join(args[1:])
            gid = name.lower().replace(" ", "_")
            g[gid] = {"name": name, "members": [u], "coins": 0}
            db.meta_set("guilds", g)
            await _reply(message, f"🛡️ Created guild *{name}*! Invite friends with `/guild join {gid}`")
            return
        if cmd == "join" and len(args) > 1:
            gid = args[1]
            if gid in g and u not in g[gid]["members"]:
                g[gid]["members"].append(u)
                db.meta_set("guilds", g)
                await _reply(message, f"🤝 Joined *{g[gid]['name']}* ({len(g[gid]['members'])} members)!")
                return
            await _reply(message, "❌ Guild not found.")
            return
    lines = "\n".join(f"🛡️ {v['name']} — {len(v['members'])} members" for v in g.values()) or "_No guilds yet._"
    await _reply(message, f"🛡️ *Guilds*\n{lines}\n\nCreate: `/guild create <name>` · Join: `/guild join <id>`")


async def friends(client, message):
    code = economy.get_referral_code(uid(message))
    await _reply(message,
        "👫 *Friends* — invite buddies and you BOTH earn coins!\n\n"
        f"🔗 Your referral link: `https://t.me/NovaBot?start={code}`\n"
        f"Or share your code: `{code}`\n\n"
        "When a friend starts the bot with your code, you get "
        f"+{economy.REFERRER_BONUS}🪙 and they get +{economy.REFEREE_BONUS}🪙. 🎉\n"
        "🚧 Full friend list & co-op missions coming soon!")


async def refer(client, message):
    code = economy.get_referral_code(uid(message))
    await _reply(message,
        "🔗 *Your Referral* — invite friends, earn together!\n\n"
        f"Share this link:\n`https://t.me/NovaBot?start={code}`\n\n"
        f"Code: `{code}`\n\n"
        f"You get +{economy.REFERRER_BONUS}🪙 · friend gets +{economy.REFEREE_BONUS}🪙 "
        "when they start with your code.")


async def gift(client, message):
    args = message.command[1:] if message.command and len(message.command) > 1 else []
    if len(args) >= 2:
        try:
            target = int(args[0]); amt = int(args[1])
        except ValueError:
            await _reply(message, "Usage: /gift <user_id> <amount>")
            return
        u = db.get_user(uid(message))
        if amt <= 0 or u["coins"] < amt:
            await _reply(message, "❌ Not enough coins to gift.")
            return
        economy.add_coins(uid(message), -amt)
        economy.add_coins(target, amt)
        await _reply(message, f"🎁 Gifted *{amt}🪙* to user `{target}`! Spreading joy ⚡")
        return
    await _reply(message, "🎁 *Gift* — share coins with friends!\nUsage: `/gift <user_id> <amount>`")


# ============================ RPG / Battle / Boss ============================
async def rpg(client, message):
    await _reply(message, "⚔️ *RPG Adventures* — dungeons, monster hunts & pet battles!\n"
                  "🚧 Full RPG engine (turn-based battles, loot, bosses) is on the roadmap. "
                  "For now, level up via /daily, /quests & /games, and collect /pet! 🐉")


async def battle(client, message):
    u = db.get_user(uid(message))
    pets = db.get_json(u, "pets", [])
    power = sum(p["power"] for p in pets)
    if power == 0:
        await _reply(message, "⚔️ *PvP Battle* — you need a pet first! Catch one with /pet.")
        return
    win = random.random() < min(0.85, 0.4 + power / 100)
    reward = random.randint(50, 200)
    if win:
        economy.add_coins(uid(message), reward)
        economy.add_xp(uid(message), 15)
        out = f"⚔️ Your team (power {power}) WINS! +{reward}🪙 🏆"
    else:
        out = f"⚔️ Tough fight — your team (power {power}) lost this round. Train more pets! 💪"
    await _reply(message, out, kbd([[("🐾 Pets", "pet"), ("🎮 Games", "games")]]))


async def boss(client, message):
    u = db.get_user(uid(message))
    lvl = config.level_from_xp(u["xp"])
    dmg = random.randint(10, 50) * lvl
    reward = random.randint(100, 400)
    economy.add_coins(uid(message), reward)
    economy.add_xp(uid(message), 30)
    await _reply(message, f"🐉 *BOSS RAID!* You dealt *{dmg}* damage and earned *{reward}🪙* +30XP! "
                  "Rally your guild for bigger bosses soon. 🔥",
                  kbd([[("🛡️ Guild", "guild"), ("🎮 Games", "games")]]))


# ============================ Garage / Travel ============================
async def garage(client, message):
    await _reply(message, "🚗 *Garage* — collect vehicles to boost travel speed & unlock missions!\n"
                  "🚧 Vehicle system launching soon. Buy a head-start at /shop (decor & upgrades).")


async def travel(client, message):
    await _reply(message, "✈️ *Travel* — explore worlds, unlock exclusive quests & events!\n"
                  "🚧 Travel map coming soon. Meanwhile, /events shows what's happening now.")


# ============================ Events / Redeem ============================
async def events(client, message):
    u = db.get_user(uid(message))
    st = economy.daily_status(uid(message))
    txt = "🎊 *Current Events*\n\n"
    txt += "🎡 *Lucky Week* — /spin for double mystery rewards!\n"
    txt += f"🔥 *Daily Streak Event* — keep your {st['streak']}-day streak for bonus coins!\n"
    txt += "🏆 *Leaderboard Race* — climb /leaderboard for seasonal rewards!\n\n"
    txt += "New seasonal festivals drop regularly — stay active! ⚡"
    await _reply(message, txt, kbd([[("🎡 Spin", "spin"), ("🏆 Rank", "leaderboard")]]))


async def redeem(client, message):
    args = message.command[1:] if message.command and len(message.command) > 1 else []
    if args:
        res = games.redeem(uid(message), args[0])
        if "error" in res:
            await _reply(message, f"❌ {res['error']}")
            return
        await _reply(message, f"🎟️ Redeemed! +{res['coins']}🪙 & +{res['gems']}💎")
        return
    codes = ", ".join(content.PROMO_CODES.keys())
    await _reply(message, f"🎟️ *Redeem a promo code!*\nUsage: `/redeem <CODE>`\n"
                  f"Try one of: `{codes}`")


# ============================ Settings / Support ============================
async def settings(client, message):
    await _reply(message, "⚙️ *Settings*\n• Notifications: ON 🔔\n• Private profile: OFF\n"
                  "• Language: English\n🚧 Toggle options coming soon — your data stays local & private.")


async def support(client, message):
    await _reply(message, "🛟 *Nova Support*\nHaving fun? Found a bug? "
                  "This is a self-hosted bot — check the project README for setup & the full command list.\n"
                  "Play fair, keep it friendly, and enjoy! ⚡")


# ============================ Achievements ============================
async def achievements(client, message):
    u = db.get_user(uid(message))
    earned = set(economy.awarded_achievements(uid(message)))
    lines = []
    for key, (name, desc) in content.ACHIEVEMENTS.items():
        mark = "✅" if key in earned else "🔒"
        lines.append(f"{mark} *{name}* — {desc}")
    claimed = economy.check_achievements(uid(message))
    head = ""
    if claimed:
        head = "🎉 *New achievement unlocked!* +100🪙 & +20XP each\n\n"
    await _reply(message, head + "*🏅 Achievements*\n" + "\n".join(lines),
                 kbd([[("🏠 Menu", "start")]]))


# ============================ Free chat ============================
async def chat(client, message):
    user_id = uid(message)
    db.get_user(user_id, *uname(message))
    reward = economy.chat_reward(user_id)
    text = message.text or ""
    reply = ai.nova_reply(message.chat.id, user_id, text)
    if reward:
        reply += f"\n\n_(+{reward}🪙 for chatting!)_"
    newly = economy.check_achievements(user_id)
    if newly:
        names = ", ".join(content.ACHIEVEMENTS[k][0] for k in newly)
        reply += f"\n\n🏅 *Unlocked:* {names}!"
    await _reply(message, reply)


# ===================== Chat companion (Luna) ========================
async def chat_cmd(client, message):
    user_id = uid(message)
    db.get_user(user_id, *uname(message))
    args = message.command[1:] if message.command and len(message.command) > 1 else []
    if args:
        want = args[0].lower()
        if ai.set_persona(user_id, want):
            persona = want
        else:
            await _reply(message, "❌ Unknown companion. Try /persona to see options.")
            return
    else:
        persona = ai.get_persona(user_id)
    p = content.PERSONAS[persona]
    await _reply(message,
        f"{p['emoji']} *{p['name']} is here!* 💬\n\n"
        f"Just send me a message and we'll chat. "
        f"Switch companions anytime with /persona.",
        kbd([[("🧑‍🤝‍🧑 Persona", "persona"), ("🎮 Games", "games")]]))


async def persona(client, message):
    args = message.command[1:] if message.command and len(message.command) > 1 else []
    if args:
        want = args[0].lower()
        if ai.set_persona(uid(message), want):
            p = content.PERSONAS[want]
            await _reply(message,
                f"✅ Switched to *{p['emoji']} {p['name']}*! Send a message to chat. 💬",
                kbd([[("💬 Chat", "chat"), ("🏠 Menu", "start")]]))
        else:
            await _reply(message, "❌ Unknown companion. Use /persona to see the list.")
        return
    cur = ai.get_persona(uid(message))
    rows = []
    for key, p in content.PERSONAS.items():
        mark = " ✅" if key == cur else ""
        rows.append([(f"{p['emoji']} {p['name']}{mark}", f"setpersona:{key}")])
    await _reply(message,
        "🧑‍🤝‍🧑 *Choose your companion* — this is who replies to your free-text chat:",
        kbd(rows + [[("💬 Chat", "chat"), ("🏠 Menu", "start")]]))


# ============================ Callback router ============================
async def callback(client, callback_query: CallbackQuery):
    await callback_query.answer()
    data = callback_query.data or ""
    message = callback_query.message
    parts = data.split(":")
    tag = parts[0]

    alias = {
        "start": start, "help": help_cmd, "daily": daily, "spin": spin,
        "shop": shop, "inv": inventory, "property": property_menu,
        "pet": pet_menu, "games": games_menu, "leaderboard": leaderboard,
        "quests": quests, "wallet": wallet, "guild": guild, "events": events,
        "achievements": achievements,
    }
    if tag in alias:
        await alias[tag](client, message); return
    if tag == "buy":
        await buy_prop(client, message, parts[1]); return
    if tag == "upgrade":
        await upgrade_prop(client, message, parts[1]); return
    if tag == "sell":
        await sell_prop(client, message, parts[1]); return
    if tag == "rent":
        await rent_prop(client, message); return
    if tag == "shopbuy":
        await shop_buy(client, message, parts[1]); return
    if tag == "catch":
        await catch(client, message); return
    if tag == "g" and len(parts) > 1:
        await game_pick(client, message, parts[1]); return
    if tag == "ttt" and len(parts) > 1:
        await ttt_move_cb(client, message, parts[1]); return
    if tag == "cf":
        await cb_coinflip(client, message, parts[1], parts[2]); return
    if tag == "dice":
        await cb_dice(client, message, parts[1]); return
    if tag == "rps":
        await cb_rps(client, message, parts[1]); return
    if tag == "bj":
        await cb_blackjack(client, message, parts[1]); return
    if tag == "sl":
        await cb_slots(client, message, parts[1]); return
    if tag == "guess":
        await cb_guess(client, message, parts[1]); return
    if tag == "quiz":
        await quiz_answer_cb(client, message, parts[1]); return
    if tag == "quest":
        await claim_quest(client, message, parts[1]); return
    if tag == "setpersona":
        pkey = parts[1]
        if ai.set_persona(uid(message), pkey):
            p = content.PERSONAS[pkey]
            await _cb(message,
                f"✅ Switched to *{p['emoji']} {p['name']}*! Send a message to chat. 💬",
                kbd([[("💬 Chat", "chat"), ("🏠 Menu", "start")]]))
        else:
            await _cb(message, "❌ Unknown companion.")
        return
    # unknown
    await _cb(message, "🤖 (unknown button)")
