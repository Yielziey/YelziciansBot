import os
import openai
import asyncio
from dotenv import load_dotenv
import discord
from discord.ui import View, Button

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# -------------------------
# AI Functions
# -------------------------
async def ask_gpt(question: str) -> str:
    """
    Send a question to OpenAI GPT and return the answer.
    """
    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful Discord bot."},
                    {"role": "user", "content": question}
                ],
                temperature=0.7,
                max_tokens=800
            )
        )
        answer = response.choices[0].message.content.strip()
        return answer
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return "Sorry, I couldn't process that question."

# -------------------------
# Pagination Helper
# -------------------------
def paginate_text(text, max_chars=1500):
    """
    Split long text into pages for Discord embeds.
    """
    pages = []
    current_page = ""
    for line in text.splitlines():
        if len(current_page) + len(line) + 1 > max_chars:
            pages.append(current_page)
            current_page = ""
        current_page += line + "\n"
    if current_page:
        pages.append(current_page)
    return pages

# -------------------------
# Embed Helper
# -------------------------
def create_ai_embed(question, content, page_num, total_pages):
    embed = discord.Embed(
        title=f"🤖 AI Response",
        description=content,
        color=discord.Color.purple()
    )
    embed.set_footer(text=f"Q: {question} | Page {page_num}/{total_pages}")
    return embed

# -------------------------
# AI Pagination View
# -------------------------
class AIPaginator(View):
    def __init__(self, ctx, question, pages):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.question = question
        self.pages = pages
        self.current = 0

    async def update_message(self, interaction):
        embed = create_ai_embed(self.question, self.pages[self.current], self.current + 1, len(self.pages))
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⏮ Previous", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: Button):
        if self.current > 0:
            self.current -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="Next ⏭", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: Button):
        if self.current < len(self.pages) - 1:
            self.current += 1
            await self.update_message(interaction)

    @discord.ui.button(label="Regenerate 🔄", style=discord.ButtonStyle.primary)
    async def regenerate(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        new_response = await ask_gpt(self.question)
        self.pages = paginate_text(new_response)
        self.current = 0
        await self.update_message(interaction)

    @discord.ui.button(label="Copy 📋", style=discord.ButtonStyle.success)
    async def copy(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(f"📋 Copied content:\n{self.pages[self.current]}", ephemeral=True)
