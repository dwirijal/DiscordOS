import asyncpg
import redis.asyncio as redis
import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.pg_pool = None
        self.dragonfly = None

    async def connect(self):
        # 1. Connect PostgreSQL
        try:
            dsn = os.getenv("POSTGRES_DSN")
            if not dsn:
                print("⚠️ POSTGRES_DSN not found in .env. Structured data will be unavailable.")
            else:
                self.pg_pool = await asyncpg.create_pool(dsn)
                print("✅ PostgreSQL Connected (Structured Data)")
        except Exception as e:
            print(f"❌ Postgres Error: {e}")

        # 2. Connect Dragonfly (Redis Protocol)
        try:
            url = os.getenv("DRAGONFLY_URL")
            if not url:
                print("⚠️ DRAGONFLY_URL not found in .env")
                return

            self.dragonfly = redis.from_url(url)
            await self.dragonfly.ping()
            print("✅ Dragonfly Connected (Short-term Memory)")
        except Exception as e:
            print(f"❌ Dragonfly Error: {e}")

    async def close(self):
        if self.pg_pool: 
            await self.pg_pool.close()
            print("🔒 PostgreSQL Connection Closed")
        if self.dragonfly: 
            await self.dragonfly.close()
            print("🔒 Dragonfly Connection Closed")

# Singleton Instance
db = DatabaseManager()
