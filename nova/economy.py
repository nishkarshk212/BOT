"""Economy helpers: coins, gems, XP, levels, passive income, daily/weekly."""
from __future__ import annotations

import time
from datetime import datetime, timezone
import secrets

from . import config, content, db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_coins(user_id: int, amount: int) -> int:
    u = db.get_user(user_id)
    new = max(0, u["coins"] + amount)
    db.update_user(user_id, coins=new)
    return new


def add_gems(user_id: int, amount: int) -> int:
    u = db.get_user(user_id)
    new = max(0, u["gems"] + amount)
    db.update_user(user_id, gems=new)
    return new


def add_xp(user_id: int, amount: int):
    """Add XP and return (new_level, leveled_up:bool)."""
    u = db.get_user(user_id)
    new_xp = u["xp"] + amount
    old_lvl = config.level_from_xp(u["xp"])
    new_lvl = config.level_from_xp(new_xp)
    db.update_user(user_id, xp=new_xp)
    return new_lvl, new_lvl > old_lvl


# --- Passive income from properties ---
def collect_income(user_id: int) -> int:
    u = db.get_user(user_id)
    props = db.get_json(u, "properties", [])
    if not props:
        return 0
    stats = db.get_json(u, "stats", {})
    last = stats.get("last_income_ts", int(time.time()))
    now = int(time.time())
    minutes = max(0, (now - last) / 60.0)
    # cap offline accrual to 12 hours so it stays "gamey"
    minutes = min(minutes, 12 * 60)
    total = 0
    for p in props:
        key = p["key"]
        lvl = p.get("level", 1)
        total += content.property_income_per_min(key, lvl)
    earned = int(total * minutes)
    stats["last_income_ts"] = now
    db.set_json(user_id, "stats", stats)
    if earned:
        add_coins(user_id, earned)
    return earned


# --- Daily / Weekly ---
def daily_status(user_id: int) -> dict:
    u = db.get_user(user_id)
    today = _now_iso()[:10]
    last = u["last_daily"]
    streak = u["streak"] or 0
    claimed_today = bool(last and last[:10] == today)
    # determine if streak continues (last claim yesterday)
    if last:
        last_day = last[:10]
        yest = datetime.now(timezone.utc)
        from datetime import timedelta
        yest = (yest - timedelta(days=1)).isoformat()[:10]
        if last_day == yest:
            would_streak = streak + 1
        else:
            would_streak = 1
    else:
        would_streak = 1
    bonus = min(streak, 7) * 20 if not claimed_today else 0
    reward = config.DAILY_BASE + bonus
    return {"claimed_today": claimed_today, "streak": streak,
            "would_streak": would_streak, "reward": reward}


def claim_daily(user_id: int) -> dict:
    st = daily_status(user_id)
    if st["claimed_today"]:
        return {"ok": False, **st}
    new_streak = st["would_streak"]
    add_coins(user_id, st["reward"])
    add_xp(user_id, 25)
    db.update_user(user_id, last_daily=_now_iso(), streak=new_streak)
    return {"ok": True, "reward": st["reward"], "streak": new_streak}


def weekly_status(user_id: int) -> dict:
    u = db.get_user(user_id)
    now = datetime.now(timezone.utc)
    # ISO week number
    iso = now.isocalendar()
    week = f"{iso[0]}-W{iso[1]}"
    last = u["last_weekly"]
    claimed = bool(last and last.startswith(week))
    return {"claimed": claimed, "week": week, "reward": config.WEEKLY_BASE}


def claim_weekly(user_id: int) -> dict:
    st = weekly_status(user_id)
    if st["claimed"]:
        return {"ok": False, **st}
    add_coins(user_id, st["reward"])
    add_xp(user_id, 120)
    db.update_user(user_id, last_weekly=st["week"])
    return {"ok": True, "reward": st["reward"]}


