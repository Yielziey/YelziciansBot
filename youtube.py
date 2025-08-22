import requests
import discord
import os

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
