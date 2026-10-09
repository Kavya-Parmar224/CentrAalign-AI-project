import asyncio
import os
from openai import AsyncOpenAI

async def main():
    client = AsyncOpenAI(
        base_url='https://generativelanguage.googleapis.com/v1beta/openai/',
        api_key=os.environ.get('GEMINI_API_KEY', 'YOUR_API_KEY_HERE')
    )
    for model_name in ['gemini-3.5-flash', 'gemini-3.1-flash-lite', 'gemini-3.7-flash', 'gemini-flash-latest']:
        try:
            print(f"Testing {model_name}...")
            resp = await client.chat.completions.create(
                model=model_name,
                messages=[{'role': 'user', 'content': 'hi'}]
            )
            print(f"  SUCCESS! {model_name} works.")
            return
        except Exception as e:
            print(f"  FAILED: {e}")

asyncio.run(main())
