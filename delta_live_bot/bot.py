"""
Main loop for the live v1 breakout-continuation bot.

Each pass: pull daily BTCUSD candles from Delta -> run the same pivot /
breakout logic as the backtest -> if a not-yet-handled confirmed leg has
broken out, size a position off live wallet balance and place a real
bracket order (only if config.live_orders_enabled()), else log a DRY RUN
line. The handled leg's key is persisted so the same leg never fires twice.

Run modes:
    python3 bot.py            single pass, then exit (cron-friendly)
    python3 bot.py --loop N   pass, sleep N seconds, repeat forever

This process is not a substitute for always-on infra: if the container
running it dies, it stops watching. For genuine 24/7 monitoring, run this
on a host you control (systemd service, tmux, etc.), not inside an
ephemeral session.
"""
import argparse
import json
import os
import sys
import time

from config import (
    PRODUCT_SYMBOL, RESOLUTION, RISK_PCT, STATE_FILE, STATUS_FILE, live_orders_enabled, DRY_RUN,
    BALANCE_OVERRIDE_USD,
)
from delta_client import DeltaClient
from strategy import evaluate_latest_leg, current_watch

LOOKBACK_DAYS = 400  # enough daily bars for ZIGZAG_THRESHOLD=8% pivots to form


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_handled_leg_key": None}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE) as f:
            return json.load(f)
    return {}


