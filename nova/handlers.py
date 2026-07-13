"""All Nova command + callback handlers (python-telegram-bot v21 async)."""
from __future__ import annotations

import random
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from . import config, content, db, economy, games
from .ai import nova_reply

EMOJI = "✨🎮💎🪙🔥🚀🎉⚡🏆🌟"
COIN = "🪙"


def kbd(rows):
    """rows: list of [ (text, data), ... ]"""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t, callback_data=d) for t, d in r] for r in rows]
    )


def uid(update: Update) -> int:
    return update.effective_user.id


def uname(update: Update) -> tuple:
    u = update.effective_user
    return (u.username, u.first_name or u.full_name or "Player")


async def _reply(update: Update, text: str, markup=None):
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup,
                                                      parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")


# ============================ /start ============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(uid(update), *uname(update))
    lvl = config.level_from_xp(user["xp"])
    txt = (
        f"👋 *Welcome to Nova*, {user['first_name'] or 'Player'}! ⚡\n\n"
        "I'm your fun companion, game master & virtual-world manager. "
        "Earn coins, collect pets, own properties, and climb the leaderboard!\n\n"
        f"🪙 *{user['coins']} coins*  💎 *{user['gems']} gems*  ⭐ *Level {lvl}*\n\n"
        "Tap a button or type /help for the full command list."
    )
    await _reply(update, txt, kbd([
        [("🎁 Daily", "daily"), ("🎡 Spin", "spin"), ("🎮 Games", "games")],
        [("🛒 Shop", "shop"), ("🏠 Property", "property"), ("🐾 Pet", "pet")],
        [("🏆 Leaderboard", "leaderboard"), ("❓ Help", "help")],
    ]))


# ============================ /help ============================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (
        "*📖 Nova Command Guide*\n\n"
        "*Economy & Profile*\n"
        "/start · /profile · /wallet · /balance · /daily · /weekly · /spin\n"
        "/quests · /missions · /leaderboard · /redeem · /settings · /support\n\n"
        "*World & Ownership*\n"
        "/shop · /market · /trade · /auction · /property · /buy · /sell · /rent · /upgrade\n"
        "/bank · /invest · /inventory · /garage · /travel · /guild · /friends · /gift\n\n"
        "*Games & Fun*\n"
        "/games · /quiz · /rpg · /battle · /boss · /pet · /fishing · /mining · /farming\n"
        "/craft · /casino · /blackjack · /poker · /slots · /dice · /chess · /events\n\n"
        "*Quick bets (casino)*\n"
        "`/coinflip 100 heads` · `/dice 50` · `/rps rock`\n"
        "`/blackjack 200` · `/slots 50` · `/guess 7`\n\n"
        "💡 Just chat with me to earn coins and get tips!"
    )
    await _reply(update, txt, kbd([[("🏠 Menu", "start")]]))


# ============================ /profile ============================
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = db.get_user(uid(update), *uname(update))
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
    await _reply(update, txt, kbd([
        [("🏠 Property", "property"), ("🐾 Pets", "pet"), ("🎒 Bag", "inv")],
        [("🏆 Rank", "leaderboard"), ("🎁 Daily", "daily")],
    ]))


async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = db.get_user(uid(update), *uname(update))
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
    await _reply(update, txt, kbd([[("🏦 Bank", "bank"), ("🎡 Spin", "spin")]]))


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await wallet(update, context)


# ===================== Daily / Weekly / Spin ======================
async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = economy.claim_daily(uid(update))
    if not res["ok"]:
        st = economy.daily_status(uid(update))
        await _reply(update,
            f"⏳ You already claimed today's bonus!\n"
            f"🔥 Streak: *{st['streak']}* · come back tomorrow for *{st['reward']}* coins.",
            kbd([[("🎡 Spin", "spin"), ("🎮 Games", "games")]]))
        return
    await _reply(update,
        f"🎁 *Daily bonus claimed!*\n\n"
        f"🔥 Streak: *{res['streak']}*\n"
        f"🪙 +*{res['reward']}* coins & +25 XP!\n\n"
        "Keep your streak alive for bigger rewards!",
        kbd([[("🎡 Spin", "spin"), ("🏆 Quests", "quests")]]))
