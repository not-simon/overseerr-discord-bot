import os
from dotenv import load_dotenv
load_dotenv()

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
OVERSEERR_API_KEY = os.environ["OVERSEERR_API_KEY"]
OVERSEERR_URL = os.environ["OVERSEERR_URL"]
DISCORD_CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID"])
