import os
from dotenv import load_dotenv

load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0))

# Channel IDs
MAIN_DASHBOARD_ID = int(os.getenv('MAIN_DASHBOARD_CHANNEL_ID', 0))
QUICK_DUMP_ID = int(os.getenv('QUICK_DUMP_CHANNEL_ID', 0))
ACTIVE_TODOS_ID = int(os.getenv('ACTIVE_TODOS_CHANNEL_ID', 0))
AGENDA_CALENDAR_ID = int(os.getenv('AGENDA_CALENDAR_CHANNEL_ID', 0))
FOCUS_SESSION_ID = int(os.getenv('FOCUS_SESSION_CHANNEL_ID', 0))
NOTES_STREAM_ID = int(os.getenv('NOTES_STREAM_CHANNEL_ID', 0))
BOOKMARKS_ID = int(os.getenv('BOOKMARKS_CHANNEL_ID', 0))
IDEAS_SPARK_ID = int(os.getenv('IDEAS_SPARK_CHANNEL_ID', 0))
FINANCE_LOG_ID = int(os.getenv('FINANCE_LOG_CHANNEL_ID', 0))
HABIT_TRACKER_ID = int(os.getenv('HABIT_TRACKER_CHANNEL_ID', 0))
SHOPPING_LIST_ID = int(os.getenv('SHOPPING_LIST_CHANNEL_ID', 0))
SYSTEM_LOGS_ID = int(os.getenv('SYSTEM_LOGS_CHANNEL_ID', 0))
CLOUD_STORAGE_ID = int(os.getenv('CLOUD_STORAGE_CHANNEL_ID', 0))
DEV_PLAYGROUND_ID = int(os.getenv('DEV_PLAYGROUND_CHANNEL_ID', 0))
ACTIVE_PROJECTS_ID = int(os.getenv('ACTIVE_PROJECTS_CHANNEL_ID', 0))
DEEP_FOCUS_ID = int(os.getenv('DEEP_FOCUS_CHANNEL_ID', 0))
VOICE_NOTES_ID = int(os.getenv('VOICE_NOTES_CHANNEL_ID', 0))

# Database Configuration
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')

# Redis Configuration
REDIS_URL = os.getenv('REDIS_URL')