async def weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = economy.claim_weekly(uid(update))
    if not res["ok"]:
        await _reply(update, "⏳ You already grabbed this week's reward. See you next week!")
        return
    await _reply(update, f"📅 *Weekly reward!* +*{res['reward']}* coins & +120 XP! 🎉")


async def spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = games.spin_wheel(uid(update))
    u = db.get_user(uid(update))
    await _reply(update,
        f"🎡 *SPIN!* 🎡\n\n"
        f"You won: *{res['label']}* 🎉\n"
        f"🪙 {u['coins']} coins · 💎 {u['gems']} gems",
        kbd([[("🔄 Spin again", "spin"), ("🎁 Daily", "daily"), ("🛒 Shop", "shop")]]))


# ============================ Shop ============================
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = []
    for key, (name, typ, price, emo, desc) in content.SHOP_ITEMS.items():
        rows.append([(f"{emo} {name} — {price}🪙", f"shopbuy:{key}")])
    txt = "🛒 *Nova Shop* — tap an item to buy:\n_(coins are deducted from your wallet)_"
    await _reply(update, txt, kbd(rows + [[("🎒 Inventory", "inv"), ("🏠 Menu", "start")]]))


async def shop_buy(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    if key not in content.SHOP_ITEMS:
        await _reply(update, "❌ Unknown item.")
        return
    name, typ, price, emo, desc = content.SHOP_ITEMS[key]
    u = db.get_user(uid(update))
    if u["coins"] < price:
        await _reply(update, f"❌ Not enough coins for {name} ({price}🪙). You have {u['coins']}🪙.")
        return
    economy.add_coins(uid(update), -price)
    inv = db.get_json(u, "inventory", {})
    inv[key] = inv.get(key, 0) + 1
    db.set_json(uid(update), "inventory", inv)
    # some items have immediate effect
    if key == "gem_pouch":
        economy.add_gems(uid(update), 5)
    await _reply(update, f"✅ Bought *{emo} {name}*! {desc}\n🎒 Check /inventory.",
                 kbd([[("🛒 Back to Shop", "shop")]]))


# ============================ Inventory ============================
async def inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = db.get_user(uid(update))
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
    await _reply(update, txt, kbd([[("🛒 Shop", "shop"), ("🏠 Property", "property")]]))


# ============================ Property ============================
async def property_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = db.get_user(uid(update))
    props = db.get_json(u, "properties", [])
    earned = economy.collect_income(uid(update))
    txt = f"🏠 *Your Properties*\n"
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
    await _reply(update, txt, kbd(buy_rows + [[("🛒 Shop", "shop"), ("🏠 Menu", "start")]]))


async def buy_prop(update, context, key=None):
    if key is None and context.args:
        key = context.args[0].lower()
    if key is None:
        await property_menu(update, context); return
    res = games.buy_property(uid(update), key)
    if "error" in res:
        await _reply(update, f"❌ {res['error']}")
        return
    await _reply(update, f"🏡 Bought *{res['emoji']} {res['name']}* for {res['cost']}🪙! It now earns passive income. Use /property to manage.",
                 kbd([[("⬆️ Upgrade", f"upgrade:{key}"), ("🏠 Property", "property")]]))


async def upgrade_prop(update, context, key=None):
    if key is None and context.args:
        key = context.args[0].lower()
    if key is None:
        await property_menu(update, context); return
    res = games.upgrade_property(uid(update), key)
    if "error" in res:
        await _reply(update, f"❌ {res['error']}")
        return
    await _reply(update, f"⬆️ {res['name']} upgraded to *Level {res['level']}*! ({res['cost']}🪙)",
                 kbd([[("🏠 Property", "property")]]))


async def sell_prop(update, context, key=None):
    if key is None and context.args:
        key = context.args[0].lower()
    if key is None:
        await property_menu(update, context); return
    res = games.sell_property(uid(update), key)
    if "error" in res:
        await _reply(update, f"❌ {res['error']}")
        return
    await _reply(update, f"💱 Sold *{res['name']}* for *{res['refund']}*🪙.",
                 kbd([[("🏠 Property", "property")]]))


async def rent_prop(update, context):
    await _reply(update, "🏷️ *Rent & Trade* — list a property for others to rent!\n_Feature preview:_ use /trade to propose swaps with friends. Full marketplace coming soon! 🚧",
                 kbd([[("🏠 Property", "property")]]))


# ============================ Pet ============================
async def pet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = db.get_user(uid(update))
    pets = db.get_json(u, "pets", [])
    txt = "🐾 *Pets* — catch & collect! They gain XP and help on adventures.\n\n"
    if pets:
        for p in pets:
            txt += f"{p['emoji']} {p['name']} ({p['rarity']}) — Lv{p['level']} ⚔{p['power']}\n"
    else:
        txt += "_No pets yet! Catch one below._\n"
    catch_rows = [[(f"🎯 Catch a pet ({content.PET_CATCH_COST}🪙)", "catch")]]
    await _reply(update, txt, kbd(catch_rows + [[("🛒 Shop", "shop"), ("🏠 Menu", "start")]]))


async def catch(update, context):
    res = games.catch_pet(uid(update))
    if "error" in res:
        await _reply(update, f"❌ {res['error']}")
        return
    name, emo, rarity = res["pet"]
    if res["success"]:
        await _reply(update, f"🎉 *Gotcha!* You caught {emo} {name} ({rarity})! Check /pet.",
                     kbd([[("🐾 Pets", "pet")]]))
    else:
        await _reply(update, f"😅 So close! The {emo} {name} escaped. Try again with /pet.",
                     kbd([[("🎯 Try again", "catch")]]))


# ============================ Games ============================
async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = "🎮 *Nova Games* — pick your challenge!"
    rows = [
        [("🪙 Coin Flip", "g:coinflip"), ("🎲 Dice", "g:dice"), ("✊ RPS", "g:rps")],
        [("🃏 Blackjack", "g:blackjack"), ("🎰 Slots", "g:slots"), ("❓ Quiz", "g:quiz")],
        [("🔢 Guess", "g:guess"), ("🐟 Fishing", "g:fishing"), ("⛏️ Mining", "g:mining")],
        [("🌾 Farming", "g:farming"), ("🛠️ Craft", "g:craft"), ("📈 Invest", "g:invest")],
    ]
    await _reply(update, txt, kbd(rows + [[("🏠 Menu", "start")]]))


BET_CHOICES = [10, 50, 200, 500]


async def game_pick(update, context, g):
    if g in ("coinflip",):
        rows = [[(f"Heads {b}🪙", f"cf:heads:{b}") for b in BET_CHOICES[:2]],
                [(f"Tails {b}🪙", f"cf:tails:{b}") for b in BET_CHOICES[2:]]]
        await _reply(update, "🪙 *Coin Flip* — pick a side & bet:", kbd(rows + [[("⬅️ Back", "games")]]))
    elif g == "dice":
        rows = [[(f"Bet {b}🪙", f"dice:{b}") for b in BET_CHOICES]]
        await _reply(update, "🎲 *Dice* — roll 4-6 to win 1.8× (or guess exact for 5×):", kbd(rows + [[("⬅️ Back", "games")]]))
    elif g == "rps":
        rows = [[("✊ Rock", "rps:rock"), ("✋ Paper", "rps:paper"), ("✌️ Scissors", "rps:scissors")]]
        await _reply(update, "✊✋✌️ *Rock Paper Scissors* — 30🪙 per win:", kbd(rows + [[("⬅️ Back", "games")]]))
    elif g == "blackjack":
        rows = [[(f"Bet {b}🪙", f"bj:{b}") for b in BET_CHOICES]]
        await _reply(update, "🃏 *Blackjack* — beat the dealer (closest to 21):", kbd(rows + [[("⬅️ Back", "games")]]))
    elif g == "slots":
        rows = [[(f"Bet {b}🪙", f"sl:{b}") for b in BET_CHOICES]]
        await _reply(update, "🎰 *Slots* — 3 matching = big payout!", kbd(rows + [[("⬅️ Back", "games")]]))
    elif g == "guess":
        rows = [[(str(n), f"guess:{n}") for n in range(1, 6)],
                [(str(n), f"guess:{n}") for n in range(6, 11)]]
        await _reply(update, "🔢 *Number Guess* — pick 1-10 (100🪙 if right):", kbd(rows + [[("⬅️ Back", "games")]]))
    elif g == "quiz":
        await quiz_start(update, context)
    elif g in ("fishing", "mining", "farming", "craft"):
        await simple_game(update, context, g)
    elif g == "invest":
        await invest(update, context)


# ---- casino handlers ----
async def cb_coinflip(update, context, side, bet):
    res = games.coinflip(uid(update), int(bet), side)
    if "error" in res:
        await _reply(update, f"❌ {res['error']}")
        return
    icon = "🪙" if res["result"] == "heads" else "🔥"
    out = f"{icon} *Coin Flip*: it was *{res['result']}* — you {'WON' if res['win'] else 'lost'} " \
          f"{'+' if res['win'] else '-'}{bet}🪙!"
    await _reply(update, out, kbd([[("🔁 Again", "g:coinflip"), ("🎮 Games", "games")]]))


async def cb_dice(update, context, bet):
    res = games.dice(uid(update), int(bet))
    if "error" in res:
        await _reply(update, f"❌ {res['error']}")
        return
    out = f"🎲 Rolled *{res['rolled']}* — you {'WON' if res['win'] else 'lost'} " \
          f"{'+' if res['win'] else '-'}{res['bet'] if not res['win'] else int(res['bet']*0.8)}🪙"
    await _reply(update, out, kbd([[("🔁 Again", "g:dice"), ("🎮 Games", "games")]]))


async def cb_rps(update, context, choice):
    res = games.rps(uid(update), choice)
    emoji = {"rock": "✊", "paper": "✋", "scissors": "✌️"}
    verdict = {"win": "🏆 You WIN +30🪙!", "lose": "😞 You lost!", "tie": "🤝 Tie!"}
    out = f"{emoji[res['you']]} vs {emoji[res['bot']]}\n{verdict[res['outcome']]}"
    await _reply(update, out, kbd([[("🔁 Again", "g:rps"), ("🎮 Games", "games")]]))


async def cb_blackjack(update, context, bet):
    res = games.blackjack(uid(update), int(bet))
    if "error" in res:
        await _reply(update, f"❌ {res['error']}")
        return
    if res["win"] is True:
        v = "🏆 You WIN!"
    elif res["win"] is None:
        v = "🤝 Push (bet returned)"
    else:
        v = "😞 Dealer wins"
    out = (f"🃏 *Blackjack*\nYour hand: {res['player']} = {res['player_val']}\n"
           f"Dealer: {res['dealer']} = {res['dealer_val']}\n{v}")
    await _reply(update, out, kbd([[("🔁 Again", "g:blackjack"), ("🎮 Games", "games")]]))


async def cb_slots(update, context, bet):
    res = games.slots(uid(update), int(bet))
    if "error" in res:
        await _reply(update, f"❌ {res['error']}")
        return
    reels = " ".join(res["reels"])
    out = f"🎰 {reels}\n" + ("🏆 JACKPOT! +%d🪙" % res["payout"] if res["win"]
          else f"😞 No match, -{bet}🪙")
    await _reply(update, out, kbd([[("🔁 Again", "g:slots"), ("🎮 Games", "games")]]))


async def cb_guess(update, context, n):
    secret = context.user_data.get("secret", None)
    res = games.number_guess(uid(update), int(n), secret)
    if res.get("done"):
        context.user_data.pop("secret", None)
        out = f"🎯 Correct! The number was {res['secret']}. +100🪙!"
    else:
        context.user_data["secret"] = res["secret"]
        out = f"❌ Not {n}… it's {res['hint']}! Try /guess again."
    await _reply(update, out, kbd([[("🔁 Again", "g:guess"), ("🎮 Games", "games")]]))


# ---- quiz ----
async def quiz_start(update, context):
    q, a, cat = games.quiz_question()
    context.user_data["quiz_answer"] = a
    opts = [a, *random.sample([o[1] for o in content.TRIVIA if o[1] != a], 2)]
    random.shuffle(opts)
    rows = [[(o[:18], f"quiz:{o}")] for o in opts]
    await _reply(update, f"❓ *Quiz* ({cat})\n{q}", kbd(rows + [[("🎮 Games", "games")]]))


async def quiz_answer_cb(update, context, ans):
    correct = context.user_data.get("quiz_answer")
    res = games.quiz_answer(uid(update), ans, correct or "")
    if res["win"]:
        out = f"✅ Correct! +50🪙 🎉"
    else:
        out = f"❌ Not quite — the answer was: *{correct}*"
    context.user_data.pop("quiz_answer", None)
    await _reply(update, out, kbd([[("➡️ Next", "g:quiz"), ("🎮 Games", "games")]]))


# ---- simple cooldown mini-games ----
CD = {"fishing": 30, "mining": 45, "farming": 60, "craft": 90}
REWARD = {"fishing": (40, 120), "mining": (60, 180), "farming": (30, 100), "craft": (80, 200)}


async def simple_game(update, context, g):
    u = db.get_user(uid(update))
    stats = db.get_json(u, "stats", {})
    last = stats.get(f"cd_{g}", 0)
    now = int(time.time())
    if now - last < CD[g]:
        left = CD[g] - (now - last)
        await _reply(update, f"⏳ Your {g} session is on cooldown. Try again in {left}s.")
        return
    lo, hi = REWARD[g]
    amt = random.randint(lo, hi)
    economy.add_coins(uid(update), amt)
    economy.add_xp(uid(update), 10)
    stats[f"cd_{g}"] = now
    db.set_json(uid(update), "stats", stats)
    emoji = {"fishing": "🐟", "mining": "⛏️", "farming": "🌾", "craft": "🛠️"}[g]
    label = {"fishing": "Caught a big one", "mining": "Mined ore", "farming": "Harvested crops", "craft": "Crafted an item"}[g]
    await _reply(update, f"{emoji} *{label}!* +{amt}🪙 & +10 XP.\nCooldown {CD[g]}s.",
                 kbd([[("🎮 Games", "games")]]))


# ---- invest (stock sim) ----
async def invest(update, context):
    u = db.get_user(uid(update))
    bet = 100
    if context.args:
        try:
            bet = max(10, min(config.CASINO_MAX_BET, int(context.args[0])))
        except ValueError:
            pass
    if u["coins"] < bet:
        await _reply(update, "❌ Not enough coins to invest.")
        return
    mult = random.uniform(0.4, 2.2)
    out = int(bet * mult) - bet
    economy.add_coins(uid(update), out)
    economy.add_xp(uid(update), 5)
    arrow = "📈" if out >= 0 else "📉"
    await _reply(update, f"{arrow} *Investment* of {bet}🪙 → {'+' if out>=0 else ''}{out}🪙 "
                  f"(×{mult:.2f})\n💡 Tip: /bank to keep coins safe!",
                 kbd([[("🎮 Games", "games")]]))


# ============================ Leaderboard ============================
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db._lock, db._conn() as c:
        rows = c.execute(
            "SELECT id, first_name, coins, xp FROM users ORDER BY coins DESC LIMIT 10"
        ).fetchall()
    if not rows:
        await _reply(update, "No players yet — be the first! 🏆")
        return
    txt = "🏆 *Top Players (by coins)*\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, r in enumerate(rows):
        m = medals[i] if i < 3 else f"{i+1}."
        txt += f"{m} {r['first_name'] or 'Player'}: {r['coins']}🪙 (Lv{config.level_from_xp(r['xp'])})\n"
    me = db.get_user(uid(update))
    txt += f"\n— You: {me['coins']}🪙 (Lv{config.level_from_xp(me['xp'])}) —"
    await _reply(update, txt, kbd([[("🎮 Games", "games"), ("🏠 Menu", "start")]]))


# ============================ Quests / Missions ============================
async def quests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = db.get_user(uid(update))
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
    await _reply(update, txt, kbd(rows + [[("🎁 Daily", "daily")]]))


async def claim_quest(update, context, mid):
    mission = next((m for m in content.DAILY_MISSIONS if m[0] == mid), None)
    if not mission:
        await _reply(update, "❌ Unknown mission.")
        return
    u = db.get_user(uid(update))
    stats = db.get_json(u, "stats", {})
    done = set(stats.get("missions_done", []))
    if mid in done:
        await _reply(update, "✅ Already claimed that mission.")
        return
    economy.add_coins(uid(update), mission[2])
    economy.add_xp(uid(update), mission[3])
    done.add(mid)
    stats["missions_done"] = list(done)
    db.set_json(uid(update), "stats", stats)
    await _reply(update, f"✅ *{mission[1]}* complete! +{mission[2]}🪙 / +{mission[3]}XP",
                 kbd([[("📋 Missions", "quests")]]))


async def missions(update, context):
    await quests(update, context)


# ============================ Market / Trade / Auction ============================
async def market(update, context):
    await _reply(update,
        "🏪 *Marketplace* — browse player listings & auction rare items!\n"
        "🚧 Live trading is in beta. Use /trade to propose a swap and /auction to list an item.",
        kbd([[("🎒 Inventory", "inv")]]))


async def trade(update, context):
    if context.args and len(context.args) >= 2:
        try:
            target = int(context.args[0]); amt = int(context.args[1])
        except ValueError:
            await _reply(update, "Usage: /trade <user_id> <amount>")
            return
        u = db.get_user(uid(update))
        if u["coins"] < amt or amt <= 0:
            await _reply(update, "❌ Invalid amount or not enough coins.")
            return
        economy.add_coins(uid(update), -amt)
        economy.add_coins(target, amt)
        await _reply(update, f"💸 Traded *{amt}🪙* to user `{target}`. (Demo: trust-based)")
        return
    await _reply(update, "💱 *Trade & Auction*\nUsage: `/trade <user_id> <amount>`\n"
                  "Full player-to-player marketplace + auctions coming soon! 🚧")


async def auction(update, context):
    await _reply(update, "🔨 *Auctions* — list rare pets/items for bidding!\n🚧 Auction house launching soon. Meanwhile /trade works for direct swaps.")


# ============================ Bank ============================
async def bank(update, context):
    u = db.get_user(uid(update))
    stats = db.get_json(u, "stats", {})
    banked = stats.get("bank", 0)
    if context.args:
        cmd = context.args[0].lower()
        if cmd == "deposit" and len(context.args) > 1:
            try: amt = int(context.args[1])
            except ValueError: amt = 0
            if 0 < amt <= u["coins"]:
                economy.add_coins(uid(update), -amt)
                stats["bank"] = banked + amt
                db.set_json(uid(update), "stats", stats)
                await _reply(update, f"🏦 Deposited *{amt}🪙*. Safe & sound!")
                return
            await _reply(update, "❌ Invalid deposit amount.")
            return
        if cmd == "withdraw" and len(context.args) > 1:
            try: amt = int(context.args[1])
            except ValueError: amt = 0
            if 0 < amt <= banked:
                economy.add_coins(uid(update), amt)
                stats["bank"] = banked - amt
                db.set_json(uid(update), "stats", stats)
                await _reply(update, f"🏦 Withdrew *{amt}🪙*.")
                return
            await _reply(update, "❌ Invalid withdrawal amount.")
            return
        if cmd == "collect":
            interest = max(1, int(banked * 0.01))
            economy.add_coins(uid(update), interest)
            await _reply(update, f"🏦 Collected *{interest}🪙* interest!")
            return
    await _reply(update, f"🏦 *Bank* — your vault: *{banked}🪙*\n"
                  "Commands: `/bank deposit <amt>` · `/bank withdraw <amt>` · `/bank collect` (1% daily interest)",
                  kbd([[("💰 Wallet", "wallet")]]))


# ============================ Guild / Friends / Gift ============================
async def guild(update, context):
    g = db.meta_get("guilds", {})
    if context.args:
        cmd = context.args[0].lower()
        u = uid(update)
        if cmd == "create" and len(context.args) > 1:
            name = " ".join(context.args[1:])
            gid = name.lower().replace(" ", "_")
            g[gid] = {"name": name, "members": [u], "coins": 0}
            db.meta_set("guilds", g)
            await _reply(update, f"🛡️ Created guild *{name}*! Invite friends with `/guild join {gid}`")
            return
        if cmd == "join" and len(context.args) > 1:
            gid = context.args[1]
            if gid in g and u not in g[gid]["members"]:
                g[gid]["members"].append(u)
                db.meta_set("guilds", g)
                await _reply(update, f"🤝 Joined *{g[gid]['name']}* ({len(g[gid]['members'])} members)!")
                return
            await _reply(update, "❌ Guild not found.")
            return
    lines = "\n".join(f"🛡️ {v['name']} — {len(v['members'])} members" for v in g.values()) or "_No guilds yet._"
    await _reply(update, f"🛡️ *Guilds*\n{lines}\n\nCreate: `/guild create <name>` · Join: `/guild join <id>`")


async def friends(update, context):
    await _reply(update, "👫 *Friends* — invite buddies with your referral!\n"
                  "Every friend who does /start earns you both a bonus. 🎉\n🚧 Full friend list & co-op missions coming soon!")


async def gift(update, context):
    if context.args and len(context.args) >= 2:
        try:
            target = int(context.args[0]); amt = int(context.args[1])
        except ValueError:
            await _reply(update, "Usage: /gift <user_id> <amount>")
            return
        u = db.get_user(uid(update))
        if amt <= 0 or u["coins"] < amt:
            await _reply(update, "❌ Not enough coins to gift.")
            return
        economy.add_coins(uid(update), -amt)
        economy.add_coins(target, amt)
        await _reply(update, f"🎁 Gifted *{amt}🪙* to user `{target}`! Spreading joy ⚡")
        return
    await _reply(update, "🎁 *Gift* — share coins with friends!\nUsage: `/gift <user_id> <amount>`")


# ============================ RPG / Battle / Boss / Pet battles ============================
async def rpg(update, context):
    await _reply(update, "⚔️ *RPG Adventures* — dungeons, monster hunts & pet battles!\n"
                  "🚧 Full RPG engine (turn-based battles, loot, bosses) is on the roadmap. "
                  "For now, level up via /daily, /quests & /games, and collect /pet! 🐉")


async def battle(update, context):
    u = db.get_user(uid(update))
    pets = db.get_json(u, "pets", [])
    power = sum(p["power"] for p in pets)
    if power == 0:
        await _reply(update, "⚔️ *PvP Battle* — you need a pet first! Catch one with /pet.")
        return
    win = random.random() < min(0.85, 0.4 + power / 100)
    reward = random.randint(50, 200)
    if win:
        economy.add_coins(uid(update), reward)
        economy.add_xp(uid(update), 15)
        out = f"⚔️ Your team (power {power}) WINS! +{reward}🪙 🏆"
    else:
        out = f"⚔️ Tough fight — your team (power {power}) lost this round. Train more pets! 💪"
    await _reply(update, out, kbd([[("🐾 Pets", "pet"), ("🎮 Games", "games")]]))


async def boss(update, context):
    u = db.get_user(uid(update))
    lvl = config.level_from_xp(u["xp"])
    dmg = random.randint(10, 50) * lvl
    reward = random.randint(100, 400)
    economy.add_coins(uid(update), reward)
    economy.add_xp(uid(update), 30)
    await _reply(update, f"🐉 *BOSS RAID!* You dealt *{dmg}* damage and earned *{reward}🪙* +30XP! "
                  "Rally your guild for bigger bosses soon. 🔥",
                  kbd([[("🛡️ Guild", "guild"), ("🎮 Games", "games")]]))


# ============================ Garage / Travel ============================
async def garage(update, context):
    await _reply(update, "🚗 *Garage* — collect vehicles to boost travel speed & unlock missions!\n"
                  "🚧 Vehicle system launching soon. Buy a head-start at /shop (decor & upgrades).")


async def travel(update, context):
    await _reply(update, "✈️ *Travel* — explore worlds, unlock exclusive quests & events!\n"
                  "🚧 Travel map coming soon. Meanwhile, /events shows what's happening now.")


# ============================ Events / Redeem ============================
async def events(update, context):
    u = db.get_user(uid(update))
    st = economy.daily_status(uid(update))
    txt = "🎊 *Current Events*\n\n"
    txt += "🎡 *Lucky Week* — /spin for double mystery rewards!\n"
    txt += f"🔥 *Daily Streak Event* — keep your {st['streak']}-day streak for bonus coins!\n"
    txt += "🏆 *Leaderboard Race* — climb /leaderboard for seasonal rewards!\n\n"
    txt += "New seasonal festivals drop regularly — stay active! ⚡"
    await _reply(update, txt, kbd([[("🎡 Spin", "spin"), ("🏆 Rank", "leaderboard")]]))


async def redeem(update, context):
    if context.args:
        res = games.redeem(uid(update), context.args[0])
        if "error" in res:
            await _reply(update, f"❌ {res['error']}")
            return
        await _reply(update, f"🎟️ Redeemed! +{res['coins']}🪙 & +{res['gems']}💎")
        return
    codes = ", ".join(content.PROMO_CODES.keys())
    await _reply(update, f"🎟️ *Redeem a promo code!*\nUsage: `/redeem <CODE>`\n"
                  f"Try one of: `{codes}`")


# ============================ Settings / Support ============================
async def settings(update, context):
    await _reply(update, "⚙️ *Settings*\n• Notifications: ON 🔔\n• Private profile: OFF\n"
                  "• Language: English\n🚧 Toggle options coming soon — your data stays local & private.")


async def support(update, context):
    await _reply(update, "🛟 *Nova Support*\nHaving fun? Found a bug? "
                  "This is a self-hosted bot — check the project README for setup & the full command list.\n"
                  "Play fair, keep it friendly, and enjoy! ⚡")


# ============================ Free chat ============================
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = uid(update)
    db.get_user(user_id, *uname(update))
    reward = economy.chat_reward(user_id)
    text = update.message.text or ""
    reply = nova_reply(update.effective_chat.id, user_id, text)
    if reward:
        reply += f"\n\n_(+{reward}🪙 for chatting!)_"
    await update.message.reply_text(reply, parse_mode="Markdown")


# ============================ Callback router ============================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    parts = data.split(":")
    tag = parts[0]

    # command alias buttons
    alias = {
        "start": start, "help": help_cmd, "daily": daily, "spin": spin,
        "shop": shop, "inv": inventory, "property": property_menu,
        "pet": pet_menu, "games": games_menu, "leaderboard": leaderboard,
        "quests": quests, "wallet": wallet, "guild": guild, "events": events,
    }
    if tag in alias:
        await alias[tag](update, context); return
    if tag == "buy":
        await buy_prop(update, context, parts[1]); return
    if tag == "upgrade":
        await upgrade_prop(update, context, parts[1]); return
    if tag == "sell":
        await sell_prop(update, context, parts[1]); return
    if tag == "rent":
        await rent_prop(update, context); return
    if tag == "shopbuy":
        await shop_buy(update, context, parts[1]); return
    if tag == "catch":
        await catch(update, context); return
    if tag == "g" and len(parts) > 1:
        await game_pick(update, context, parts[1]); return
    if tag == "cf":
        await cb_coinflip(update, context, parts[1], parts[2]); return
    if tag == "dice":
        await cb_dice(update, context, parts[1]); return
    if tag == "rps":
        await cb_rps(update, context, parts[1]); return
    if tag == "bj":
        await cb_blackjack(update, context, parts[1]); return
    if tag == "sl":
        await cb_slots(update, context, parts[1]); return
    if tag == "guess":
        await cb_guess(update, context, parts[1]); return
    if tag == "quiz":
        await quiz_answer_cb(update, context, parts[1]); return
    if tag == "quest":
        await claim_quest(update, context, parts[1]); return
    # unknown
    await q.edit_message_text("🤖 (unknown button)")
