import discord
from discord.ext import commands
import asyncio
import yt_dlp
import os

# -------------------------
# Global Variables
# -------------------------
queues = {}  # guild_id: list of URLs
players = {}  # guild_id: current player

# -------------------------
# Helper Functions
# -------------------------
def get_guild_queue(guild_id):
    if guild_id not in queues:
        queues[guild_id] = []
    return queues[guild_id]

async def join_voice(ctx):
    if ctx.author.voice is None:
        await ctx.send("⛔ You must be in a voice channel to play music.")
        return None
    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        return await channel.connect()
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)
    return ctx.voice_client

def create_ydl_opts(cookies_path="cookies.txt"):
    return {
        "format": "bestaudio/best",
        "quiet": True,
        "extract_flat": "in_playlist",
        "noplaylist": True,
        "cookiefile": cookies_path if os.path.exists(cookies_path) else None,
        "default_search": "ytsearch",
        "source_address": "0.0.0.0",
    }

async def play_next(ctx, guild_id):
    queue = get_guild_queue(guild_id)
    if not queue:
        await ctx.voice_client.disconnect()
        return

    url = queue.pop(0)
    ydl_opts = create_ydl_opts()
    loop = asyncio.get_event_loop()

    def extract_info():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        info = await loop.run_in_executor(None, extract_info)
        if "entries" in info:
            info = info["entries"][0]
        url2 = info["url"]
        title = info.get("title", "Unknown Title")
    except Exception as e:
        await ctx.send(f"❌ Error fetching URL: {e}")
        await play_next(ctx, guild_id)
        return

    source = discord.FFmpegPCMAudio(url2, executable="ffmpeg")
    ctx.voice_client.play(
        source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx, guild_id), loop)
    )

    await ctx.send(f"▶️ Now playing: **{title}**")

# -------------------------
# Bot Setup
# -------------------------
async def setup(bot):
    @bot.command(name="play")
    async def play(ctx, *, search: str):
        vc = await join_voice(ctx)
        if not vc:
            return

        queue = get_guild_queue(ctx.guild.id)
        queue.append(search)
        if not vc.is_playing():
            await play_next(ctx, ctx.guild.id)
        else:
            await ctx.send(f"✅ Added to queue: `{search}`")

    @bot.command(name="skip")
    async def skip(ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏭ Skipped the current track.")
        else:
            await ctx.send("⛔ No music is playing.")

    @bot.command(name="stop")
    async def stop(ctx):
        if ctx.voice_client:
            ctx.voice_client.stop()
            get_guild_queue(ctx.guild.id).clear()
            await ctx.voice_client.disconnect()
            await ctx.send("⏹ Stopped playback and cleared queue.")
        else:
            await ctx.send("⛔ Not connected to a voice channel.")

    @bot.command(name="queue")
    async def queue_cmd(ctx):
        queue = get_guild_queue(ctx.guild.id)
        if not queue:
            await ctx.send("📃 The queue is empty.")
        else:
            msg = "\n".join(f"{i+1}. {q}" for i, q in enumerate(queue))
            await ctx.send(f"📃 **Current Queue:**\n{msg}")

    @bot.command(name="volume")
    async def volume(ctx, vol: int):
        if ctx.voice_client and 0 < vol <= 100:
            ctx.voice_client.source.volume = vol / 100
            await ctx.send(f"🔊 Volume set to {vol}%")
        else:
            await ctx.send("⛔ Volume must be between 1-100 or bot not connected.")
