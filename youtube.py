import requests
import discord
from discord.ui import View, Button
import os

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def get_latest_video(channel_id: str):
    url = (
        f"https://www.googleapis.com/youtube/v3/search"
        f"?key={YOUTUBE_API_KEY}&channelId={channel_id}"
        f"&part=snippet,id&order=date&maxResults=1"
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
    video_id = video["id"].get("videoId")
    snippet = video.get("snippet", {})
    title = snippet.get("title", "New Video")
    thumbnail = snippet.get("thumbnails", {}).get("high", {}).get("url")
    
    embed = discord.Embed(
        title="📢 New YouTube Video!",
        description=f"**{title}** just dropped!\n[▶️ Watch on YouTube](https://www.youtube.com/watch?v={video_id})",
        color=discord.Color.red()
    )
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    embed.set_footer(
        text="Powered by YouTube API 🎥",
        icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384060.png"
    )
    
    return embed


def create_youtube_view(video: dict):
    """Create Discord UI View with Open in YouTube button"""
    view = View()
    video_id = video["id"].get("videoId")
    if video_id:
        view.add_item(Button(label="Open in YouTube", url=f"https://www.youtube.com/watch?v={video_id}", style=discord.ButtonStyle.link))
    return view