def save_status(**fields):
    """Merges `fields` into the persisted status snapshot rather than
    replacing it wholesale, so `last_trigger` survives the many passes in
    between that find nothing new - the dashboard needs to keep showing the
    most recent trigger, not just whatever happened on the last pass."""
    status = load_status()
    status.update(fields)
    status["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)


def fetch_daily_bars(client, symbol):
    now = int(time.time())
    start = now - LOOKBACK_DAYS * 86400
    resp, path = client.get_candles(symbol, RESOLUTION, start, now)
    if resp is None or resp.status_code != 200:
        raise RuntimeError(f"candle fetch failed (path={path}): "
                            f"{resp.status_code if resp else 'no response'} {resp.text[:300] if resp else ''}")

    raw = resp.json().get("result", [])
    if not raw:
        raise RuntimeError(f"candle fetch ok but empty result from {path}")

    bars = []
    for c in raw:
        ts = c.get("time", c.get("t"))
        bars.append({
            "date": time.strftime("%Y-%m-%d", time.gmtime(ts)) if ts else None,
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"]),
            "_time": ts,
        })
    bars.sort(key=lambda b: (b["_time"] is None, b["_time"]))
    return bars


def size_position(client, product, entry_price, sl_price, balance_usd):
    """Same convention as the backtest: risk_amount = balance * RISK_PCT,
    units = risk_amount / |entry - sl| (in the underlying currency, BTC for
    BTCUSD). contract_value on Delta's vanilla BTCUSD product is denominated
    in contract_unit_currency (BTC), NOT USD - confirmed live via
    get_product(), not assumed - so contracts = units / contract_value."""
    risk_amount = balance_usd * RISK_PCT
    stop_distance = abs(entry_price - sl_price)
    if stop_distance <= 0:
        raise ValueError("zero stop distance, refusing to size a position")

    units = risk_amount / stop_distance
    notional_usd = units * entry_price

    contract_value = float(product.get("contract_value", 1) or 1)
    contracts = max(1, round(units / contract_value))
    return contracts, risk_amount, notional_usd


def get_usd_balance(client):
    if DRY_RUN and BALANCE_OVERRIDE_USD:
        print(f"[DRY RUN] using BALANCE_OVERRIDE_USD={BALANCE_OVERRIDE_USD} instead of a live wallet fetch")
        return float(BALANCE_OVERRIDE_USD)

    resp = client.get_wallet_balances()
    if resp.status_code != 200:
        raise RuntimeError(f"wallet balance fetch failed: {resp.status_code} {resp.text[:300]}")
    for bal in resp.json().get("result", []):
        if bal.get("asset_symbol") in ("USD", "USDT"):
            return float(bal.get("balance", 0))
    raise RuntimeError("no USD/USDT balance entry found in wallet response")


def watch_summary(watch):
    if watch is None:
        return None
    return {
        "direction": watch["direction"],
        "swing_origin": round(watch["swing_origin"], 2),
        "swing_point": round(watch["swing_point"], 2),
        "breakout_level": round(watch["breakout_level"], 2),
        "sl": round(watch["sl"], 2),
        "tp": round(watch["tp"], 2),
        "leg_key": watch["leg_key"],
    }


def run_once(client):
    bars = fetch_daily_bars(client, PRODUCT_SYMBOL)
    state = load_state()
    last_bar = {"date": bars[-1]["date"], "close": bars[-1]["close"]}
    watch = current_watch(bars)

    setup = evaluate_latest_leg(bars, state.get("last_handled_leg_key"))
    if setup is None:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] no new triggered breakout. "
              f"last bar: {bars[-1]['date']} close={bars[-1]['close']}")
        save_status(symbol=PRODUCT_SYMBOL, dry_run=DRY_RUN, last_bar=last_bar,
                    watching=watch_summary(watch), last_pass_message="no new triggered breakout")
        return

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] TRIGGER: {setup['direction']} {PRODUCT_SYMBOL} "
          f"breakout={setup['breakout_level']:.2f} sl={setup['sl']:.2f} tp={setup['tp']:.2f} "
          f"triggered on {setup['triggered_date']}")

    product = client.get_product(PRODUCT_SYMBOL)
    if product is None:
        print(f"ABORT: could not find product spec for {PRODUCT_SYMBOL}, not sizing or placing an order.")
        save_status(symbol=PRODUCT_SYMBOL, dry_run=DRY_RUN, last_bar=last_bar,
                    watching=watch_summary(watch),
                    last_pass_message=f"ABORT: no product spec for {PRODUCT_SYMBOL}")
        return

    balance = get_usd_balance(client)
    contracts, risk_amount, notional_usd = size_position(
        client, product, setup["breakout_level"], setup["sl"], balance
    )
    print(f"balance=${balance:,.2f} risk=${risk_amount:,.2f} notional=${notional_usd:,.2f} "
          f"-> {contracts} contract(s)")

    side = "buy" if setup["direction"] == "LONG" else "sell"

    last_trigger = {
        "triggered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "direction": setup["direction"], "triggered_date": setup["triggered_date"],
        "breakout_level": round(setup["breakout_level"], 2), "sl": round(setup["sl"], 2),
        "tp": round(setup["tp"], 2), "contracts": contracts,
        "risk_amount": round(risk_amount, 2), "notional_usd": round(notional_usd, 2),
        "balance": round(balance, 2), "dry_run": DRY_RUN,
    }

    if live_orders_enabled():
        resp = client.place_order(
            product_id=product["id"], side=side, size=contracts, order_type="market_order",
            bracket_stop_loss_price=round(setup["sl"], 2),
            bracket_take_profit_price=round(setup["tp"], 2),
        )
        print(f"LIVE ORDER placed: {resp.status_code} {resp.text[:500]}")
        last_trigger["order_status_code"] = resp.status_code
        if resp.status_code not in (200, 201):
            print("Order placement failed, NOT marking this leg as handled - will retry next pass.")
            last_trigger["outcome"] = "order_failed_will_retry"
            save_status(symbol=PRODUCT_SYMBOL, dry_run=DRY_RUN, last_bar=last_bar,
                        watching=watch_summary(watch), last_trigger=last_trigger,
                        last_pass_message="order placement failed, will retry")
            return
        last_trigger["outcome"] = "live_order_placed"
    else:
        print(f"[DRY RUN] (DRY_RUN={DRY_RUN}) would place {side} {contracts} contracts of "
              f"{PRODUCT_SYMBOL} with SL={setup['sl']:.2f} TP={setup['tp']:.2f}. "
              f"Set DRY_RUN=false and LIVE_TRADING_CONFIRM=I_UNDERSTAND_THE_RISK to go live.")
        last_trigger["outcome"] = "dry_run_only"

    state["last_handled_leg_key"] = setup["leg_key"]
    save_state(state)
    save_status(symbol=PRODUCT_SYMBOL, dry_run=DRY_RUN, last_bar=last_bar,
                watching=watch_summary(watch), last_trigger=last_trigger,
                last_pass_message=f"TRIGGER handled: {setup['direction']} ({last_trigger['outcome']})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", type=int, default=0, metavar="SECONDS",
                         help="if set, repeat forever sleeping this many seconds between passes")
    args = parser.parse_args()

    client = DeltaClient()

    while True:
        try:
            run_once(client)
        except Exception as e:
            print(f"ERROR during pass: {e}", file=sys.stderr)
            save_status(last_pass_message=f"ERROR: {e}", dry_run=DRY_RUN, symbol=PRODUCT_SYMBOL)
        if args.loop <= 0:
            break
        time.sleep(args.loop)


if __name__ == "__main__":
    main()
