# FINAL api.py

import aiohttp
import urllib.parse
import logging
from bot.config import OVERSEERR_API_KEY, OVERSEERR_URL
import discord
import json

def format_season_status(seasons):
    """Formats the season list with emojis based on their real status."""
    status_emojis = {
        5: "🟢",  # Available
        4: "🟡",  # Partially Available
        3: "🔵",  # Processing
        2: "🟣",  # Pending Request
        1: "⚫",  # Not Requested / Unknown
    }
    out = []
    sorted_seasons = sorted(seasons, key=lambda s: s.get("seasonNumber", 0))

    for s in sorted_seasons:
        n = s.get("seasonNumber")
        st = s.get("status", 1)
        if n == 0:
            continue
        emoji = status_emojis.get(st, "❔")
        out.append(f"{emoji} S{n}")
    
    return " ".join(out) if out else "No season data"

def get_type_color(media_type):
    return {
        "movie": discord.Color.blue(),
        "tv": discord.Color.purple(),
    }.get(media_type, discord.Color.dark_gray())

def get_year(result):
    date = result.get("releaseDate") or result.get("firstAirDate")
    return date.split("-")[0] if date else "Unknown"

def get_rating(result):
    vote = result.get("voteAverage")
    return f"{vote:.1f}/10" if vote is not None else "N/A"

def get_tmdb_url(result):
    media_type = result.get("mediaType")
    tmdb_id = result.get("tmdbId")
    if media_type and tmdb_id:
        return f"https://www.themoviedb.org/{media_type}/{tmdb_id}"
    return None

async def overseerr_make_request(tmdb_id, media_type, user, season_numbers=None):
    url = f"{OVERSEERR_URL}/api/v1/request"
    headers = {"X-Api-Key": OVERSEERR_API_KEY, "Content-Type": "application/json"}
    payload = {"mediaType": media_type, "mediaId": tmdb_id, "is4k": False}
    
    if media_type == "tv":
        # For 'All Seasons' requests, we need to fetch all requestable season numbers
        if season_numbers == "all":
            all_seasons_data = []
            # Make a fresh call to get basic season structure
            tv_url = f"{OVERSEERR_URL}/api/v1/tv/{tmdb_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(tv_url, headers=headers) as resp:
                    if resp.status == 200:
                        tv_data = await resp.json()
                        all_seasons_data = tv_data.get("seasons", [])
            
            # Since this data lacks status, we request all non-zero seasons. 
            # Overseerr will correctly reject already-available ones.
            payload["seasons"] = [s["seasonNumber"] for s in all_seasons_data if s.get("seasonNumber", 0) > 0]
        elif season_numbers:
            payload["seasons"] = season_numbers

    async with aiohttp.ClientSession() as session:
        logging.info(f"Payload to Overseerr: {json.dumps(payload)}")
        async with session.post(url, headers=headers, data=json.dumps(payload)) as resp:
            status = resp.status
            try:
                data = await resp.json()
            except Exception:
                data = await resp.text()
            if status not in [201, 409]:
                logging.error(f"Overseerr request failed: {status} {data}")
            return status, data

async def overseerr_search(query, requester_name=None, requester_avatar_url=None):
    logging.info(f"Querying Overseerr: {query!r}")
    url = f"{OVERSEERR_URL}/api/v1/search?query={urllib.parse.quote(query.strip())}"
    headers = {"X-Api-Key": OVERSEERR_API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                return [{"embed": discord.Embed(title="API Error", color=discord.Color.red())}]
            data = await resp.json()
    
    results = data.get("results", [])
    if not results:
        return [{"embed": discord.Embed(title="No Results", color=discord.Color.orange())}]

    processed_embeds = []
    for result in results[:5]:
        embed_data = {}
        media_type = result.get("mediaType")
        
        embed = discord.Embed(
            title=f"{result.get('title') or result.get('name')} ({get_year(result)})",
            description=(result.get("overview") or "")[:350],
            color=get_type_color(media_type),
            url=get_tmdb_url(result)
        )
        if result.get("posterPath"):
            embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w500{result.get('posterPath')}")
        
        embed.add_field(name="Type", value=media_type.title(), inline=True)
        embed.add_field(name="Rating", value=get_rating(result), inline=True)
        embed.add_field(name="TMDb", value=f"[Link]({get_tmdb_url(result)})" if get_tmdb_url(result) else "N/A", inline=True)
        
        status_map = {5: "🟢 Available", 4: "🟡 Partially Available", 3: "🔵 Processing", 2: "🟣 Pending", 1: "⚫ Unknown"}
        media_info = result.get("mediaInfo")
        requestable_seasons = []

        if media_type == "tv":
            if media_info:
                season_list = media_info.get("seasons", [])
                if season_list:
                    embed.add_field(name="Status", value=format_season_status(season_list), inline=False)
                    # A season is requestable if its status is 1 (Unknown/Not Requested)
                    requestable_seasons = [s["seasonNumber"] for s in season_list if s.get("status") == 1 and s.get("seasonNumber", 0) > 0]
                else:
                    embed.add_field(name="Status", value=status_map.get(media_info.get("status"), "Unknown"), inline=False)
            else:
                embed.add_field(name="Status", value="⚫ Not Requested", inline=False)
                # If no mediaInfo, all seasons are considered requestable
                requestable_seasons = [s["seasonNumber"] for s in result.get("seasons", []) if s.get("seasonNumber", 0) > 0]

        elif media_type == "movie":
            status_str = "⚫ Not Requested" if not media_info else status_map.get(media_info.get("status"), "Unknown")
            embed.add_field(name="Status", value=status_str, inline=True)

        if requester_avatar_url:
            embed.set_footer(text=f"Requested by {requester_name}", icon_url=requester_avatar_url)
        
        embed_data["embed"] = embed
        embed_data["result"] = result
        embed_data["requestable_seasons"] = requestable_seasons
        processed_embeds.append(embed_data)
        
    return processed_embeds