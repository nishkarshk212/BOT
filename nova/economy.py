"""Economy helpers: coins, gems, XP, levels, passive income, daily/weekly."""
from __future__ import annotations

import time
from datetime import datetime, timezone

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
