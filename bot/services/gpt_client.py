import os
import httpx
from bot.config import settings

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
API_KEY = settings.openai_api_key

async def ask_gpt(messages: list, model: str = "gpt-3.5-turbo"):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    json_data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(OPENAI_API_URL, json=json_data, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]