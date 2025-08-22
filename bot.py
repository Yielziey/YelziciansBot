from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import requests, aiohttp
import asyncio
import os
import json
import yt_dlp
from tickets import setup as setup_tickets

# -------------------------
# Load Environment Variables
# -------------------------
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# -------------------------
# Role & Channel IDs
# -------------------------
MODERATOR_ROLE_ID = 1407630846294491169
ARTIST_ROLE_ID = 1407630978469466112
ADMIN_ROLE_ID = 1407630846294491170
NOTIFY_ROLE_ID = 1407630846294491168

SPOTIFY_ANNOUNCEMENT_CHANNEL_ID = 1407641244263514194
YOUTUBE_ANNOUNCEMENT_CHANNEL_ID = 1407641272323412058
YTMUSIC_ANNOUNCEMENT_CHANNEL_ID = 1407641183978782760
GENERAL_ANNOUNCEMENT_CHANNEL_ID = 1407630847703781426

# -------------------------
# Ticket Config
# -------------------------
TICKET_CHANNEL_ID = 1407630847703781427
TICKET_LOG_CHANNEL_ID = 1407656944164016138
TICKET_TIMEOUT = 3600  # 1 hour

# -------------------------
# Intents & Bot Setup
# -------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# -------------------------
# Globals
# -------------------------
SPOTIFY_ACCESS_TOKEN = None
latest_spotify_release = None
latest_youtube_video = None
last_ytmusic_release = None

# -------------------------
# Constants
# -------------------------
ROLE_MENTION = f"<@&{NOTIFY_ROLE_ID}>"
FFMPEG_PATH = r"C:\Users\BioStaR\Downloads\ffmpeg\bin\ffmpeg.exe"

# -------------------------
# Helper Functions
# -------------------------
def get_spotify_token():
    url = "https://accounts.spotify.com/api/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET
    }
    response = requests.post(url, headers=headers, data=data)
    return response.json().get("access_token")

def create_announcement_embed(message, attachments=None):
    embed = discord.Embed(
        title="📢 Announcement",
        description=f"\n{message}",
        color=discord.Color.blue()
    )
    for word in message.split():
        if word.startswith("http"):
            embed.add_field(name="🔗 Link", value=word, inline=False)
    if attachments:
        embed.set_image(url=attachments[0].url)
    return embed

def create_spotify_artist_embed(artist_data, top_tracks, latest_albums):
    embed = discord.Embed(
        title=artist_data["name"],
        url=artist_data["external_urls"]["spotify"],
        description=f"{ROLE_MENTION}\n🎵 Discover this artist on Spotify!",
        color=discord.Color.green()
    )
    if artist_data["images"]:
        embed.set_thumbnail(url=artist_data["images"][0]["url"])
    embed.add_field(name="👥 Followers", value=f"{artist_data['followers']['total']:,}", inline=True)
    embed.add_field(name="🎸 Genres", value=", ".join(artist_data["genres"]) if artist_data["genres"] else "N/A", inline=True)
    embed.add_field(name="🔥 Top Songs", value="\n".join(top_tracks) if top_tracks else "No tracks found.", inline=False)
    embed.add_field(name="📀 Latest Albums", value="\n".join(latest_albums) if latest_albums else "No albums found.", inline=False)
    embed.set_footer(text="Powered by Spotify API 🎶", icon_url="https://cdn-icons-png.flaticon.com/512/2111/2111624.png")
    return embed

def create_youtube_video_embed(video):
    video_id = video["id"].get("videoId")
    embed = discord.Embed(
        title="📢 New YouTube Video!",
        description=f"**{video['snippet']['title']}** just dropped!\n[▶️ Watch on YouTube](https://www.youtube.com/watch?v={video_id})",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=video["snippet"]["thumbnails"]["high"]["url"])
    embed.set_footer(
        text="Powered by YouTube API 🎥",
        icon_url="https://cdn-icons-png.flaticon.com/512/1384/1384060.png"
    )
    return embed

