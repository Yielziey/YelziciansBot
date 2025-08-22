import discord
from discord.ext import commands
from discord.ui import View, Button
import yt_dlp
import asyncio
import os

YTDLP_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "cookiefile": "cookies.txt",  # <-- your cookies.txt
    "extract_flat": True,
    "playlist_items": "0-100",  # for playlists, up to 100 songs
}

queues = {}  # {guild_id: [url1, url2,...]}
players = {}  # {guild_id: current voice player}

# -------------------------
# Music Controls UI
# -------------------------
class MusicControls(View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.green)
    async def skip(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await self.ctx.invoke(self.ctx.bot.get_command("skip"))

    @discord.ui.button(label="⏹ Stop", style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await self.ctx.invoke(self.ctx.bot.get_command("stop"))

    @discord.ui.button(label="📋 Queue", style=discord.ButtonStyle.blurple)
    async def queue(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await self.ctx.invoke(self.ctx.bot.get_command("queue"))

# -------------------------
# Helper Functions
# -------------------------
async def play_next(ctx, guild_id):
    if guild_id not in queues or not queues[guild_id]:
        players.pop(guild_id, None)
        return
    url = queues[guild_id].pop(0)

    YTDL = yt_dlp.YoutubeDL(YTDLP_OPTIONS)
    info = YTDL.extract_info(url, download=False)
    if "entries" in info:  # Playlist
        info = info["entries"][0]

    url2 = info["url"]
    title = info.get("title", "Unknown Track")

    voice = discord.utils.get(ctx.guild.voice_channels, guild=ctx.voice_client.channel) or ctx.voice_client
    if not voice:
        return await ctx.send("⛔ Bot is not connected to a voice channel!")

    players[guild_id] = voice
    source = discord.FFmpegPCMAudio(url2, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5")
    voice.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx, guild_id), ctx.bot.loop))

    embed = discord.Embed(title="🎶 Now Playing", description=title, color=discord.Color.blurple())
    await ctx.send(embed=embed, view=MusicControls(ctx))

# -------------------------
# Commands
# -------------------------
async def setup(bot):
    @bot.command()
    async def play(ctx, *, query):
        """Play a song or playlist from YouTube"""
        if not ctx.voice_client:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                return await ctx.send("⛔ You need to join a voice channel first!")

        guild_id = ctx.guild.id
        YTDL = yt_dlp.YoutubeDL(YTDLP_OPTIONS)
        info = YTDL.extract_info(query, download=False)
        urls = []
        if "entries" in info:  # Playlist
            for entry in info["entries"]:
                if entry:
                    urls.append(entry["webpage_url"])
        else:
            urls.append(info["webpage_url"])

        if guild_id not in queues:
            queues[guild_id] = []

        queues[guild_id].extend(urls)
        await ctx.send(f"✅ Added {len(urls)} song(s) to the queue.")

        if guild_id not in players or not ctx.voice_client.is_playing():
            await play_next(ctx, guild_id)

    @bot.command()
    async def skip(ctx):
        """Skip current song"""
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await ctx.send("⏭ Skipped the current song.")
        else:
            await ctx.send("⛔ Nothing is playing.")

    @bot.command()
    async def stop(ctx):
        """Stop playback and clear queue"""
        vc = ctx.voice_client
        guild_id = ctx.guild.id
        if vc:
            vc.stop()
            queues[guild_id] = []
            await ctx.send("⏹ Stopped playback and cleared the queue.")
        else:
            await ctx.send("⛔ Not connected.")

    @bot.command()
    async def queue(ctx):
        """Show current queue"""
        guild_id = ctx.guild.id
        if guild_id in queues and queues[guild_id]:
            desc = "\n".join(f"{i+1}. {url}" for i, url in enumerate(queues[guild_id][:10]))
            await ctx.send(f"📋 Current Queue:\n{desc}")
        else:
            await ctx.send("📋 Queue is empty.")
