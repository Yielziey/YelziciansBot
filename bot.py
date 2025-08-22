from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import os
import json, requests

from tickets import setup as setup_tickets
from spotify import get_spotify_token, create_spotify_artist_embed, get_latest_albums
from youtube import create_youtube_video_embed
from lyrics import fetch_lyrics, paginate_lyrics, LyricsPaginator, create_lyrics_embed
from ai import ask_gpt, paginate_text, AIPaginator, create_ai_embed
from music import setup as setup_music
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

SPOTIFY_ANNOUNCEMENT_CHANNEL_ID = 1407641244263514194
YOUTUBE_ANNOUNCEMENT_CHANNEL_ID = 1407641272323412058
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
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# -------------------------
# Globals
# -------------------------
SPOTIFY_ACCESS_TOKEN = None
latest_spotify_release = None
latest_youtube_video = None

# -------------------------
# Constants
# -------------------------
MEMBER_ROLE_ID = 1407630846294491168   # @Member role ID (for mention + auto-assign)
ROLE_MENTION = f"<@&{MEMBER_ROLE_ID}>"
WELCOME_CHANNEL_ID = 1407736229994430475   # Welcome channel

# -------------------------
# Intents & Bot Setup
# -------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# -------------------------
# Globals
# -------------------------
SPOTIFY_ACCESS_TOKEN = None
latest_spotify_release = None
latest_youtube_video = None

# -------------------------
# Welcome Event
# -------------------------
@bot.event
async def on_member_join(member):
    # Auto-assign @Member role
    role = member.guild.get_role(MEMBER_ROLE_ID)
    if role:
        try:
            await member.add_roles(role)
        except discord.Forbidden:
            print(f"Cannot assign role to {member}.")

    # Send welcome embed
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🎉 Welcome!",
            description=f"👋 Hello {member.mention}, welcome to **{member.guild.name}**!",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Enjoy your stay!")
        await channel.send(embed=embed)

# -------------------------
# Commands
# -------------------------

# --- ANNOUNCE
@bot.command(name="announce")
async def announce(ctx, *, message):
    if any(role.id in [MODERATOR_ROLE_ID, ARTIST_ROLE_ID, ADMIN_ROLE_ID] for role in ctx.author.roles):
        embed = discord.Embed(title="📢 Announcement", description=message, color=0x2ecc71)
        await ctx.send(content=ROLE_MENTION, embed=embed)
        try: await ctx.message.delete()
        except discord.Forbidden: pass
    else:
        await ctx.send("⛔ You don't have permission.")

# --- POST
@bot.command(name="post")
async def post(ctx, *, message):
    if any(role.id in [MODERATOR_ROLE_ID, ARTIST_ROLE_ID, ADMIN_ROLE_ID] for role in ctx.author.roles):
        embed = discord.Embed(description=message, color=0x2ecc71)
        await ctx.send(content=ROLE_MENTION, embed=embed)
        try: await ctx.message.delete()
        except discord.Forbidden: pass
    else:
        await ctx.send("⛔ You don't have permission.")

