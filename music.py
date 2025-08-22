import discord
from discord.ext import commands
import yt_dlp
import asyncio

queues = {}  # guild_id: [song_dict, ...]
current = {}  # guild_id: current song

ffmpeg_options = {
    'options': '-vn -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'extract_flat': 'in_playlist',
}


class MusicButtonView(discord.ui.View):
    def __init__(self, ctx, vc, guild_id):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.vc = vc
        self.guild_id = guild_id

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.primary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc.is_playing():
            self.vc.stop()
            await interaction.response.send_message("⏭ Skipped the current song.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No song is playing.", ephemeral=True)

    @discord.ui.button(label="⏹ Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = self.guild_id
        if self.vc:
            self.vc.stop()
            await self.vc.disconnect()
            queues[guild_id] = []
            await interaction.response.send_message("⏹ Stopped playback and cleared the queue.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Not connected.", ephemeral=True)

    @discord.ui.button(label="⏸ Pause", style=discord.ButtonStyle.secondary)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc.is_playing():
            self.vc.pause()
            await interaction.response.send_message("⏸ Paused the song.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No song is playing.", ephemeral=True)

    @discord.ui.button(label="▶ Resume", style=discord.ButtonStyle.success)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc.is_paused():
            self.vc.resume()
            await interaction.response.send_message("▶ Resumed the song.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No song is paused.", ephemeral=True)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="play")
    async def play(self, ctx, *, query):
        if not ctx.author.voice:
            return await ctx.send("❌ You must be in a voice channel to play music.")
        voice_channel = ctx.author.voice.channel
        guild_id = ctx.guild.id

        vc = ctx.guild.voice_client
        if not vc:
            vc = await voice_channel.connect()
        elif vc.channel != voice_channel:
            await vc.move_to(voice_channel)

        # Get audio URL
        loop = asyncio.get_event_loop()
        try:
            info = await loop.run_in_executor(None, lambda: self.search_yt(query))
        except Exception as e:
            return await ctx.send(f"❌ Error fetching song: {e}")

        if not info:
            return await ctx.send("❌ Could not find the song.")

        queues.setdefault(guild_id, []).append(info)
        await ctx.send(f"✅ Added **{info['title']}** to the queue!")

        if not vc.is_playing():
            await self.start_queue(ctx, vc, guild_id)

    def search_yt(self, query):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if "youtube.com/watch" in query or "youtu.be/" in query:
                info = ydl.extract_info(query, download=False)
            else:
                info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            return {'title': info['title'], 'url': info['url'], 'webpage_url': info.get('webpage_url')}

    async def start_queue(self, ctx, vc, guild_id):
        while queues.get(guild_id):
            current_song = queues[guild_id][0]
            current[guild_id] = current_song

            vc.play(discord.FFmpegPCMAudio(current_song['url'], **ffmpeg_options),
                    after=lambda e: None)

            view = MusicButtonView(ctx, vc, guild_id)
            await ctx.send(f"▶️ Now playing: **{current_song['title']}**", view=view)

            while vc.is_playing() or vc.is_paused():
                await asyncio.sleep(1)
            queues[guild_id].pop(0)


async def setup(bot):
    await bot.add_cog(Music(bot))
