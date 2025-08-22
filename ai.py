# ai.py
import os
import discord
from discord.ui import View, Button
from discord import Embed
import asyncio
import math
import openai

# Load API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------
# AI Function
# -------------------------
async def ask_gpt(question: str) -> str:
    """
    Sends a question to OpenAI ChatCompletion API and returns the answer.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": question}],
            temperature=0.7,
            max_tokens=800
        )
        answer = response.choices[0].message.content
        return answer.strip()
    except Exception as e:
        return f"❌ OpenAI API Error: {e}"

# -------------------------
# Pagination Helpers
# -------------------------
def paginate_text(text: str, max_chars: int = 1000):
    """
    Split text into pages of maximum max_chars characters.
    """
    pages = []
    lines = text.split("\n")
    current_page = ""
    
    for line in lines:
        if len(current_page) + len(line) + 1 > max_chars:
            pages.append(current_page)
            current_page = line + "\n"
        else:
            current_page += line + "\n"
    
    if current_page:
        pages.append(current_page)
    
    return pages

# -------------------------
# Embed Creator
# -------------------------
def create_ai_embed(question: str, page_text: str, page_num: int, total_pages: int):
    embed = Embed(title="🤖 AI Answer", description=page_text, color=discord.Color.blurple())
    embed.set_footer(text=f"Q: {question} | Page {page_num}/{total_pages}")
    return embed

# -------------------------
# Paginator Class
# -------------------------
class AIPaginator(View):
    def __init__(self, ctx, question: str, pages: list[str]):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.question = question
        self.pages = pages
        self.current = 0
        self.total = len(pages)

        # Buttons
        self.add_item(Button(label="◀️ Prev", style=discord.ButtonStyle.primary, custom_id="prev"))
        self.add_item(Button(label="▶️ Next", style=discord.ButtonStyle.primary, custom_id="next"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only allow the command invoker to use the buttons
        return interaction.user.id == self.ctx.author.id

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        self.current = max(self.current - 1, 0)
        embed = create_ai_embed(self.question, self.pages[self.current], self.current + 1, self.total)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        self.current = min(self.current + 1, self.total - 1)
        embed = create_ai_embed(self.question, self.pages[self.current], self.current + 1, self.total)
        await interaction.response.edit_message(embed=embed, view=self)

    async def update_message(self):
        embed = create_ai_embed(self.question, self.pages[self.current], self.current + 1, self.total)
        await self.ctx.send(embed=embed, view=self)
