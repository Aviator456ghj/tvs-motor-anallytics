# Deploying the bot

The bot is a long-running process — it must stay up 24/7 and restart on crash.
Pick **one** of the options below. **Always run a few days in `LIVE=false`
(dry-run) on the server first**, read the logs, then flip to live.

> Before anything: on Delta (Account → API Keys) create a key with **Trading**
> enabled and **whitelist your server's IP**. Put the key/secret in `.env`.
> Never commit `.env` (it's already gitignored).

---

## Option A — Docker (recommended, portable)

On any host with Docker installed:

```bash
git clone <your-repo> && cd delta-liquidity-bot
cp .env.example .env          # edit: API keys, LIVE=false to start
docker compose up -d --build  # builds and runs detached, auto-restarts
docker compose logs -f        # watch it
```

- State (`bot_state.json`) persists in the `bot-data` volume across restarts.
- `restart: unless-stopped` brings it back after crashes and host reboots.
- Update: `git pull && docker compose up -d --build`.
- Go live: set `LIVE=true` in `.env`, then `docker compose up -d` (recreates).
- Stop: `docker compose down`.

---

## Option B — VPS + systemd (recommended for a Linux box)

On a fresh Ubuntu/Debian VPS ($5 droplet is plenty):

```bash
sudo useradd -r -m -d /opt/delta-liquidity-bot botuser
sudo -u botuser -s
cd /opt/delta-liquidity-bot
git clone <your-repo> .
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # edit: API keys, LIVE=false
exit
```

Install the service:

```bash
sudo cp deploy/delta-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now delta-bot
sudo systemctl status delta-bot       # check it's running
journalctl -u delta-bot -f            # live logs
```

- `Restart=always` keeps it alive; `enable` starts it on boot.
- Update: `git pull && sudo systemctl restart delta-bot`.
- Go live: edit `.env` → `LIVE=true`, then `sudo systemctl restart delta-bot`.

---

## Option C — tmux/screen (quick test only, not robust)

On a box you already have running:

```bash
tmux new -s bot
cd delta-liquidity-bot && source .venv/bin/activate
python -m bot.bot
# detach: Ctrl-b then d   |   reattach: tmux attach -t bot
```

No auto-restart — if the process or box dies, the bot stops. Fine for a
dry-run trial, not for unattended live trading.

---

## After deploying — operational checklist

1. **Dry-run first.** Leave `LIVE=false`, watch logs for a day. Confirm it
   prints sensible `SIGNAL` / `PLAN` lines at real swing levels.
2. **Backtest on the server** once: `python -m bot.backtest --tf 1h --bars 1500`.
3. **Verify connectivity & auth:** the startup line should log your product id,
   tick size, and contract value. An auth error means key/secret/IP-whitelist.
4. **Clock matters.** Delta rejects signatures older than 5s — keep server time
   synced: `sudo timedatectl set-ntp true`.
5. **Go live small.** Flip `LIVE=true`, keep `RISK_PCT` modest, watch the first
   real order fill and that the bracket SL/TP attached correctly.
6. **Monitor.** Check logs daily; set `max-size` log rotation (already set for
   Docker; journald handles it for systemd).

## Security
- API key with **Trading** scope only — do **not** enable Withdrawals.
- IP-whitelist the key to your server.
- `.env` stays off git; restrict perms: `chmod 600 .env`.
- Use a non-root user (both options above do).
