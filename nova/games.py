"""Game logic for Nova — pure functions returning structured results.

Each game takes a user id (for balances/rewards) and bet/choice where relevant,
and returns a dict describing the outcome so handlers can format a message.
"""
from __future__ import annotations

import random
from . import config, content, db, economy


def _too_poor(user_id: int, bet: int) -> bool:
    return db.get_user(user_id)["coins"] < bet or bet <= 0


# ----------------------------- Coin flip -----------------------------
def coinflip(user_id: int, bet: int, choice: str) -> dict:
    choice = (choice or "heads").lower()
    if choice not in ("heads", "tails", "h", "t"):
        return {"error": "Pick heads or tails."}
    if _too_poor(user_id, bet):
        return {"error": "Not enough coins for that bet."}
    result = random.choice(["heads", "tails"])
    win = (result[0] == choice[0])
    if win:
        economy.add_coins(user_id, bet)
        economy.add_xp(user_id, 5)
        payout = bet * 2
    else:
        economy.add_coins(user_id, -bet)
        payout = 0
    return {"game": "coinflip", "result": result, "win": win,
            "bet": bet, "payout": payout}


# ------------------------------- Dice --------------------------------
def dice(user_id: int, bet: int, guess: int = None) -> dict:
    if _too_poor(user_id, bet):
        return {"error": "Not enough coins for that bet."}
    rolled = random.randint(1, 6)
    if guess is None:
        # simple 2.5x payout on a random roll gamble
        win = rolled >= 4
        mult = 1.8
    else:
        guess = max(1, min(6, int(guess)))
        win = rolled == guess
        mult = 5.0
    if win:
        economy.add_coins(user_id, int(bet * (mult - 1)))
        economy.add_xp(user_id, 6)
        payout = int(bet * mult)
    else:
        economy.add_coins(user_id, -bet)
        payout = 0
    return {"game": "dice", "rolled": rolled, "guess": guess,
            "win": win, "bet": bet, "payout": payout}


# ------------------------- Rock Paper Scissors -----------------------
def rps(user_id: int, choice: str) -> dict:
    choice = (choice or "").lower()
    if choice not in ("rock", "paper", "scissors", "r", "p", "s"):
        return {"error": "Pick rock, paper or scissors."}
    norm = {"r": "rock", "p": "paper", "s": "scissors"}.get(choice, choice)
    bot = random.choice(["rock", "paper", "scissors"])
    beats = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
    if norm == bot:
        outcome = "tie"
    elif beats[norm] == bot:
        outcome = "win"
    else:
        outcome = "lose"
    if outcome == "win":
        economy.add_coins(user_id, 30); economy.add_xp(user_id, 8)
    elif outcome == "tie":
        economy.add_xp(user_id, 2)
    return {"game": "rps", "you": norm, "bot": bot, "outcome": outcome,
            "reward": 30 if outcome == "win" else 0}


# --------------------------- Number guess ---------------------------
def number_guess(user_id: int, guess: int, secret: int = None) -> dict:
    if secret is None:
        secret = random.randint(1, 10)
    try:
        guess = int(guess)
    except (TypeError, ValueError):
        return {"error": "Send a number 1-10."}
    if not (1 <= guess <= 10):
        return {"error": "Guess a number between 1 and 10."}
    if guess == secret:
        economy.add_coins(user_id, 100); economy.add_xp(user_id, 15)
        return {"game": "guess", "win": True, "secret": secret,
                "reward": 100, "done": True}
    hint = "higher" if secret > guess else "lower"
    return {"game": "guess", "win": False, "secret": secret,
            "hint": hint, "done": False}


