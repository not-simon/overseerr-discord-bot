import discord
from discord.ext import commands
from bot.config import DISCORD_BOT_TOKEN

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# Import and setup all commands
from bot.commands import search
search.setup(bot)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)