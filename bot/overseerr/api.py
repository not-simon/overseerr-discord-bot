import aiohttp
import urllib.parse
import logging
from bot.config import OVERSEERR_API_KEY, OVERSEERR_URL
import discord

def get_type_color(media_type):
    return {
        "movie": discord.Color.blue(),
        "tv": discord.Color.purple(),
        "person": discord.Color.gold(),
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
        if media_type == "movie":
            return f"https://www.themoviedb.org/movie/{tmdb_id}"
        elif media_type == "tv":
            return f"https://www.themoviedb.org/tv/{tmdb_id}"
    return None

async def overseerr_search(query, requester_name=None, requester_avatar_url=None):
    logging.info(f"Querying Overseerr: {query!r}")
    query_encoded = urllib.parse.quote(query.strip())
    url = f"{OVERSEERR_URL}/api/v1/search?query={query_encoded}"
    logging.info(f"Requesting URL: {url}")
    async with aiohttp.ClientSession() as session:
        headers = {"X-Api-Key": OVERSEERR_API_KEY}
        async with session.get(url, headers=headers) as resp:
            logging.info(f"Overseerr API status: {resp.status}")

            # ERROR HANDLING: if Overseerr returns error status
            if resp.status != 200:
                logging.error(f"Overseerr API error: {resp.status}")
                error_embed = discord.Embed(
                    title="Overseerr API Error",
                    description="Sorry, could not retrieve results from Overseerr.",
                    color=discord.Color.red()
                )
                embeds = [{"embed": error_embed}]
                return embeds

            data = await resp.json()
            logging.info(f"Overseerr API returned: {data}")
            results = data.get("results", [])

            embeds = []


            embeds = []

            if not results:
                no_embed = discord.Embed(
                    title="No Results",
                    description=f"No results found for '{query}'.",
                    color=discord.Color.orange()
                )
                embeds.append({"embed": no_embed})
                return embeds

            for result in results[:5]:
                tmdb_id = result.get("tmdbId") or result.get("id")
                title = result.get("title") or result.get("name", "Unknown Title")
                year = get_year(result)
                overview = (result.get("overview") or "No description available.").strip()
                if len(overview) > 350:
                    overview = overview[:347] + "…"
                media_type = result.get("mediaType", "unknown")
                color = get_type_color(media_type)
                tmdb_url = get_tmdb_url(result)
                poster = result.get("posterPath")

                embed = discord.Embed(
                    title=f"{title} ({year})",
                    description=overview,
                    color=color,
                    url=tmdb_url
                )
                if poster:
                    embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w500{poster}")

                embed.add_field(name="Type", value=media_type.title(), inline=True)
                embed.add_field(name="User Rating", value=get_rating(result), inline=True)
                embed.add_field(name="TMDb", value=f"[Link]({tmdb_url})" if tmdb_url else "N/A", inline=True)

                if result.get("mediaInfo"):
                    status = result["mediaInfo"].get("status")
                    status_str = {
                        1: "Available",
                        2: "Partially Available",
                        3: "Processing",
                        4: "Requested",
                        5: "Unavailable"
                    }.get(status, "Unknown")
                    embed.add_field(name="Request Status", value=status_str, inline=True)

                if requester_avatar_url:
                    embed.set_footer(
                        text=f"Powered by Fetcherr • Requested by {requester_name or 'Unknown'}",
                        icon_url=requester_avatar_url
                    )
                else:
                    embed.set_footer(
                        text=f"Powered by Fetcherr • Requested by {requester_name or 'Unknown'}"
                    )

                # Only append if tmdb_id is present
                if tmdb_id:
                    embeds.append({"embed": embed, "result": result})
                else:
                    embed.add_field(name="⚠️ Not Requestable", value="No TMDb ID found.", inline=False)
                    embeds.append({"embed": embed, "result": result})

            return embeds