# --- Chat activity reward (rate-limited) ---
def chat_reward(user_id: int) -> int:
    u = db.get_user(user_id)
    now = int(time.time())
    if now - (u["last_chat"] or 0) < config.CHAT_COOLDOWN:
        return 0
    import random
    amt = random.randint(config.CHAT_REWARD_MIN, config.CHAT_REWARD_MAX)
    add_coins(user_id, amt)
    add_xp(user_id, 1)
    db.update_user(user_id, last_chat=now)
    return amt


# --- Achievements ---
def check_achievements(user_id: int) -> list[str]:
    """Evaluate all achievement conditions; grant any newly-earned ones.

    Returns a list of achievement keys that were JUST earned this call.
    """
    from . import content

    u = db.get_user(user_id)
    stats = db.get_json(u, "stats", {})
    earned = set(stats.get("achievements", []))
    level = config.level_from_xp(u["xp"])
    pets = db.get_json(u, "pets", [])
    props = db.get_json(u, "properties", [])
    games_played = stats.get("games_played", 0)

    def grant(key):
        if key not in earned:
            earned.add(key)
            return True
        return False

    newly = []
    # first_coins: reached 100 coins at some point (track peak)
    peak = max(u["coins"], stats.get("peak_coins", 0))
    stats["peak_coins"] = peak
    if peak >= 100 and grant("first_coins"):
        newly.append("first_coins")
    if u["coins"] >= 1000 and grant("high_roller"):
        newly.append("high_roller")
    if len({p["key"] for p in pets}) >= 3 and grant("collector"):
        newly.append("collector")
    if len(props) >= 5 and grant("tycoon"):
        newly.append("tycoon")
    if level >= 10 and grant("level10"):
        newly.append("level10")
    if games_played >= 25 and grant("gambler"):
        newly.append("gambler")

    if newly:
        stats["achievements"] = list(earned)
        db.set_json(user_id, "stats", stats)
        # small reward per achievement
        add_coins(user_id, 100 * len(newly))
        add_xp(user_id, 20 * len(newly))
    return newly


def awarded_achievements(user_id: int) -> list[str]:
    u = db.get_user(user_id)
    return db.get_json(u, "stats", {}).get("achievements", [])


# --- Referrals ---
REFERRER_BONUS = 150
REFEREE_BONUS = 100


def get_referral_code(user_id: int) -> str:
    u = db.get_user(user_id)
    stats = db.get_json(u, "stats", {})
    code = stats.get("ref_code")
    if not code:
        code = f"NOVA{user_id:x}{secrets.token_hex(2).upper()}"
        stats["ref_code"] = code
        db.set_json(user_id, "stats", stats)
    return code


def apply_referral(referrer_id: int, new_user_id: int) -> dict:
    """Credit both sides when `new_user` was referred. One-time per new user."""
    if referrer_id == new_user_id:
        return {"error": "Can't refer yourself."}
    ref_u = db.get_user(referrer_id)
    new_u = db.get_user(new_user_id)
    new_stats = db.get_json(new_u, "stats", {})
    if new_stats.get("referred_by"):
        return {"error": "Already used a referral."}
    # verify code matches referrer's
    ref_stats = db.get_json(ref_u, "stats", {})
    if new_stats.get("ref_code_used") == ref_stats.get("ref_code"):
        return {"error": "Already used this code."}
    add_coins(referrer_id, REFERRER_BONUS)
    add_coins(new_user_id, REFEREE_BONUS)
    add_xp(referrer_id, 25)
    add_xp(new_user_id, 15)
    new_stats["referred_by"] = referrer_id
    new_stats["ref_code_used"] = ref_stats.get("ref_code")
    db.set_json(new_user_id, "stats", new_stats)
    return {"ok": True, "referrer_bonus": REFERRER_BONUS,
            "referee_bonus": REFEREE_BONUS}


def record_game(user_id: int) -> list[str]:
    """Call after any game play: bump counter and evaluate achievements."""
    u = db.get_user(user_id)
    stats = db.get_json(u, "stats", {})
    stats["games_played"] = stats.get("games_played", 0) + 1
    db.set_json(user_id, "stats", stats)
    return check_achievements(user_id)
