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
    def __init__(self, bot, guild):
        self.bot = bot
        self.guild = guild
        self.queue = queues.setdefault(guild.id, [])
        self.current = None
        self.voice = None
        self.play_next_event = asyncio.Event()
        self.loop_task = bot.loop.create_task(self.player_loop())
        self.volume = 0.5
        self.is_paused = False

    async def player_loop(self):
        while True:
            if not self.queue:
                await asyncio.sleep(1)
                continue

            self.current = self.queue.pop(0)
            channel = getattr(self.current.requester.author.voice, "channel", None)
            if not channel:
                await self.current.requester.send(f"❌ You are not in a voice channel!")
                continue

            if not self.voice or not self.voice.is_connected():
                self.voice = await channel.connect()

            ydl_opts = {
                "format": "bestaudio/best",
                "quiet": True,
                "cookiefile": "cookies.txt" if os.path.exists("cookies.txt") else None
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(self.current.url, download=False)
                    url2 = info['url']

                source = discord.FFmpegPCMAudio(url2, options=f"-vn -filter:a volume={self.volume}")
                self.voice.play(source, after=lambda e: self.play_next_event.set())
                await self.current.requester.send(f"▶️ Now playing: **{self.current.title}**")

                self.is_paused = False
                await self.play_next_event.wait()
                self.play_next_event.clear()

            except yt_dlp.utils.DownloadError as e:
                await self.current.requester.send(f"❌ Could not play {self.current.title}: {e}")
                continue

# -------------------------
# Bot Setup
# -------------------------
async def setup(bot):

    # --- Play Command
    @bot.command()
    async def play(ctx, *, query):
        guild_id = ctx.guild.id
        player = players.get(guild_id)
        if not player:
            player = MusicPlayer(bot, ctx.guild)
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

    # --- Queue List
    @bot.command()
    async def queuelist(ctx):
        guild_id = ctx.guild.id
        player = players.get(guild_id)
        if not player or (not player.queue and not player.current):
            await ctx.send("❌ The queue is empty.")
            return

        description = ""
        if player.current:
            description += f"▶️ **Now Playing:** {player.current.title}\n\n"
        if player.queue:
            for i, song in enumerate(player.queue, 1):
                description += f"{i}. {song.title}\n"

        embed = discord.Embed(title="🎶 Music Queue", description=description, color=discord.Color.blue())
        await ctx.send(embed=embed)

    # --- Reset Queue
    @bot.command()
    async def reset(ctx):
        guild_id = ctx.guild.id
        player = players.get(guild_id)
        if not player:
            await ctx.send("❌ No music is playing right now.")
            return

        if player.voice and player.voice.is_connected():
            await player.voice.disconnect()

        player.queue.clear()
        player.current = None
        await ctx.send("✅ Queue cleared and disconnected from voice channel.")

    # --- Music Control Buttons
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

    @bot.command()
    async def controls(ctx):
        guild_id = ctx.guild.id
        player = players.get(guild_id)
        if not player:
            await ctx.send("No music is playing right now.")
            return
        view = MusicControlView(player)
        await ctx.send("🎶 Music Controls", view=view)
