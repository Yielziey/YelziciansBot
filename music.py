import discord
from discord.ext import commands
import yt_dlp
import asyncio

queues = {}           # guild_id: [song dicts]
voice_clients = {}    # guild_id: VoiceClient

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "extract_flat": False,
    "cookiefile": "cookies.txt",
    "default_search": "ytsearch",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


async def play_next(ctx, guild_id):
    queue = queues.get(guild_id)
    if not queue or len(queue) == 0:
        return

    song = queue.pop(0)
    url = song["url"]
    voice_client = voice_clients[guild_id]

    ydl_opts = YDL_OPTIONS.copy()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        source = discord.FFmpegPCMAudio(info['url'], **FFMPEG_OPTIONS)
        voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx, guild_id), ctx.bot.loop))


class MusicView(discord.ui.View):
    def __init__(self, ctx, guild_id):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.guild_id = guild_id

    @discord.ui.button(label="⏯️ Play/Pause", style=discord.ButtonStyle.primary)
    async def play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = voice_clients.get(self.guild_id)
        if not voice or not voice.is_connected():
            return await interaction.response.send_message("❌ Bot is not in a voice channel.", ephemeral=True)

        if voice.is_playing():
            voice.pause()
            await interaction.response.send_message("⏸️ Paused", ephemeral=True)
        elif voice.is_paused():
            voice.resume()
            await interaction.response.send_message("▶️ Resumed", ephemeral=True)
        else:
            if queues.get(self.guild_id):
                await play_next(self.ctx, self.guild_id)
                await interaction.response.send_message("▶️ Playing", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Queue is empty.", ephemeral=True)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = voice_clients.get(self.guild_id)
        if voice and voice.is_playing():
            voice.stop()
            await interaction.response.send_message("⏭️ Skipped", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = voice_clients.get(self.guild_id)
        if voice and voice.is_playing():
            voice.stop()
            queues[self.guild_id] = []
            await interaction.response.send_message("⏹️ Stopped and cleared queue.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)


async def setup(bot: commands.Bot):
    @bot.command()
    async def play(ctx, *, query):
        """Play a song from YouTube (URL or search) with buttons"""
        if not ctx.author.voice:
            return await ctx.send("❌ You must be in a voice channel.")

        channel = ctx.author.voice.channel
        guild_id = ctx.guild.id

        if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
            voice_clients[guild_id] = await channel.connect()
        else:
            await voice_clients[guild_id].move_to(channel)

        ydl_opts = YDL_OPTIONS.copy()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            song = {"title": info.get("title"), "url": info.get("webpage_url")}

        queues.setdefault(guild_id, []).append(song)

        # Play immediately if nothing is playing
        voice = voice_clients[guild_id]
        if not voice.is_playing():
            await play_next(ctx, guild_id)

        # Send buttons
        embed = discord.Embed(title="🎶 Music Player",
                              description=f"✅ Added to queue: **{song['title']}**",
                              color=discord.Color.green())
        view = MusicView(ctx, guild_id)
        await ctx.send(embed=embed, view=view)
