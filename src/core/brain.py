import google.generativeai as genai
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class BrainManager:
    def __init__(self):
        # Setup Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.gemini = genai.GenerativeModel('gemini-1.5-flash')
        else:
            print("⚠️ GEMINI_API_KEY not found in .env")
            self.gemini = None
        
        # Setup Qwen (via OpenAI compatible endpoint)
        qwen_key = os.getenv("QWEN_API_KEY")
        qwen_base = os.getenv("QWEN_API_BASE")

        if qwen_key and qwen_base:
            self.qwen = AsyncOpenAI(
                base_url=qwen_base,
                api_key=qwen_key
            )
        else:
            print("⚠️ Qwen API Key or Base URL not found in .env")
            self.qwen = None

    async def think(self, prompt, model="gemini", context="", images=None):
        text_prompt = f"Context from memory:\n{context}\n\nUser Query: {prompt}"
        
        try:
            if model == "qwen" and not images:
                if not self.qwen:
                    return "❌ Qwen Brain not configured."

                # Pakai Qwen untuk coding/logic keras
                response = await self.qwen.chat.completions.create(
                    model="qwen-2.5-72b", # Sesuaikan nama model di servermu
                    messages=[{"role": "user", "content": text_prompt}]
                )
                return response.choices[0].message.content
            else:
                # Pakai Gemini untuk general chat & creative & VISION
                if self.gemini:
                    if images:
                        # Jika ada gambar, input jadi list [text, image1, image2...]
                        # Pastikan images adalah list
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
            if self.gemini:
                # Gemini Embedding (text-embedding-004 is a good default, or embedding-001)
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