# -------------------------
# Commands
# -------------------------
# --- Embed Creator Function
def create_announcement_embed(message, attachments, announcement=True):
    embed = discord.Embed(description=message, color=0x2ecc71)

    if announcement:
        embed.set_author(name="📢 Announcement")

    # if there’s an attachment, use first as image
    if attachments:
        embed.set_image(url=attachments[0].url)

    return embed


# --- ANNOUNCE (with 📢 + mention)
@bot.command(name="announce")
async def announce(ctx, *, message):
    if any(role.id in [MODERATOR_ROLE_ID, ARTIST_ROLE_ID, ADMIN_ROLE_ID] for role in ctx.author.roles):
        for emoji in ctx.guild.emojis:
            message = message.replace(f":{emoji.name}:", str(emoji))
        embed = create_announcement_embed(message, ctx.message.attachments, announcement=True)
        await ctx.send(content=ROLE_MENTION, embed=embed)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            print("Bot cannot delete messages.")
    else:
        await ctx.send("⛔ You don't have permission to use this command.")

# --- POST (same embed, no 📢, no mention)
@bot.command(name="post")
async def post(ctx, *, message):
    if any(role.id in [MODERATOR_ROLE_ID, ARTIST_ROLE_ID, ADMIN_ROLE_ID] for role in ctx.author.roles):
        for emoji in ctx.guild.emojis:
            message = message.replace(f":{emoji.name}:", str(emoji))
        embed = create_announcement_embed(message, ctx.message.attachments, announcement=False)
        await ctx.send(embed=embed)  # no mention
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            print("Bot cannot delete messages.")
    else:
        await ctx.send("⛔ You don't have permission to use this command.")

@bot.command(name="search")
async def search(ctx, *, artist_name):
    global SPOTIFY_ACCESS_TOKEN
    # Get artist info
    search_url = f"https://api.spotify.com/v1/search?q={artist_name}&type=artist&limit=1"
    headers = {"Authorization": f"Bearer {SPOTIFY_ACCESS_TOKEN}"}
    artist_response = requests.get(search_url, headers=headers)
    
    if artist_response.status_code != 200:
        await ctx.send("⚠️ Error fetching data from Spotify.")
        return
    
    artist_data = artist_response.json().get("artists", {}).get("items", [])
    if not artist_data:
        await ctx.send("🎵 Artist not found.")
        return
    
    artist = artist_data[0]
    artist_id = artist["id"]

    # Top tracks
    top_tracks_data = requests.get(
        f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=US", headers=headers
    ).json()
    top_tracks = [f"🎵 [{t['name']}]({t['external_urls']['spotify']})" for t in top_tracks_data.get("tracks", [])[:5]]

    # Latest releases (albums + singles + EPs)
    albums_data = requests.get(
        f"https://api.spotify.com/v1/artists/{artist_id}/albums?include_groups=album,single&limit=5",
        headers=headers
    ).json()
    latest_albums = [f"📀 [{a['name']}]({a['external_urls']['spotify']})" for a in albums_data.get("items", [])]

    # Create embed
    embed = create_spotify_artist_embed(artist, top_tracks, latest_albums)

    # View button
    view = View()
    view.add_item(Button(label="Open in Spotify", url=artist["external_urls"]["spotify"], style=discord.ButtonStyle.link))

    # Send with mention only once in content
    await ctx.send(content=ROLE_MENTION, embed=embed, view=view)

    # Delete user's command
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        print("Bot cannot delete messages.")


