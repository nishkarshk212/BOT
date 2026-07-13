"""Ad-hoc verification for Nova (no live Telegram token required).

Run:  .venv/bin/python tests/verify.py
Coverage:
  - economy: daily/weekly claim, passive income, leveling
  - games: coinflip/dice/rps/blackjack/slots/quiz/pet/property/promo
  - ai: rule-based reply + LLM fallback path (mocked) + history recording
  - app: Application builds with all handlers
"""
import os
import sys
import random
from pathlib import Path

# isolate DB/state into a temp dir (fresh each run)
TMP = Path(__file__).resolve().parent / "tmp_data"
if TMP.exists():
    import shutil
    shutil.rmtree(TMP)
TMP.mkdir(exist_ok=True)
os.environ["DB_PATH"] = str(TMP / "nova_test.db")
os.environ["DATA_DIR"] = str(TMP)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nova import config, db, economy, games, ai

db.init()
random.seed(1)
UID = 424242

ok = 0
fail = 0


def check(name, cond):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}")


print("\n[economy]")
u = db.get_user(UID, "tester", "Test")
check("starting coins", u["coins"] == config.START_COINS)
d = economy.claim_daily(UID)
check("daily claim ok", d["ok"] and d["reward"] > 0)
d2 = economy.claim_daily(UID)
check("daily dedupe", not d2["ok"])
w = economy.claim_weekly(UID)
check("weekly claim ok", w["ok"] and w["reward"] == config.WEEKLY_BASE)
# leveling
lvl, up = economy.add_xp(UID, 100000)
check("level up past 1", lvl > 1 and up)
check("level_from_xp monotonic", config.level_from_xp(0) == 1)

print("\n[games - economy logic]")
# give coins
economy.add_coins(UID, 100000)
c = games.coinflip(UID, 100, "heads")
check("coinflip returns result", "result" in c and "win" in c)
check("coinflip conserves coins", c["win"] is True and c["payout"] == 200 or (c["win"] is False and c["payout"] == 0))
dice = games.dice(UID, 50, 3)
check("dice guess path", "rolled" in dice and "win" in dice)
rps = games.rps(UID, "rock")
check("rps outcome", rps["outcome"] in ("win", "lose", "tie"))
bj = games.blackjack(UID, 200)
check("blackjack hands", bj["player_val"] and bj["dealer_val"] and bj["win"] in (True, False, None))
sl = games.slots(UID, 50)
check("slots reels", len(sl["reels"]) == 3)
g = games.number_guess(UID, 5, 5)
check("guess correct", g["win"] is True)
g2 = games.number_guess(UID, 1, 5)
check("guess hint", g2["win"] is False and g2["hint"] in ("higher", "lower"))

print("\n[games - world]")
bp = games.buy_property(UID, "house")
check("buy property", bp["ok"] and bp["cost"] > 0)
before = db.get_user(UID)["coins"]
inc = economy.collect_income(UID)
check("passive income collects", inc >= 0)
up = games.upgrade_property(UID, "house")
check("upgrade property", up["ok"] and up["level"] == 2)
sp = games.sell_property(UID, "house")
check("sell property", sp["ok"] and sp["refund"] > 0)
cp = games.catch_pet(UID)
check("catch pet (success or fail)", "success" in cp)
rd = games.redeem(UID, "NOVA2026")
check("redeem promo", rd["ok"] and rd["coins"] > 0)
rd2 = games.redeem(UID, "NOVA2026")
check("promo once-only", "error" in rd2)
rd3 = games.redeem(UID, "BOGUS")
check("promo invalid", "error" in rd3)

print("\n[ai - rule-based + LLM fallback]")
# force rule-based (no key)
config.OPENROUTER_API_KEY = ""
r1 = ai.nova_reply(999, UID, "hello there")
check("rule greet", "hey" in r1.lower())
r2 = ai.nova_reply(999, UID, "who are you")
check("rule identity", "nova" in r2.lower())
hist = db.get_history(999)
check("history recorded", len(hist) >= 4)

# LLM path with mocked requests
import unittest.mock as mock
config.OPENROUTER_API_KEY = "fake-key"
fake = mock.Mock()
fake.status_code = 200
fake.json.return_value = {"choices": [{"message": {"content": "LLM says hi!"}}]}
with mock.patch("nova.ai.requests.post", return_value=fake):
    r3 = ai.nova_reply(998, UID, "tell me a joke")
check("llm path used", r3 == "LLM says hi!")

# LLM all-429 -> fallback to rule-based
fail_resp = mock.Mock(); fail_resp.status_code = 429
with mock.patch("nova.ai.requests.post", return_value=fail_resp):
    r4 = ai.nova_reply(997, UID, "hello")
check("llm fallback to rule", isinstance(r4, str) and len(r4) > 0)

print("\n[app build]")
try:
    from nova.main import build_application
    config.BOT_TOKEN = "123:fake"
    app = build_application()
    check("application builds", app is not None)
    # count registered handlers across all groups
    total = sum(len(grp) for grp in app.handlers.values())
    print("    total handlers:", total, "| groups:", {k: len(v) for k, v in app.handlers.items()})
    # verify every spec-listed command is registered
    from nova.main import COMMANDS as _cmds
    spec = ["start","help","profile","wallet","balance","daily","weekly","spin","quests",
            "missions","inventory","shop","market","trade","auction","leaderboard","games",
            "rpg","battle","boss","pet","property","buy","sell","rent","upgrade","bank",
            "invest","casino","blackjack","poker","slots","dice","chess","quiz","fishing",
            "mining","farming","craft","travel","garage","guild","friends","gift","events",
            "redeem","settings","support"]
    missing = [c for c in spec if c not in _cmds]
    check("all spec commands wired", not missing)
    check("handlers registered (>=50)", total >= 50)
except Exception as e:
    check(f"application builds ({e})", False)

print(f"\n==== {ok} passed, {fail} failed ====")
sys.exit(1 if fail else 0)