# ----------------------------- Blackjack -----------------------------
def blackjack(user_id: int, bet: int) -> dict:
    if _too_poor(user_id, bet):
        return {"error": "Not enough coins for that bet."}
    deck = [2,3,4,5,6,7,8,9,10,10,10,10,11] * 4

    def hand_val(cards):
        s = sum(cards)
        aces = cards.count(11)
        while s > 21 and aces:
            s -= 10; aces -= 1
        return s

    player = [random.choice(deck), random.choice(deck)]
    dealer = [random.choice(deck), random.choice(deck)]
    while hand_val(player) < 17:
        player.append(random.choice(deck))
    while hand_val(dealer) < 17:
        dealer.append(random.choice(deck))
    pv, dv = hand_val(player), hand_val(dealer)
    if pv > 21:
        win = False
    elif dv > 21 or pv > dv:
        win = True
    elif pv == dv:
        win = None  # push
    else:
        win = False
    if win is True:
        economy.add_coins(user_id, bet); economy.add_xp(user_id, 10); payout = bet*2
    elif win is None:
        payout = bet  # returned
    else:
        economy.add_coins(user_id, -bet); payout = 0
    return {"game": "blackjack", "player": player, "dealer": dealer,
            "player_val": pv, "dealer_val": dv, "win": win, "bet": bet,
            "payout": payout}


# ------------------------------- Slots ------------------------------
SYMBOLS = ["🍒", "🍋", "🔔", "💎", "7️⃣", "⭐"]
PAYTABLE = {
    "🍒": 2, "🍋": 2, "🔔": 3, "💎": 10, "7️⃣": 20, "⭐": 50,
}
def slots(user_id: int, bet: int) -> dict:
    if _too_poor(user_id, bet):
        return {"error": "Not enough coins for that bet."}
    reels = [random.choice(SYMBOLS) for _ in range(3)]
    counts = {s: reels.count(s) for s in set(reels)}
    mult = 0
    for s, c in counts.items():
        if c == 3:
            mult = max(mult, PAYTABLE[s])
        elif c == 2:
            mult = max(mult, 1)
    win = mult > 0
    if win:
        payout = bet * mult
        economy.add_coins(user_id, payout - bet)  # net
        economy.add_xp(user_id, 7)
    else:
        economy.add_coins(user_id, -bet)
        payout = 0
    return {"game": "slots", "reels": reels, "mult": mult,
            "win": win, "bet": bet, "payout": payout}


# ------------------------------- Quiz -------------------------------
def quiz_question() -> tuple:
    q, a, cat = random.choice(content.TRIVIA)
    return q, a, cat

def quiz_answer(user_id: int, user_ans: str, correct: str) -> dict:
    ok = user_ans.strip().lower() == correct.strip().lower()
    if ok:
        economy.add_coins(user_id, 50); economy.add_xp(user_id, 20)
    return {"win": ok, "correct": correct, "reward": 50 if ok else 0}


# --------------------------- Lucky wheel -----------------------------
def spin_wheel(user_id: int) -> dict:
    labels = [p[0] for p in content.WHEEL_PRIZES]
    weights = [p[2] for p in content.WHEEL_PRIZES]
    idx = random.choices(range(len(labels)), weights=weights, k=1)[0]
    _, value, _ = content.WHEEL_PRIZES[idx]
    label = labels[idx]
    if "coins" in label:
        economy.add_coins(user_id, value); economy.add_xp(user_id, 10)
    elif "gems" in label:
        economy.add_gems(user_id, value); economy.add_xp(user_id, 10)
    elif "XP" in label:
        economy.add_xp(user_id, value)
    elif "Mystery" in label:
        # random small reward
        r = random.choice([("coins", 200), ("gems", 3), ("coins", 80)])
        if r[0] == "coins":
            economy.add_coins(user_id, r[1])
        else:
            economy.add_gems(user_id, r[1])
        economy.add_xp(user_id, 10)
        value = r[1]
        label = f"🎁 Mystery: {r[1]} {r[0]}"
    # streak update handled by caller via claim logic; return result
    return {"label": label, "value": value}


