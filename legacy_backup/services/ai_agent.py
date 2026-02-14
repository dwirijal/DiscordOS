import aiohttp
import logging
import json
import os

logger = logging.getLogger('ai_agent')

# N8N Webhook URL - Can be overridden by env
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/gemini-chat")

class AIAgent:
    @staticmethod
    async def ask_n8n(user_id: str, username: str, query: str, context: dict = None):
        """
        Sends a query to n8n for processing by Gemini/Qdrant.
        """
        if context is None:
            context = {}
            
        payload = {
            "user_id": str(user_id),
            "username": username,
            "query": query,
            "timestamp": "now", # n8n can generate this, but useful for logs
            "context": context
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(N8N_WEBHOOK_URL, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Expect n8n to return { "response": "..." }
                        return data.get("text", "⚠️ **Signal Lost**: N8N received it, but returned no text.")
                    else:
                        logger.error(f"N8N Webhook Failed: {response.status}")
                        return f"❌ **System Error**: N8N Webhook rejected request ({response.status})."
                        
        except Exception as e:
            logger.error(f"AI Agent Error: {e}")
            return f"❌ **Connection Error**: Could not reach Neural Core (n8n). Is it running?\n`{e}`"

ai_agent = AIAgent()
