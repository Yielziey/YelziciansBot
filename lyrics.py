import aiohttp
import discord
from discord.ui import View, Button
import asyncio

LYRICS_API_URL = "https://api.lyrics.ovh/v1/{artist}/{song}"

# -------------------------
# Fetch Lyrics Function
# -------------------------
async def fetch_lyrics(song_name: str, artist_name: str = None) -> str:
    """
    Fetch lyrics from API. If artist is provided, search specific artist.
    """
    async with aiohttp.ClientSession() as session:
        try:
            if artist_name:
                url = LYRICS_API_URL.format(artist=artist_name, song=song_name)
            else:
                # if no artist, attempt generic search (API may fail)
                url = LYRICS_API_URL.format(artist="", song=song_name)

            async with session.get(url) as resp:
                if resp.status != 200:
                    return "❌ Lyrics not found."
                data = await resp.json()
                lyrics = data.get("lyrics", "Lyrics not available.")
                return lyrics
        except Exception as e:
            print(f"Error fetching lyrics: {e}")
            return "❌ Failed to fetch lyrics."

# -------------------------
# Pagination Utilities
# -------------------------
def paginate_lyrics(lyrics_text: str, max_chars=1000):
    pages = []
    current = ""
    for line in lyrics_text.split("\n"):
        if len(current) + len(line) + 1 > max_chars:
            pages.append(current)
            current = line
        else:
            current += line + "\n"
    if current:
        pages.append(current)
    return pages

def create_lyrics_embed(song_name: str, artist_name: str, lyrics_part: str, page_num: int, total_pages: int):
    embed = discord.Embed(
        title=f"🎵 {song_name}",
        description=lyrics_part,
        color=discord.Color.gold()
    )
    if artist_name:
        embed.set_author(name=f"Artist: {artist_name}")
    embed.set_footer(text=f"Page {page_num}/{total_pages}")
    return embed

# -------------------------
# Lyrics Paginator View
# -------------------------
class LyricsPaginator(View):
    def __init__(self, ctx, song_name, artist_name, pages):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.song_name = song_name
        self.artist_name = artist_name
        self.pages = pages
        self.current_page = 0
        self.message = None

    async def update_message(self):
        embed = create_lyrics_embed(self.song_name, self.artist_name, self.pages[self.current_page], self.current_page + 1, len(self.pages))
        if self.message:
            await self.message.edit(embed=embed, view=self)
        else:
            self.message = await self.ctx.send(embed=embed, view=self)

    @discord.ui.button(label="⬅️ Prev", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.defer()
            await self.update_message()

    @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await interaction.response.defer()
            await self.update_message()
