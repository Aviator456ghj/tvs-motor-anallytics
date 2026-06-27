"""
Read-mostly web dashboard for delta_live_bot.

Shows the status.json snapshot bot.py writes each pass (last bar, the leg
it's currently watching, the most recent trigger) plus the systemd service
state, and lets you start/stop/restart the *service* via a narrowly scoped
sudoers rule (see ../deploy/sudoers-delta-bot). It never edits .env and
never flips DRY_RUN/LIVE_TRADING_CONFIRM - those safety gates stay a
deliberate, manual, SSH-only action. This only controls whether the
already-configured bot is running at all.

If DASHBOARD_USER/DASHBOARD_PASSWORD aren't set, refuses to bind to
anything but localhost - an unauthenticated trading-bot control panel
should never be reachable from the public internet.
"""
import os
import subprocess
import sys
from functools import wraps

from flask import Flask, jsonify, request, render_template

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    DASHBOARD_PORT, DASHBOARD_USER, DASHBOARD_PASSWORD, STATUS_FILE, STATE_FILE,
    PRODUCT_SYMBOL, DRY_RUN, LIVE_TRADING_CONFIRM,
)
from bot import load_status, load_state, get_usd_balance
from delta_client import DeltaClient

SERVICE_NAME = "delta-bot.service"
ALLOWED_ACTIONS = {"start", "stop", "restart"}

app = Flask(__name__)


def auth_configured():
    return bool(DASHBOARD_USER and DASHBOARD_PASSWORD)


def check_auth(username, password):
    return username == DASHBOARD_USER and password == DASHBOARD_PASSWORD


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not auth_configured():
            return view(*args, **kwargs)
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return ("Authentication required", 401,
                    {"WWW-Authenticate": 'Basic realm="delta-live-bot"'})
        return view(*args, **kwargs)
    return wrapped


def service_state():
    try:
        result = subprocess.run(
            ["systemctl", "is-active", SERVICE_NAME],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except (FileNotFoundError, subprocess.SubprocessError):
        return "unavailable"


@app.route("/")
@require_auth
def index():
    return render_template(
        "index.html",
        symbol=PRODUCT_SYMBOL,
        auth_warning=not auth_configured(),
    )


@app.route("/api/status")
@require_auth
def api_status():
    status = load_status()
    state = load_state()
    return jsonify({
        "status": status,
        "last_handled_leg_key": state.get("last_handled_leg_key"),
        "service_state": service_state(),
        "safety": {
            "dry_run": DRY_RUN,
            "live_trading_confirm_set": LIVE_TRADING_CONFIRM == "I_UNDERSTAND_THE_RISK",
        },
    })


@app.route("/api/balance")
@require_auth
def api_balance():
    try:
        client = DeltaClient()
        balance = get_usd_balance(client)
        return jsonify({"ok": True, "balance": balance})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502


@app.route("/api/service/<action>", methods=["POST"])
@require_auth
def api_service_action(action):
    if action not in ALLOWED_ACTIONS:
        return jsonify({"ok": False, "error": f"action must be one of {sorted(ALLOWED_ACTIONS)}"}), 400
    try:
        result = subprocess.run(
            ["sudo", "-n", "systemctl", action, SERVICE_NAME],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return jsonify({
                "ok": False,
                "error": result.stderr.strip() or result.stdout.strip() or "systemctl failed",
                "hint": "check deploy/sudoers-delta-bot is installed on this host",
            }), 502
        return jsonify({"ok": True, "service_state": service_state()})
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        return jsonify({"ok": False, "error": str(e)}), 502


if __name__ == "__main__":
    host = "0.0.0.0" if auth_configured() else "127.0.0.1"
    if not auth_configured():
        print("WARNING: DASHBOARD_USER/DASHBOARD_PASSWORD not set in .env - "
              "binding to 127.0.0.1 only. Set both and restart to expose this "
              "dashboard beyond localhost.", file=sys.stderr)
    app.run(host=host, port=DASHBOARD_PORT)