# --- SEARCH (Spotify)
@bot.command(name="search")
async def search(ctx, *, artist_name):
    global SPOTIFY_ACCESS_TOKEN
    if not SPOTIFY_ACCESS_TOKEN:
        SPOTIFY_ACCESS_TOKEN = get_spotify_token()
    
    # Fetch artist
    headers = {"Authorization": f"Bearer {SPOTIFY_ACCESS_TOKEN}"}
    search_url = f"https://api.spotify.com/v1/search?q={artist_name}&type=artist&limit=1"
    resp = requests.get(search_url, headers=headers).json()
    items = resp.get("artists", {}).get("items", [])
    if not items:
        return await ctx.send("🎵 Artist not found.")
    artist = items[0]
    artist_id = artist["id"]

    # Top tracks
    top_tracks_data = requests.get(f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=US", headers=headers).json()
    top_tracks = [f"🎵 [{t['name']}]({t['external_urls']['spotify']})" for t in top_tracks_data.get("tracks", [])[:5]]

    # Latest albums
    latest_albums = get_latest_albums(artist_id, SPOTIFY_ACCESS_TOKEN, limit=5)

    # Create embed
    embed = create_spotify_artist_embed(artist, top_tracks, latest_albums)
    view = View()
    view.add_item(Button(label="Open in Spotify", url=artist["external_urls"]["spotify"], style=discord.ButtonStyle.link))
    await ctx.send(content=ROLE_MENTION, embed=embed, view=view)

# --- LYRICS
@bot.command()
async def lyrics(ctx, *, song_name):
    await ctx.defer()  # in case fetching takes time
    lyrics_text = await fetch_lyrics(song_name)
    pages = paginate_lyrics(lyrics_text)
    embed = create_lyrics_embed(song_name, pages[0], 1, len(pages))
    view = LyricsPaginator(ctx, song_name, pages)
    await ctx.send(embed=embed, view=view)

# --- AI ASK
@bot.command(name="ask")
async def ask(ctx, *, question):
    await ctx.defer()  # Show “thinking…” in Discord
    answer = await ask_gpt(question)
    pages = paginate_text(answer)
    embed = create_ai_embed(question, pages[0], 1, len(pages))
    view = AIPaginator(ctx, question, pages)
    await ctx.send(embed=embed, view=view)

# --- HELP
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(title="📖 Help Menu", description="Available commands:", color=discord.Color.blue())
    embed.add_field(name="General", value="`help`, `post`, `announce`, `search`, `lyrics`, `ask`", inline=False)
    await ctx.send(embed=embed)

# -------------------------
# Automated Tasks
# -------------------------
@tasks.loop(minutes=10)
async def check_new_releases():
    global latest_spotify_release
    headers = {"Authorization": f"Bearer {SPOTIFY_ACCESS_TOKEN}"}
    artist_id = "6rhenHsRHjPnQIcawW67VQ"  # example artist
    data = requests.get(f"https://api.spotify.com/v1/artists/{artist_id}/albums?include_groups=single,album&limit=1", headers=headers).json()
    if "items" not in data or not data["items"]:
        return
    album = data["items"][0]
    album_id = album["id"]
    if latest_spotify_release != album_id:
        latest_spotify_release = album_id
        channel = bot.get_channel(SPOTIFY_ANNOUNCEMENT_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="🎵 New Release!", description=f"**{album['name']}** is out!\n[Listen here]({album['external_urls']['spotify']})", color=discord.Color.green())
            await channel.send(content=ROLE_MENTION, embed=embed)

@tasks.loop(minutes=10)
async def check_youtube():
    global latest_youtube_video
    channel_id = "UC2M3qP1SHMAOhrYThLwiJPw"
    data = requests.get(f"https://www.googleapis.com/youtube/v3/search?key={os.getenv('YOUTUBE_API_KEY')}&channelId={channel_id}&part=snippet,id&order=date&maxResults=1").json()
    items = data.get("items", [])
    if not items: return
    video = items[0]
    video_id = video["id"].get("videoId")
    if video_id and latest_youtube_video != video_id:
        latest_youtube_video = video_id
        channel = bot.get_channel(YOUTUBE_ANNOUNCEMENT_CHANNEL_ID)
        if channel:
            embed = create_youtube_video_embed(video)
            await channel.send(content=ROLE_MENTION, embed=embed)

# -------------------------
# Bot Startup
# -------------------------
@bot.event
async def on_ready():
    global SPOTIFY_ACCESS_TOKEN
    SPOTIFY_ACCESS_TOKEN = get_spotify_token()
    print(f"✅ Logged in as {bot.user}")

    # Start background tasks
    check_new_releases.start()
    check_youtube.start()
    await setup_music(bot)

    # Setup Ticket System
    try:
        await setup_tickets(bot)  # from tickets.py
        print("✅ Ticket System is running")
    except Exception as e:
        print(f"❌ Ticket System failed to load: {e}")

bot.run(DISCORD_TOKEN)