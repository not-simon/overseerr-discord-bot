import logging
logging.basicConfig(level=logging.INFO)
from discord import app_commands
from bot.config import DISCORD_CHANNEL_ID
from bot.overseerr.api import overseerr_search
from discord import ui, Interaction, ButtonStyle
import discord

class RequestView(ui.View):
    def __init__(self, media_type, tmdb_id, seasons=None):
        super().__init__(timeout=120)
        self.media_type = media_type
        self.tmdb_id = tmdb_id
        self.seasons = seasons or []

        # Add the main request button(s)
        if media_type == "movie":
            self.add_item(ui.Button(
                label="Request Movie",
                style=ButtonStyle.green,
                custom_id=f"req_movie_{tmdb_id}"
            ))
        elif media_type == "tv":
            self.add_item(ui.Button(
                label="Request All Seasons",
                style=ButtonStyle.green,
                custom_id=f"req_tv_all_{tmdb_id}"
            ))
            # Limit to 10 seasons for visual sanity
            for season in self.seasons[:10]:
                self.add_item(ui.Button(
                    label=f"Request Season {season}",
                    style=ButtonStyle.blurple,
                    custom_id=f"req_tv_{tmdb_id}_s{season}"
                ))

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
                raw = result.get("result")  # Needs to be provided in your overseerr_search return!
                if not raw:
                    await interaction.followup.send(embed=embed)
                    continue

                media_type = raw.get("mediaType")
                tmdb_id = raw.get("tmdbId")
                seasons = []
                if media_type == "tv" and raw.get("seasonNumbers"):
                    seasons = raw["seasonNumbers"]

                view = RequestView(media_type, tmdb_id, seasons)
                await interaction.followup.send(embed=embed, view=view)
                logging.info(f"Sent embed for: {embed.title} with request buttons.")
        except Exception as e:
            logging.exception(f"Error handling /search command: {e}")
            await interaction.followup.send("There was an error while searching. Please try again later.")

    # Add a global interaction handler for the request buttons
    @bot.event
    async def on_interaction(interaction: Interaction):
        # Only handle button presses
        if not interaction.type == discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id")
        if custom_id and (custom_id.startswith("req_movie_") or custom_id.startswith("req_tv_")):
            await interaction.response.send_message(
                f"Request button pressed: `{custom_id}`.\n(Actual Overseerr request not yet implemented.)",
                ephemeral=True
            )
            logging.info(f"User {interaction.user} pressed request button: {custom_id}")