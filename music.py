import discord
from discord.ext import commands
from discord.ui import View, Button
import yt_dlp
import asyncio

class MusicPlayer:
    def __init__(self):
        self.queue = []
        self.current = None
        self.voice_client = None

    async def join_voice(self, ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            if ctx.guild.voice_client:
                self.voice_client = ctx.guild.voice_client
            else:
                self.voice_client = await channel.connect()
        else:
            await ctx.send("❌ You must be in a voice channel to play music.")

    async def play_song(self, ctx, query):
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "nocheckcertificate": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
        except yt_dlp.utils.DownloadError as e:
            if "[DRM]" in str(e):
                await ctx.send("❌ This video is DRM-protected and cannot be played.")
            else:
                await ctx.send(f"❌ Error fetching video: {e}")
            return

        url = info['url']
        self.current = info

        source = discord.FFmpegPCMAudio(url, options='-vn')
        if not self.voice_client.is_playing():
            self.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.next_song(ctx), ctx.bot.loop))
            await ctx.send(f"▶️ Now playing: **{info.get('title', 'Unknown')}**", view=self.create_controls(ctx))
        else:
            self.queue.append(query)
            await ctx.send(f"⏳ Added to queue: **{info.get('title', 'Unknown')}**")

    async def next_song(self, ctx):
        if self.queue:
            next_query = self.queue.pop(0)
            await self.play_song(ctx, next_query)

    def create_controls(self, ctx):
        view = View()

        async def skip_callback(interaction):
            if self.voice_client.is_playing():
                self.voice_client.stop()
                await interaction.response.send_message("⏭ Skipped!", ephemeral=True)

        async def stop_callback(interaction):
            if self.voice_client.is_playing():
                self.voice_client.stop()
            if self.voice_client:
                await self.voice_client.disconnect()
            await interaction.response.send_message("⏹ Stopped and left the channel.", ephemeral=True)

        skip_btn = Button(label="⏭ Skip", style=discord.ButtonStyle.primary)
        skip_btn.callback = skip_callback
        stop_btn = Button(label="⏹ Stop", style=discord.ButtonStyle.danger)
        stop_btn.callback = stop_callback

        view.add_item(skip_btn)
        view.add_item(stop_btn)
        return view


# -----------------
# Commands for bot.py
# -----------------
async def setup(bot):
    player = MusicPlayer()

    @bot.command(name="play")
    async def play(ctx, *, query):
        await player.join_voice(ctx)
        await player.play_song(ctx, query)

    @bot.command(name="skip")
    async def skip(ctx):
        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.stop()
            await ctx.send("⏭ Skipped current song.")

    @bot.command(name="stop")
    async def stop(ctx):
        if player.voice_client:
            player.voice_client.stop()
            await player.voice_client.disconnect()
            await ctx.send("⏹ Stopped and left the channel.")
