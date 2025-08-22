import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import yt_dlp
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

queues = {}      # guild_id -> list of Song
players = {}     # guild_id -> MusicPlayer per guild

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
        self.now_playing_msg = None

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

            # Connect if not connected
            if not self.voice or not self.voice.is_connected():
                self.voice = await channel.connect()

            # YDL options
            ydl_opts = {
                "format": "bestaudio/best",
                "quiet": True,
                "cookiefile": "cookies.txt" if os.path.exists("cookies.txt") else None
            }

            # Attempt to play song, refresh URL on 403
            for attempt in range(3):
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(self.current.url, download=False)
                        url2 = info['url']

                    source = discord.FFmpegPCMAudio(url2, options=f"-vn -filter:a volume={self.volume}")
                    self.voice.play(source, after=lambda e: self.play_next_event.set())

                    # Send/Update Now Playing message with buttons
                    view = MusicControlView(self)
                    if self.now_playing_msg:
                        try:
                            await self.now_playing_msg.edit(content=f"▶️ Now Playing: **{self.current.title}**", view=view)
                        except:
                            self.now_playing_msg = await self.current.requester.send(f"▶️ Now Playing: **{self.current.title}**", view=view)
                    else:
                        self.now_playing_msg = await self.current.requester.send(f"▶️ Now Playing: **{self.current.title}**", view=view)

                    self.is_paused = False
                    await self.play_next_event.wait()
                    self.play_next_event.clear()
                    break

                except yt_dlp.utils.DownloadError as e:
                    if "403" in str(e):
                        await self.current.requester.send(f"⚠️ URL expired, refreshing and retrying {self.current.title}...")
                        continue
                    else:
                        await self.current.requester.send(f"❌ Could not play {self.current.title}: {e}")
                        break
                except Exception as e:
                    await self.current.requester.send(f"❌ Could not play {self.current.title}: {e}")
                    break

# -------------------------
# Music Controls
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
        """Play a song from YouTube or Spotify"""
        guild_id = ctx.guild.id
        player = players.get(guild_id)
        if not player:
            player = MusicPlayer(bot, ctx.guild)
            players[guild_id] = player

        # Spotify handling
        if "spotify.com" in query:
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
    async def qlist(ctx):
        """Show upcoming songs"""
        guild_id = ctx.guild.id
        player = players.get(guild_id)
        if not player or not player.queue:
            await ctx.send("No songs in the queue.")
            return
        embed = discord.Embed(title="🎶 Queue", description="\n".join([f"{i+1}. {song.title}" for i, song in enumerate(player.queue)]))
        await ctx.send(embed=embed)

    @bot.command()
    async def reset(ctx):
        """Stop and clear queue"""
        guild_id = ctx.guild.id
        player = players.get(guild_id)
        if not player:
            await ctx.send("No music player running.")
            return
        if player.voice:
            await player.voice.disconnect()
        player.queue.clear()
        await ctx.send("✅ Music queue cleared and player stopped.")