@bot.command(name="help", aliases=["zihelp"])
async def help_command(ctx):
    image_url = "https://cdn.discordapp.com/attachments/1305467055469756427/1340186960245035069/7.jpg"
    embed = discord.Embed(
        title="📖 YelziciansBot Help Menu",
        description="Here are the available commands:",
        color=discord.Color.blue()
    )
    embed.add_field(name="**Ticket System**", value="""
    `close_ticket` - Manually close a ticket  
    `setup_tickets` - Admin command to set up ticket messages  
    `toggle_notify` - Opt-in/out of notifications  
    """, inline=False)
    embed.add_field(name="**General Commands**", value="""
    `help` - Shows this help menu  
    `post` - Post an announcement  
    `search` - Search for an artist  
    """, inline=False)
    embed.set_footer(text="Powered by YelziciansBot 🎶", icon_url=image_url)
    await ctx.send(embed=embed)

# -------------------------
# Automated Tasks
# -------------------------
@tasks.loop(minutes=10)
async def check_new_releases():
    global latest_spotify_release, SPOTIFY_ACCESS_TOKEN
    headers = {"Authorization": f"Bearer {SPOTIFY_ACCESS_TOKEN}"}
    artist_id = "6rhenHsRHjPnQIcawW67VQ"
    data = requests.get(f"https://api.spotify.com/v1/artists/{artist_id}/albums?include_groups=single,album&limit=1", headers=headers).json()
    if "items" not in data or not data["items"]:
        return
    album = data["items"][0]
    album_id = album["id"]
    if latest_spotify_release != album_id:
        latest_spotify_release = album_id
        channel = bot.get_channel(SPOTIFY_ANNOUNCEMENT_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🎵 New Release Alert!",
                description=f"**{album['name']}** by the artist is now available!\n[🎧 Listen on Spotify]({album['external_urls']['spotify']})",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=album["images"][0]["url"] if album["images"] else None)
            embed.set_footer(text="Powered by Spotify API 🎶", icon_url="https://cdn-icons-png.flaticon.com/512/2111/2111624.png")
            await channel.send(content=ROLE_MENTION, embed=embed)

@tasks.loop(minutes=10)
async def check_youtube():
    global latest_youtube_video
    channel_id = "UC2M3qP1SHMAOhrYThLwiJPw"
    data = requests.get(f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}&channelId={channel_id}&part=snippet,id&order=date&maxResults=1").json()
    items = data.get("items", [])
    if not items:
        return
    video = items[0]
    video_id = video["id"].get("videoId")
    if video_id and latest_youtube_video != video_id:
        latest_youtube_video = video_id
        channel = bot.get_channel(YOUTUBE_ANNOUNCEMENT_CHANNEL_ID)
        if channel:
            embed = create_youtube_video_embed(video)
            await channel.send(content=ROLE_MENTION, embed=embed)

DEFAULT_MEMBER_ROLE_ID = 1407630846294491168  # Member role
WELCOME_CHANNEL_ID = 1407736229994430475   # Welcome channel

@bot.event
async def on_member_join(member):
    # Assign default member role
    role = member.guild.get_role(DEFAULT_MEMBER_ROLE_ID)
    if role:
        try:
            await member.add_roles(role)
        except discord.Forbidden:
            print(f"❌ Cannot assign role to {member}. Check bot permissions.")

    # Send welcome embed
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title=f"Welcome {member.name}!",
            description=f"👋 Hello {member.mention}, welcome to **{member.guild.name}**!\nEnjoy your stay!",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Welcome to the server 🎉")
        await channel.send(embed=embed)

# -------------------------
# Bot Startup
# -------------------------
@bot.event
async def on_ready():
    global SPOTIFY_ACCESS_TOKEN
    SPOTIFY_ACCESS_TOKEN = get_spotify_token()
    print(f"✅ Logged in as {bot.user}")

    # Setup Ticket System
    try:
        await setup_tickets(bot)  # registers TicketSystem cog
        print("✅ Ticket System is running")
    except Exception as e:
        print(f"❌ Ticket System failed to load: {e}")

    # Start automated tasks
    check_new_releases.start()
    check_youtube.start()
    print("✅ Background tasks started")

# -------------------------
# Run the bot
# -------------------------
bot.run(DISCORD_TOKEN)