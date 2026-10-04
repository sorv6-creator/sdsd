import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]

SUBSCRIBE_CHANNEL = os.getenv("SUBSCRIBE_CHANNEL", "https://t.me/EGE_Market")
SUBSCRIBE_CHANNEL_ID = os.getenv("SUBSCRIBE_CHANNEL_ID", "@EGE_Market")
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@mishaykazahpik")

TERMS_URL = os.getenv("TERMS_URL", "https://telegra.ph")
REVIEWS_URL = os.getenv("REVIEWS_URL", "https://t.me/EGE_Market")
REVIEWS_FAQ_URL = os.getenv("REVIEWS_FAQ_URL", "https://t.me/EGE_Market")

REFERRAL_JOIN_REWARD = int(os.getenv("REFERRAL_JOIN_REWARD", "10"))
REFERRAL_PURCHASE_REWARD = int(os.getenv("REFERRAL_PURCHASE_REWARD", "50"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env")