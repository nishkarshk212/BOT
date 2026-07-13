"""Static content catalogs for Nova's virtual world."""
from __future__ import annotations

# ----------------------------- PROPERTIES -----------------------------
# key: (name, base_cost, base_income/min, emoji, tier)
PROPERTIES = {
    "house":      ("House",        500,     2,   "🏠", 1),
    "apartment":  ("Apartment",    900,     4,   "🏢", 1),
    "cafe":       ("Cafe",         1500,    7,   "☕", 2),
    "restaurant": ("Restaurant",   3000,    14,  "🍽️", 2),
    "farm":       ("Farm",         2500,    10,  "🌾", 2),
    "villa":      ("Villa",        8000,    32,  "🏡", 3),
    "factory":    ("Factory",      12000,   45,  "🏭", 3),
    "mall":       ("Mall",         25000,   90,  "🛍️", 4),
    "hotel":      ("Hotel",        40000,   150, "🏨", 4),
    "office":     ("Office",       55000,   200, "🏢", 4),
    "nightclub":  ("Nightclub",    70000,   260, "🪩", 5),
    "yacht":      ("Luxury Yacht", 120000,  420, "🛥️", 5),
    "island":     ("Private Island",200000, 700, "🏝️", 6),
    "stadium":    ("Stadium",      350000,  1200,"🏟️", 6),
    "airport":    ("Airport",      600000,  2000,"✈️", 7),
    "castle":     ("Castle",       900000,  3200,"🏰", 7),
    "spacestation":("Space Station",5000000, 18000,"🛰️",8),
}
UPGRADE_COST_MULT = 0.8   # cost to upgrade = base_cost * tier * 0.8
UPGRADE_INCOME_MULT = 1.6  # each level multiplies income

def property_income_per_min(key, level):
    base = PROPERTIES[key][2]
    return int(base * (UPGRADE_INCOME_MULT ** (level - 1)))

def property_cost(key, level):
    base = PROPERTIES[key][1]
    return int(base * (1 + 0.5 * (level - 1)))

# ------------------------------- SHOP -------------------------------
# key: (name, type, price(coins), emoji, desc)
SHOP_ITEMS = {
    "mystery_box":  ("Mystery Box",   "consumable", 150,   "🎁", "Contains a random surprise!"),
    "lucky_charm":  ("Lucky Charm",   "boost",      400,   "🍀", "+15% casino win chance for 1h (symbolic)."),
    "gem_pouch":    ("Gem Pouch",     "consumable", 900,   "💎", "Grants 5 gems."),
    "xp_boost":     ("XP Booster",    "boost",      600,   "⚡", "Double XP from games for 1h (symbolic)."),
    "pet_food":     ("Pet Food",      "consumable", 80,    "🦴", "Feed your pets to gain XP."),
    "furniture":    ("Furniture Set", "decor",      350,   "🛋️", "Decorate a property (+income)."),
    "security":     ("Security System","upgrade",  500,   "🔒", "Protects a property from raids."),
    "workers":      ("Hire Workers",  "upgrade",    700,   "👷", "Auto-boost a property's income."),
    "skin_nova":    ("Nova Skin: Neon","skin",      1200,  "🌈", "A flashy cosmetic for you."),
    "badge_pro":    ("Pro Badge",     "badge",      2500,  "🏅", "Show off your dedication."),
}

# ------------------------------- PETS --------------------------------
# key: (name, emoji, rarity, base_power)
PETS = {
    "slime":   ("Slime",   "🟢", "Common",   5),
    "cat":     ("Cat",     "🐱", "Common",   8),
    "fox":     ("Fox",     "🦊", "Uncommon", 12),
    "dragon":  ("Dragon",  "🐉", "Legendary",30),
    "phoenix": ("Phoenix", "🦅", "Mythic",   45),
    "robot":   ("Robot",   "🤖", "Rare",     18),
}
PET_CATCH_COST = 100  # coins to attempt a catch

# ------------------------------ TRIVIA -------------------------------
TRIVIA = [
    ("How many points is a royal flush worth in poker?", "It's the best hand! (no points, just wins)", "poker"),
    ("What does 'XP' stand for in games?", "Experience Points", "rpg"),
    ("Which property generates the most passive income?", "The Space Station 🛰️", "property"),
    ("In roulette, what color is the number 0?", "Green", "casino"),
    ("What do you use /daily for?", "To claim your daily login bonus", "daily"),
    ("Name a legendary pet in Nova.", "Dragon 🐉 or Phoenix 🦅", "pet"),
    ("What command opens the lucky wheel?", "/spin", "spin"),
    ("What currency can you buy with a Gem Pouch?", "Gems 💎", "shop"),
]

# --------------------------- DAILY MISSIONS ---------------------------
# (id, text, reward_coins, reward_xp)
DAILY_MISSIONS = [
    ("m1", "Play any casino game once", 60, 20),
    ("m2", "Spin the lucky wheel", 50, 15),
    ("m3", "Try to catch a pet", 80, 25),
    ("m4", "Send Nova 5 chat messages", 40, 30),
    ("m5", "Check your /profile", 30, 10),
]

# --------------------------- ACHIEVEMENTS -----------------------------
ACHIEVEMENTS = {
    "first_coins": ("💸 First Coins", "Earn your first 100 coins"),
    "high_roller": ("🎰 High Roller", "Bet 1,000 coins in the casino"),
    "collector":   ("🐉 Collector", "Own 3 different pets"),
    "tycoon":      ("🏙️ Tycoon", "Own 5 properties"),
    "level10":     ("⭐ Rising Star", "Reach level 10"),
    "gambler":     ("🃏 Gambler", "Play 25 games"),
}

# --------------------------- PROMO CODES ------------------------------
PROMO_CODES = {
    "NOVA2026": {"coins": 500, "gems": 3, "once": True},
    "WELCOME":  {"coins": 200, "gems": 1, "once": True},
    "LUCKY":    {"coins": 1000, "gems": 0, "once": True},
}
