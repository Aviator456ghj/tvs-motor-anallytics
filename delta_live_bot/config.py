"""
Configuration for the live breakout-continuation bot.

All secrets come from environment variables - NEVER hardcode an API key
or secret here, and never commit a .env file. See .env.example.
"""
import os

DELTA_BASE_URL = os.environ.get("DELTA_BASE_URL", "https://api.india.delta.exchange")
DELTA_API_KEY = os.environ.get("DELTA_API_KEY", "")
DELTA_API_SECRET = os.environ.get("DELTA_API_SECRET", "")

PRODUCT_SYMBOL = os.environ.get("DELTA_PRODUCT_SYMBOL", "BTCUSD")
RESOLUTION = "1d"

# v1 breakout-continuation parameters (unchanged from breakout_continuation_backtest.py,
# the user explicitly chose to deploy this exact ruleset, not the v2 redesign).
ZIGZAG_THRESHOLD = 0.08
BREAKOUT_BUFFER = 0.002
SL_BUFFER = 0.02
TP_EXTENSION = 1.0

RISK_PCT = float(os.environ.get("RISK_PCT", "0.01"))

# Lets bot.py dry-run the trigger/sizing logic when the wallet-balance call
# can't be authenticated (e.g. this session's IP isn't on Delta's whitelist).
# Unset by default; never used to size or place a real order - that always
# requires a real authenticated balance fetch.
BALANCE_OVERRIDE_USD = os.environ.get("BALANCE_OVERRIDE_USD", "")

# Safety gates. Both must be explicitly set for a real order to ever be placed.
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() != "false"
LIVE_TRADING_CONFIRM = os.environ.get("LIVE_TRADING_CONFIRM", "")  # must equal "I_UNDERSTAND_THE_RISK"

STATE_FILE = os.environ.get("BOT_STATE_FILE", os.path.join(os.path.dirname(__file__), "bot_state.json"))


def live_orders_enabled():
    return (not DRY_RUN) and LIVE_TRADING_CONFIRM == "I_UNDERSTAND_THE_RISK"
