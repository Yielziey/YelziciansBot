import requests
import discord
import os
from discord.ui import View, Button
from bot import ROLE_MENTION  # Make sure ROLE_MENTION is defined in bot.py

# Load API key and channel ID from environment variables
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_API_CHANNEL_ID")  # Example: UC2M3qP1SHMAOhrYThLwiJPw

def get_latest_video(channel_id: str):
    """
    Fetch the latest video from a YouTube channel.
    Returns a dict with 'videoId' and 'snippet' or None if not found.
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

def create_youtube_video_embed(video: dict) -> discord.Embed:
    """
    Creates a Discord embed for a YouTube video.
    """
    video_id = video["id"].get("videoId")
    snippet = video.get("snippet", {})
    title = snippet.get("title", "New Video")
    description = snippet.get("description", "")
    thumbnail = snippet.get("thumbnails", {}).get("high", {}).get("url")
    
    embed = discord.Embed(
        title=f"📢 New Video: {title}",
        description=f"{description[:200]}...\n[▶️ Watch on YouTube](https://www.youtube.com/watch?v={video_id})",
        color=discord.Color.red()
    )
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    embed.set_footer(
        text="Powered by YouTube API 🎥",
        icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384060.png"
    )
    
    return embed

async def post_latest_video(bot):
    """
    Check the latest video and post to Discord channel with role mention and button.
    """
    video = get_latest_video(YOUTUBE_CHANNEL_ID)
    if not video:
        print("No new video found.")
        return
    
    video_id = video["id"].get("videoId")
    channel = bot.get_channel(YOUTUBE_CHANNEL_ID)  # Discord channel ID
    if channel:
        embed = create_youtube_video_embed(video)
        view = View()
        view.add_item(Button(label="Watch on YouTube", url=f"https://www.youtube.com/watch?v={video_id}", style=discord.ButtonStyle.link))
        await channel.send(content=ROLE_MENTION, embed=embed, view=view)
