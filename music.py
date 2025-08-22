import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import asyncio
import yt_dlp
import os

FFMPEG_PATH = r"C:\Users\BioStaR\Downloads\ffmpeg\bin\ffmpeg.exe"  # Update if needed

# -------------------------
# Music Queue & Player
# -------------------------
class Song:
    def __init__(self, url, title, requester):
        self.url = url
        self.title = title
        self.requester = requester

class MusicPlayer:
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.current = None
        self.voice_client = None
        self.volume = 0.5
        self.lock = asyncio.Lock()

    async def play_next(self, ctx):
        if not self.queue:
            self.current = None
            return
        self.current = self.queue.pop(0)
        source = await self.get_source(self.current.url)
        self.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop))
        await ctx.send(f"🎶 Now playing: **{self.current.title}** (requested by {self.current.requester.mention})")

    async def get_source(self, url):
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
        return discord.FFmpegPCMAudio(audio_url, executable=FFMPEG_PATH, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options=f'-vn -filter:a "volume={self.volume}"')

music_players = {}

def get_player(ctx):
    guild_id = ctx.guild.id
    if guild_id not in music_players:
        music_players[guild_id] = MusicPlayer(ctx.bot)
    return music_players[guild_id]

# -------------------------
# Music Commands
# -------------------------
class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="join")
    async def join(self, ctx):
        if ctx.author.voice is None:
            return await ctx.send("❌ You are not in a voice channel.")
        channel = ctx.author.voice.channel
        player = get_player(ctx)
        if player.voice_client is None:
            player.voice_client = await channel.connect()
        else:
            await player.voice_client.move_to(channel)
        await ctx.send(f"✅ Connected to {channel.name}")

    @commands.command(name="leave")
    async def leave(self, ctx):
        player = get_player(ctx)
        if player.voice_client:
            await player.voice_client.disconnect()
            player.voice_client = None
            player.queue.clear()
            player.current = None
            await ctx.send("👋 Disconnected and cleared queue.")

    @commands.command(name="play")
    async def play(self, ctx, *, url):
        if ctx.author.voice is None:
            return await ctx.send("❌ Join a voice channel first.")
        player = get_player(ctx)
        if player.voice_client is None:
            player.voice_client = await ctx.author.voice.channel.connect()

        # Get title using yt-dlp
        with yt_dlp.YoutubeDL({'quiet': True, 'format': 'bestaudio'}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')

        song = Song(url, title, ctx.author)
        player.queue.append(song)

        if not player.voice_client.is_playing() and not player.current:
            await player.play_next(ctx)

        # Show control buttons
        view = MusicControlView(player, ctx)
        await ctx.send(f"✅ Added **{title}** to the queue.", view=view)

# -------------------------
# Button Controls
# -------------------------
class MusicControlView(View):
    def __init__(self, player, ctx):
        super().__init__(timeout=None)
        self.player = player
        self.ctx = ctx

    @discord.ui.button(label="⏯️ Play/Pause", style=discord.ButtonStyle.primary)
    async def play_pause(self, interaction: discord.Interaction, button: Button):
        vc = self.player.voice_client
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Paused", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Resumed", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing", ephemeral=True)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: Button):
        vc = self.player.voice_client
        if vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏩ Skipped", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing", ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: Button):
        vc = self.player.voice_client
        if vc.is_playing() or vc.is_paused():
            vc.stop()
        self.player.queue.clear()
        self.player.current = None
        await interaction.response.send_message("⏹️ Stopped and cleared queue", ephemeral=True)

    @discord.ui.button(label="🔉 Volume -", style=discord.ButtonStyle.secondary)
    async def vol_down(self, interaction: discord.Interaction, button: Button):
        self.player.volume = max(0.0, self.player.volume - 0.1)
        await interaction.response.send_message(f"🔉 Volume: {int(self.player.volume*100)}%", ephemeral=True)

    @discord.ui.button(label="🔊 Volume +", style=discord.ButtonStyle.secondary)
    async def vol_up(self, interaction: discord.Interaction, button: Button):
        self.player.volume = min(2.0, self.player.volume + 0.1)
        await interaction.response.send_message(f"🔊 Volume: {int(self.player.volume*100)}%", ephemeral=True)

# -------------------------
# Cog Setup
# -------------------------
async def setup(bot):
    await bot.add_cog(Music(bot))
