# lyrics.py
import aiohttp
import discord
from discord.ui import View, Button

MAX_CHARS = 2000  # Discord embed max

# -------------------------
# Fetch Lyrics from Google
# -------------------------
async def fetch_lyrics(song_name: str) -> str:
    """
    Fetch full lyrics using Google search scraping.
    Returns lyrics as string.
    """
    query = f"{song_name} lyrics"
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(search_url, headers=headers) as response:
            html = await response.text()

    # Basic extraction: Google puts lyrics in <div class="BNeawe tAd8D AP7Wnd"> blocks
    import re
    matches = re.findall(r'<div class="BNeawe tAd8D AP7Wnd">(.*?)</div>', html)
    if matches:
        lyrics = "\n".join(matches)
        lyrics = lyrics.replace("<br>", "\n").replace("&amp;", "&")
        return lyrics
    return "❌ Lyrics not found."

# -------------------------
# Paginate Lyrics
# -------------------------
def paginate_lyrics(lyrics: str, max_chars: int = MAX_CHARS) -> list:
    pages = []
    lines = lyrics.split("\n")
    current_page = ""
    for line in lines:
        if len(current_page) + len(line) + 1 > max_chars:
            pages.append(current_page)
            current_page = ""
        current_page += line + "\n"
    if current_page:
        pages.append(current_page)
    return pages

# -------------------------
# Create Embed
# -------------------------
def create_lyrics_embed(song_name: str, page_content: str, page_number: int, total_pages: int) -> discord.Embed:
    embed = discord.Embed(
        title=f"Lyrics: {song_name}",
        description=page_content,
        color=discord.Color.purple()
    )
    embed.set_footer(text=f"Page {page_number}/{total_pages}")
    return embed

# -------------------------
# Pagination View
# -------------------------
class LyricsPaginator(View):
    def __init__(self, ctx, song_name: str, pages: list):
        super().__init__(timeout=120)  # 2 min timeout
        self.ctx = ctx
        self.song_name = song_name
        self.pages = pages
        self.current = 0

        # Disable prev button initially
        self.prev_button.disabled = True
        if len(pages) <= 1:
            self.next_button.disabled = True

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        self.current -= 1
        if self.current <= 0:
            self.current = 0
            button.disabled = True
        self.next_button.disabled = False
        embed = create_lyrics_embed(self.song_name, self.pages[self.current], self.current+1, len(self.pages))
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        self.current += 1
        if self.current >= len(self.pages)-1:
            self.current = len(self.pages)-1
            button.disabled = True
        self.prev_button.disabled = False
        embed = create_lyrics_embed(self.song_name, self.pages[self.current], self.current+1, len(self.pages))
        await interaction.response.edit_message(embed=embed, view=self)
