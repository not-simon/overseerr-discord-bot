import os
import aiohttp
import asyncio
from dotenv import load_dotenv
load_dotenv()


OVERSEERR_URL = os.environ.get("OVERSEERR_URL")
OVERSEERR_API_KEY = os.environ.get("OVERSEERR_API_KEY")

async def test_overseerr():
    async with aiohttp.ClientSession() as session:
        headers = {"X-Api-Key": OVERSEERR_API_KEY}
        async with session.get(f"{OVERSEERR_URL}/api/v1/status", headers=headers) as resp:
            print("Overseerr status:", resp.status)
            print(await resp.json())

# Test it directly (for now)
if __name__ == "__main__":
    asyncio.run(test_overseerr())
