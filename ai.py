# ai.py
import discord
from discord.ui import View, Button
from discord.ext import commands
from openai import OpenAI
import math

import os

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------
# AI Chat Function
# -------------------------
async def ask_gpt(prompt: str) -> str:
    """
    Send prompt to OpenAI GPT model and return the assistant's response.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    # Extract content
    return response.choices[0].message.content.strip()

# -------------------------
# Pagination Helpers
# -------------------------
def paginate_text(text: str, page_size: int = 1500):
    """
    Split text into pages of max page_size characters.
    """
    pages = []
    for i in range(0, len(text), page_size):
        pages.append(text[i:i+page_size])
    return pages

def create_ai_embed(question: str, answer: str, page: int, total_pages: int) -> discord.Embed:
    embed = discord.Embed(
        title="🤖 AI Answer",
        description=answer,
        color=discord.Color.purple()
    )
    embed.set_footer(text=f"Q: {question} | Page {page}/{total_pages}")
    return embed

# -------------------------
# Paginator View
# -------------------------
class AIPaginator(View):
    def __init__(self, ctx: commands.Context, question: str, pages: list[str]):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.question = question
        self.pages = pages
        self.current_page = 0
        self.message = None

        # Add buttons
        self.add_item(Button(label="⏮️ Prev", style=discord.ButtonStyle.primary))
        self.add_item(Button(label="⏭️ Next", style=discord.ButtonStyle.primary))
        self.add_item(Button(label="Regenerate 🔄", style=discord.ButtonStyle.success))

        # Assign callbacks
        self.children[0].callback = self.prev_page
        self.children[1].callback = self.next_page
        self.children[2].callback = self.regenerate

    async def update_message(self):
        embed = create_ai_embed(
            self.question,
            self.pages[self.current_page],
            self.current_page + 1,
            len(self.pages)
        )
        if self.message:
            await self.message.edit(embed=embed, view=self)
        else:
            self.message = await self.ctx.send(embed=embed, view=self)

    async def prev_page(self, interaction: discord.Interaction):
        self.current_page = (self.current_page - 1) % len(self.pages)
        await interaction.response.edit_message(embed=create_ai_embed(
            self.question,
            self.pages[self.current_page],
            self.current_page + 1,
            len(self.pages)
        ), view=self)

    async def next_page(self, interaction: discord.Interaction):
        self.current_page = (self.current_page + 1) % len(self.pages)
        await interaction.response.edit_message(embed=create_ai_embed(
            self.question,
            self.pages[self.current_page],
            self.current_page + 1,
            len(self.pages)
        ), view=self)

    async def regenerate(self, interaction: discord.Interaction):
        await interaction.response.defer()  # Acknowledge button press
        new_answer = await ask_gpt(self.question)
        self.pages = paginate_text(new_answer)
        self.current_page = 0
        await self.update_message()
