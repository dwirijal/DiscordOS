import google.generativeai as genai
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
from src.core.database import db

load_dotenv()

class BrainManager:
    def __init__(self):
        self.gemini = None
        self.qwen = None # This handles OpenAI/Ollama compatible endpoints
        self.config = {}

    async def initialize(self):
        print("🧠 Initializing Brain...")
        await self.load_config()

    async def load_config(self):
        # 1. Load from DB
        settings = await db.get_all_settings()
        self.config = settings

        # 2. Setup Gemini
        gemini_key = settings.get("gemini_api_key") or os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                self.gemini = genai.GenerativeModel('gemini-1.5-flash')
                # print("✨ Gemini Online")
            except Exception as e:
                print(f"❌ Gemini Setup Error: {e}")
                self.gemini = None
        else:
            self.gemini = None
        
        # 3. Setup OpenAI/Ollama
        # Map old env vars QWEN_* to generic OpenAI client
        openai_key = settings.get("openai_api_key") or os.getenv("QWEN_API_KEY") or "ollama"
        openai_base = settings.get("openai_base_url") or os.getenv("QWEN_API_BASE")

        if openai_key and openai_base:
            try:
                self.qwen = AsyncOpenAI(
                    base_url=openai_base,
                    api_key=openai_key
                )
                # print(f"🤖 OpenAI/Ollama Online ({openai_base})")
            except Exception as e:
                print(f"❌ OpenAI/Ollama Setup Error: {e}")
                self.qwen = None
        else:
            self.qwen = None

    async def reload(self):
        await self.load_config()

    async def think(self, prompt, model=None, context="", images=None):
        text_prompt = f"Context from memory:\n{context}\n\nUser Query: {prompt}"
        
        # Determine default model from config if not specified
        if model is None:
            model = self.config.get("ai_provider", "gemini")

        # Determine model usage
        use_openai = model in ["qwen", "ollama", "local", "openai"]

        try:
            if use_openai and not images:
                if not self.qwen:
                    return "❌ OpenAI/Ollama Brain not configured."

                model_name = self.config.get("openai_model") or "qwen-2.5-72b"

                response = await self.qwen.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": text_prompt}]
                )
                return response.choices[0].message.content
            else:
                # Default to Gemini (handles images and text)
                if self.gemini:
                    if images:
                        if not isinstance(images, list):
                            images = [images]
                        content = [text_prompt] + images
                        response = await self.gemini.generate_content_async(content)
                    else:
                        response = await self.gemini.generate_content_async(text_prompt)
                    return response.text
                else:
                    return "❌ Gemini Brain not configured."
        except Exception as e:
            return f"❌ Brain Error: {e}"

    async def embed_content(self, text):
        try:
            # Check config for preferred embedding provider
            provider = self.config.get("embed_provider", "gemini")

            if provider in ["openai", "ollama"] and self.qwen:
                model = self.config.get("embed_model", "text-embedding-3-small")
                # OpenAI/Ollama Embedding
                response = await self.qwen.embeddings.create(
                    input=text,
                    model=model
                )
                return response.data[0].embedding

            elif self.gemini:
                # Gemini Embedding
                result = await genai.embed_content_async(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="retrieval_query"
                )
                return result['embedding']
            return None
        except Exception as e:
            print(f"❌ Embedding Error: {e}")
            return None

brain = BrainManager()
