import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import yt_dlp
import os

# -------------------------
# Globals
# -------------------------
queues = {}  # guild_id -> list of songs
players = {}  # guild_id -> MusicPlayer per guild

# -------------------------
# Song Object
# -------------------------
class Song:
    def __init__(self, title, url, requester):
        self.title = title
        self.url = url
        self.requester = requester

# -------------------------
# Music Player
# -------------------------
class MusicPlayer:
    def __init__(self, bot, guild, text_channel):
        self.bot = bot
        self.guild = guild
        self.queue = queues.setdefault(guild.id, [])
        self.current = None
        self.voice = None
        self.text_channel = text_channel
        self.play_next_event = asyncio.Event()
        self.loop_task = bot.loop.create_task(self.player_loop())
        self.volume = 0.5
        self.is_paused = False
        self.controls_view = MusicControlView(self)

    async def player_loop(self):
        while True:
            if not self.queue:
                await asyncio.sleep(1)
                continue

            self.current = self.queue.pop(0)
            channel = getattr(self.current.requester.author.voice, "channel", None)
            if not channel:
                await self.text_channel.send(f"❌ {self.current.requester.author.mention}, you are not in a voice channel!")
                continue

            if not self.voice or not self.voice.is_connected():
                try:
                    self.voice = await channel.connect()
                except discord.ClientException:
                    pass

            ydl_opts = {
                "format": "bestaudio/best",
                "quiet": True,
                "nocheckcertificate": True,
                "cookiefile": "cookies.txt" if os.path.exists("cookies.txt") else None
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(self.current.url, download=False)
                    url2 = info['url']

                source = discord.FFmpegPCMAudio(url2, options=f"-vn -filter:a volume={self.volume}")
                self.voice.play(source, after=lambda e: self.bot.loop.call_soon_threadsafe(self.play_next_event.set))
                
                # Always show controls view in text channel
                await self.text_channel.send(f"▶️ Now playing: **{self.current.title}**", view=self.controls_view)

                self.is_paused = False
                await self.play_next_event.wait()
                self.play_next_event.clear()

            except Exception as e:
                await self.text_channel.send(f"❌ Could not play **{self.current.title}**: {e}")
                continue

# -------------------------
# Music Control Buttons
# -------------------------
class MusicControlView(View):
    def __init__(self, player):
        super().__init__(timeout=None)
        self.player = player

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.primary)
    async def skip(self, interaction: discord.Interaction, button: Button):
        if self.player.voice and self.player.voice.is_playing():
            self.player.voice.stop()
            await interaction.response.send_message("⏭ Skipped!", ephemeral=True)

    @discord.ui.button(label="⏹ Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: Button):
        if self.player.voice:
            await self.player.voice.disconnect()
            self.player.queue.clear()
            await interaction.response.send_message("⏹ Stopped and cleared queue!", ephemeral=True)

    @discord.ui.button(label="⏸ Pause", style=discord.ButtonStyle.secondary)
    async def pause(self, interaction: discord.Interaction, button: Button):
        if self.player.voice and self.player.voice.is_playing():
            self.player.voice.pause()
            self.player.is_paused = True
            await interaction.response.send_message("⏸ Paused!", ephemeral=True)

    @discord.ui.button(label="▶ Resume", style=discord.ButtonStyle.success)
    async def resume(self, interaction: discord.Interaction, button: Button):
        if self.player.voice and self.player.is_paused:
            self.player.voice.resume()
            self.player.is_paused = False
            await interaction.response.send_message("▶ Resumed!", ephemeral=True)

    @discord.ui.button(label="🔊 Volume +", style=discord.ButtonStyle.primary)
    async def vol_up(self, interaction: discord.Interaction, button: Button):
        self.player.volume = min(self.player.volume + 0.1, 2.0)
        await interaction.response.send_message(f"🔊 Volume: {int(self.player.volume*100)}%", ephemeral=True)

    @discord.ui.button(label="🔉 Volume -", style=discord.ButtonStyle.primary)
    async def vol_down(self, interaction: discord.Interaction, button: Button):
        self.player.volume = max(self.player.volume - 0.1, 0.0)
        await interaction.response.send_message(f"🔉 Volume: {int(self.player.volume*100)}%", ephemeral=True)

# -------------------------
# Bot Setup
# -------------------------
async def setup(bot):
    @bot.command()
    async def play(ctx, *, query):
        """Play a song from YouTube or Spotify link"""
        guild_id = ctx.guild.id
        player = players.get(guild_id)
        if not player:
            player = MusicPlayer(bot, ctx.guild, ctx.channel)
            players[guild_id] = player

        # Spotify link handling
        if "spotify.com" in query:
            import spotipy
            from spotipy.oauth2 import SpotifyClientCredentials
            sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
            ))

            if "track" in query:
                track_id = query.split("/")[-1].split("?")[0]
                track = sp.track(track_id)
                query = f"{track['name']} {track['artists'][0]['name']}"
            elif "playlist" in query:
                playlist_id = query.split("/")[-1].split("?")[0]
                playlist = sp.playlist_items(playlist_id)
                for item in playlist['items']:
                    track = item['track']
                    youtube_query = f"{track['name']} {track['artists'][0]['name']}"
                    player.queue.append(Song(track['name'], youtube_query, ctx))
                await ctx.send(f"✅ Added **{len(playlist['items'])} tracks** to the queue.")
                return

        player.queue.append(Song(query, query, ctx))
        await ctx.send(f"✅ Added **{query}** to the queue.")

    @bot.command()
    async def queuelist(ctx):
        """Shows the current queue"""
        guild_id = ctx.guild.id
        player = players.get(guild_id)
        if not player or not player.queue:
            return await ctx.send("Queue is empty.")
        msg = "\n".join([f"{i+1}. {s.title}" for i, s in enumerate(player.queue)])
        await ctx.send(f"🎶 Queue:\n{msg}")

    @bot.command()
    async def reset(ctx):
        """Clears the queue and stops the player"""
        guild_id = ctx.guild.id
        player = players.get(guild_id)
        if player:
            if player.voice:
                await player.voice.disconnect()
            player.queue.clear()
        await ctx.send("✅ Queue cleared and player stopped.")
