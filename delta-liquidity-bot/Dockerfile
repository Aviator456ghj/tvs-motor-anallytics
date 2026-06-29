FROM python:3.12-slim

# System certs for HTTPS to Delta
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY bot/ ./bot/

# State file lives here; mount a volume to persist across restarts
ENV STATE_FILE=/data/bot_state.json
VOLUME ["/data"]

# Reads config from environment (pass --env-file .env at run time)
CMD ["python", "-m", "bot.bot"]
