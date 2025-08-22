# youtube.py

import requests
import discord
from discord.ui import View, Button
import os

# Load YouTube API key from environment
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


def get_latest_video(channel_id: str):
    """
    Fetch the latest video from a YouTube channel.
    Returns a dict with 'videoId' and 'snippet', or None if not found.
    """
    url = (
        f"https://www.googleapis.com/youtube/v3/search"
        f"?key={YOUTUBE_API_KEY}&channelId={channel_id}"
        f"&part=snippet,id&order=date&maxResults=1&type=video"
    )
    try:
        response = requests.get(url)
        data = response.json()
        items = data.get("items", [])
        if not items:
            return None
        return items[0]
    except Exception as e:
        print(f"❌ YouTube API Error: {e}")
        return None


def create_youtube_video_embed(video: dict, role_mention: str = None) -> discord.Embed:
    """
    Create a Discord embed for a YouTube video.
    Optional role_mention can be added at the top of the embed.
    """
    video_id = video["id"].get("videoId")
    snippet = video.get("snippet", {})
    title = snippet.get("title", "New Video")
    description = snippet.get("description", "")

    embed = discord.Embed(
        title=f"📢 New Video: {title}",
        description=f"{description[:200]}...\n[▶️ Watch on YouTube](https://www.youtube.com/watch?v={video_id})",
        color=discord.Color.red()
    )

    thumbnail = snippet.get("thumbnails", {}).get("high", {}).get("url")
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    footer_text = "Powered by YouTube API 🎥"
    embed.set_footer(text=footer_text, icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384060.png")

    return embed


def create_youtube_view(video_id: str) -> View:
    """
    Create a Discord UI view with a 'Watch on YouTube' button.
    """
    view = View()
    view.add_item(
        Button(
            label="Watch on YouTube",
            url=f"https://www.youtube.com/watch?v={video_id}",
            style=discord.ButtonStyle.link
        )
    )
    return view
