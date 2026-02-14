# DiscordOS (Python)

This project has been rebuilt using Python (discord.py) and connects to a robust backend infrastructure.

## Infrastructure
This bot requires:
1.  **PostgreSQL** (Port 5432) - Main Database.
2.  **Dragonfly/Redis** (Port 6379) - Caching and high-speed data.

## Setup

1.  **Environment Variables**:
    Ensure `.env` is configured with your Discord Token and Database Credentials:
    ```env
    DISCORD_TOKEN=...
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=...
    REDIS_URL=redis://:password@localhost:6379/0
    ```

2.  **Install Dependencies**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Run the Bot**:
    ```bash
    python bot.py
    ```

## Features
- **Control Station**: Dashboard GUI for quick actions.
- **Quick Dump**: Intelligent parsing of unorganized thoughts.
- **Action Zone**: Persistent Todo list backed by Postgres.
- **Second Brain**: Note logging.