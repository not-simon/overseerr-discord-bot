import logging
logging.basicConfig(level=logging.INFO)
from discord import app_commands
from bot.config import DISCORD_CHANNEL_ID
from bot.overseerr.api import overseerr_search


def setup(bot):
    @bot.tree.command(name="search", description="Search for a movie or TV show in Overseerr")
    async def search(interaction, query: str):
        logging.info(f"User {interaction.user} searched for: {query!r} in channel {interaction.channel_id}")
        if interaction.channel_id != DISCORD_CHANNEL_ID:
            await interaction.response.send_message(
                "This command can only be used in the designated channel.", ephemeral=True
            )
            logging.info("Blocked command in wrong channel.")
            return

        await interaction.response.defer()
        try:
            results = await overseerr_search(
                query, 
                requester_name=interaction.user.display_name,
                requester_avatar_url=interaction.user.display_avatar.url
            )
            if not results:
                await interaction.followup.send(f"No results found for '{query}'.")
                logging.warning(f"No results for: {query!r}")
                return

            for result in results[:3]:
                embed = result["embed"]
                await interaction.followup.send(embed=embed)
                logging.info(f"Sent embed for: {embed.title}")
        except Exception as e:
            logging.exception(f"Error handling /search command: {e}")
            await interaction.followup.send("There was an error while searching. Please try again later.")
