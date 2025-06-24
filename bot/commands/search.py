# FINAL search.py

import logging
import re
from discord import app_commands, ui, Interaction, ButtonStyle
import discord
from bot.config import DISCORD_CHANNEL_ID
from bot.overseerr.api import overseerr_search, overseerr_make_request

logging.basicConfig(level=logging.INFO)

class RequestView(ui.View):
    def __init__(self, media_type, tmdb_id, requestable_seasons=None):
        super().__init__(timeout=120)
        
        if media_type == "movie":
            self.add_item(ui.Button(
                label="Request Movie",
                style=ButtonStyle.green,
                custom_id=f"req_movie_{tmdb_id}"
            ))
        elif media_type == "tv":
            seasons = requestable_seasons or []
            if seasons:
                self.add_item(ui.Button(
                    label="Request All Remaining",
                    style=ButtonStyle.green,
                    custom_id=f"req_tv_all_{tmdb_id}"
                ))
                # Limit to 10 season buttons to avoid clutter
                for season in seasons[:10]:
                    self.add_item(ui.Button(
                        label=f"Request Season {season}",
                        style=ButtonStyle.blurple,
                        custom_id=f"req_tv_{tmdb_id}_s{season}"
                    ))

def setup(bot):
    if not hasattr(bot, "_fetcherr_listener_registered"):
        bot.add_listener(handle_interaction, "on_interaction")
        bot._fetcherr_listener_registered = True

    @bot.tree.command(name="search", description="Search for a movie or TV show in Overseerr")
    async def search(interaction: Interaction, query: str):
        logging.info(f"User {interaction.user} searched for: {query!r}")
        if interaction.channel_id != DISCORD_CHANNEL_ID:
            await interaction.response.send_message("This command can only be used in the designated channel.", ephemeral=True)
            return

        await interaction.response.defer()
        try:
            results = await overseerr_search(
                query,
                requester_name=interaction.user.display_name,
                requester_avatar_url=interaction.user.display_avatar.url
            )
            
            for result_data in results:
                embed = result_data["embed"]
                raw = result_data.get("result")
                if not raw:
                    await interaction.followup.send(embed=embed)
                    continue

                media_type = raw.get("mediaType")
                tmdb_id = raw.get("tmdbId") or raw.get("id")
                requestable_seasons = result_data.get("requestable_seasons", [])
                
                view = RequestView(media_type, tmdb_id, requestable_seasons)
                await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            logging.exception(f"Error handling /search command: {e}")
            if not interaction.response.is_done():
                await interaction.followup.send("An error occurred.", ephemeral=True)


async def handle_interaction(interaction: Interaction):
    custom_id = interaction.data.get("custom_id")
    if not custom_id:
        return

    await interaction.response.defer(ephemeral=True)
    
    try:
        # Movie request
        if match := re.match(r"req_movie_(\d+)", custom_id):
            tmdb_id = int(match.group(1))
            status, data = await overseerr_make_request(tmdb_id, "movie", interaction.user)
        # TV All Seasons request
        elif match := re.match(r"req_tv_all_(\d+)", custom_id):
            tmdb_id = int(match.group(1))
            status, data = await overseerr_make_request(tmdb_id, "tv", interaction.user, season_numbers="all")
        # TV Specific Season request
        elif match := re.match(r"req_tv_(\d+)_s(\d+)", custom_id):
            tmdb_id = int(match.group(1))
            season = int(match.group(2))
            status, data = await overseerr_make_request(tmdb_id, "tv", interaction.user, season_numbers=[season])
        else:
            await interaction.followup.send("Unknown action.", ephemeral=True)
            return

        # Common status handling
        if status == 201:
            await interaction.followup.send("✅ Request successful!", ephemeral=True)
        elif status == 409:
            await interaction.followup.send("⚠️ This is already requested or available.", ephemeral=True)
        else:
            error_message = data.get("message", "An unknown error occurred.")
            await interaction.followup.send(f"❌ Request failed: {error_message}", ephemeral=True)

    except Exception as e:
        logging.exception("Exception in handle_interaction:")
        if not interaction.response.is_done():
            await interaction.followup.send("⚠️ An error occurred while handling your request.", ephemeral=True)