# --------------------------- Pet catching ---------------------------
def catch_pet(user_id: int, pet_key: str = None) -> dict:
    u = db.get_user(user_id)
    if u["coins"] < content.PET_CATCH_COST:
        return {"error": f"Need {content.PET_CATCH_COST} coins to catch a pet."}
    economy.add_coins(user_id, -content.PET_CATCH_COST)
    keys = list(content.PETS.keys())
    if pet_key and pet_key in content.PETS:
        key = pet_key
    else:
        # weighted by rarity (common easier)
        weights = {"Common": 40, "Uncommon": 25, "Rare": 18,
                   "Legendary": 12, "Mythic": 5}
        key = random.choices(keys, weights=[weights[content.PETS[k][2]] for k in keys])[0]
    name, emoji, rarity, power = content.PETS[key]
    # 70% catch success
    success = random.random() < 0.7
    if success:
        pets = db.get_json(u, "pets", [])
        pets.append({"key": key, "name": name, "emoji": emoji,
                     "rarity": rarity, "power": power, "xp": 0, "level": 1})
        db.set_json(user_id, "pets", pets)
        economy.add_xp(user_id, 15)
        return {"success": True, "pet": (name, emoji, rarity)}
    return {"success": False, "pet": (name, emoji, rarity)}


# --------------------------- Property buy ----------------------------
def buy_property(user_id: int, key: str) -> dict:
    if key not in content.PROPERTIES:
        return {"error": "Unknown property type."}
    u = db.get_user(user_id)
    cost = content.property_cost(key, 1)
    if u["coins"] < cost:
        return {"error": f"Need {cost} coins for a {content.PROPERTIES[key][0]}."}
    economy.add_coins(user_id, -cost)
    props = db.get_json(u, "properties", [])
    props.append({"key": key, "level": 1, "bought_at": int(__import__("time").time())})
    db.set_json(user_id, "properties", props)
    economy.add_xp(user_id, 20)
    return {"ok": True, "name": content.PROPERTIES[key][0], "cost": cost,
            "emoji": content.PROPERTIES[key][3]}


def upgrade_property(user_id: int, key: str) -> dict:
    u = db.get_user(user_id)
    props = db.get_json(u, "properties", [])
    match = [p for p in props if p["key"] == key]
    if not match:
        return {"error": f"You don't own a {content.PROPERTIES.get(key,(key,))[0]}."}
    p = match[0]
    lvl = p["level"]
    cost = content.property_cost(key, lvl + 1)
    if u["coins"] < cost:
        return {"error": f"Upgrade costs {cost} coins."}
    economy.add_coins(user_id, -cost)
    p["level"] = lvl + 1
    db.set_json(user_id, "properties", props)
    economy.add_xp(user_id, 10)
    return {"ok": True, "name": content.PROPERTIES[key][0], "level": lvl + 1,
            "cost": cost}


def sell_property(user_id: int, key: str) -> dict:
    u = db.get_user(user_id)
    props = db.get_json(u, "properties", [])
    match = [p for p in props if p["key"] == key]
    if not match:
        return {"error": "You don't own that property."}
    p = match[0]
    refund = int(content.property_cost(key, 1) * 0.5 * p["level"])
    economy.add_coins(user_id, refund)
    props.remove(p)
    db.set_json(user_id, "properties", props)
    return {"ok": True, "name": content.PROPERTIES[key][0], "refund": refund}


# --------------------------- Redeem promo ----------------------------
def redeem(user_id: int, code: str) -> dict:
    code = (code or "").strip().upper()
    if code not in content.PROMO_CODES:
        return {"error": "Invalid promo code."}
    info = content.PROMO_CODES[code]
    u = db.get_user(user_id)
    stats = db.get_json(u, "stats", {})
    used = stats.get("promos", [])
    if info.get("once") and code in used:
        return {"error": "You already used that code."}
    if info.get("coins"):
        economy.add_coins(user_id, info["coins"])
    if info.get("gems"):
        economy.add_gems(user_id, info["gems"])
    used.append(code)
    stats["promos"] = used
    db.set_json(user_id, "stats", stats)
    return {"ok": True, "coins": info.get("coins", 0), "gems": info.get("gems", 0)}
