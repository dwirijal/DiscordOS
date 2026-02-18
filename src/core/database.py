import asyncpg
import redis.asyncio as redis
import os
import json
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
                await self.initialize_health_tables()
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

    async def initialize_health_tables(self):
        if not self.pg_pool: return
        query = """
        CREATE TABLE IF NOT EXISTS health_logs (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            metric_type VARCHAR(50) NOT NULL,
            data JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_health_logs_user_type ON health_logs(user_id, metric_type);
        """
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(query)
                print("✅ Health Tables Initialized")
        except Exception as e:
            print(f"❌ Database Init Error: {e}")

    async def log_health_data(self, user_id, metric_type, data):
        if not self.pg_pool: return False
        query = "INSERT INTO health_logs (user_id, metric_type, data) VALUES ($1, $2, $3)"
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(query, user_id, metric_type, json.dumps(data))
            return True
        except Exception as e:
            print(f"❌ Log Health Error: {e}")
            return False

    async def get_recent_health_logs(self, user_id, metric_type, limit=10):
        if not self.pg_pool: return []
        query = """
            SELECT data, created_at FROM health_logs
            WHERE user_id = $1 AND metric_type = $2
            ORDER BY created_at DESC LIMIT $3
        """
        try:
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch(query, user_id, metric_type, limit)
                # Convert Record to dict, parse JSONB string back to dict
                result = []
                for row in rows:
                    entry = dict(row)
                    if isinstance(entry['data'], str):
                        entry['data'] = json.loads(entry['data'])
                    result.append(entry)
                return result
        except Exception as e:
            print(f"❌ Get Health Logs Error: {e}")
            return []

# Singleton Instance
db = DatabaseManager()
