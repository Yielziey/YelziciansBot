import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import yt_dlp
import os

# -------------------------
# Globals & Config
# -------------------------
QUEUE = {}
YTDLP_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": False,  # Allow playlists
    "quiet": True,
    "extract_flat": False,
    "cookiefile": "cookies.txt",  # Make sure your cookies.txt works
}

# -------------------------
# Music Player Class
# -------------------------
class MusicPlayer:
    def __init__(self, bot):
        self.bot = bot
        self.queue = {}  # guild_id: [songs]
        self.current = {}  # guild_id: current voice_client

    async def play_song(self, ctx, query):
        guild_id = ctx.guild.id

        # Ensure queue exists
        if guild_id not in self.queue:
            self.queue[guild_id] = []

        # Extract info using yt-dlp
        ydl_opts = YTDLP_OPTIONS.copy()
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
        except yt_dlp.utils.DownloadError as e:
            return await ctx.send(f"❌ Could not play the song/playlist: {e}")

        # If it's a playlist, add all entries
        if "entries" in info:
            songs = info["entries"]
        else:
            songs = [info]

        # Add to queue
        self.queue[guild_id].extend(songs)

        # If not connected to voice, join
        voice_client = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if not voice_client:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
                voice_client = await channel.connect()
            else:
                return await ctx.send("⛔ You must be in a voice channel to play music.")

        # Store voice client
        self.current[guild_id] = voice_client

        # If already playing, just notify added to queue
        if voice_client.is_playing():
            return await ctx.send(f"✅ Added {len(songs)} song(s) to the queue.")

        # Start playback
        await self._play_next(ctx)

    async def _play_next(self, ctx):
        guild_id = ctx.guild.id
        if not self.queue[guild_id]:
            return

        song = self.queue[guild_id].pop(0)
        url = song.get("url") or song.get("webpage_url")
        title = song.get("title", "Unknown Track")

        voice_client = self.current[guild_id]
        source = discord.FFmpegPCMAudio(url, options="-vn")

        def after_playing(error):
            coro = self._play_next(ctx)
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error in after_playing: {e}")

        voice_client.play(source, after=after_playing)
        asyncio.create_task(ctx.send(f"▶️ Now playing: **{title}**"))

    async def skip(self, ctx):
        guild_id = ctx.guild.id
        voice_client = self.current.get(guild_id)
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await ctx.send("⏭ Skipped current song.")
        else:
            await ctx.send("⛔ Nothing is playing.")

    async def stop(self, ctx):
        guild_id = ctx.guild.id
        voice_client = self.current.get(guild_id)
        self.queue[guild_id] = []
        if voice_client and voice_client.is_playing():
            voice_client.stop()
        await ctx.send("⏹ Stopped playback and cleared the queue.")

# -------------------------
# Setup Function for Bot
# -------------------------
async def setup(bot):
    bot.music_player = MusicPlayer(bot)

    @bot.command(name="play")
    async def play(ctx, *, query):
        await bot.music_player.play_song(ctx, query)

    @bot.command(name="skip")
    async def skip(ctx):
        await bot.music_player.skip(ctx)

    @bot.command(name="stop")
    async def stop(ctx):
        await bot.music_player.stop(ctx)

    @bot.command(name="queue")
    async def show_queue(ctx):
        guild_id = ctx.guild.id
        q = bot.music_player.queue.get(guild_id, [])
        if not q:
            return await ctx.send("📭 The queue is empty.")
        desc = "\n".join([f"{i+1}. {song.get('title', 'Unknown')}" for i, song in enumerate(q)])
        await ctx.send(f"🎶 **Queue:**\n{desc}")
