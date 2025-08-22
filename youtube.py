import requests
from discord import Embed

def create_youtube_video_embed(video):
    video_id = video["id"].get("videoId")
    embed = Embed(
        title="📢 New YouTube Video!",
        description=f"**{video['snippet']['title']}** just dropped!\n[▶️ Watch on YouTube](https://www.youtube.com/watch?v={video_id})",
        color=0xFF0000
    )
    embed.set_thumbnail(url=video["snippet"]["thumbnails"]["high"]["url"])
    embed.set_footer(text="Powered by YouTube API 🎥", icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384060.png")
    return embed


async def check_youtube_videos(api_key, last_video_id=None):
    channel_id = "UC2M3qP1SHMAOhrYThLwiJPw"  # Replace with your channel ID
    url = f"https://www.googleapis.com/youtube/v3/search?key={api_key}&channelId={channel_id}&part=snippet,id&order=date&maxResults=1"
    res = requests.get(url).json()
    items = res.get("items", [])
    if not items:
        return None
    video = items[0]
    video_id = video["id"].get("videoId")
    if video_id == last_video_id:
        return None
    return video
