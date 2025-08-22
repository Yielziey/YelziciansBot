import os
import openai
import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Button

# Load API key
from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------
# AI Interaction
# -------------------------
async def ask_gpt(question: str) -> str:
    """
    Send a question to OpenAI GPT and return the answer.
    """
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",  # use gpt-4 if your API has access
            messages=[
                {"role": "system", "content": "You are a helpful Discord bot."},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ OpenAI API Error:", e)
        return f"Sorry, I couldn't process that question. ({e})"

# -------------------------
# Pagination Utilities
# -------------------------
def paginate_text(text, max_chars=1000):
    """
    Splits long text into chunks for Discord embeds.
    """
    chunks = []
    while len(text) > max_chars:
        split_at = text.rfind("\n", 0, max_chars)
        if split_at == -1:
            split_at = max_chars
        chunks.append(text[:split_at])
        text = text[split_at:].strip()
    chunks.append(text)
    return chunks

def create_ai_embed(question, answer_chunk, page, total_pages):
    embed = discord.Embed(
        title="🤖 AI Answer",
        description=answer_chunk,
        color=discord.Color.purple()
    )
    embed.set_footer(text=f"Q: {question} | Page {page}/{total_pages}")
    return embed

# -------------------------
# Paginator View
# -------------------------
class AIPaginator(View):
    def __init__(self, ctx, question, pages):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.question = question
        self.pages = pages
        self.current = 0

    async def update_message(self, interaction):
        embed = create_ai_embed(self.question, self.pages[self.current], self.current+1, len(self.pages))
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅️ Prev", style=discord.ButtonStyle.primary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current > 0:
            self.current -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current < len(self.pages) - 1:
            self.current += 1
            await self.update_message(interaction)

    @discord.ui.button(label="Regenerate 🔄", style=discord.ButtonStyle.success)
    async def regenerate(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()  # prevent “already responded” error
        new_answer = await ask_gpt(self.question)
        self.pages = paginate_text(new_answer)
        self.current = 0
        await self.update_message(interaction)

# -------------------------
# Cog Setup
# -------------------------
class AICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ask")
    async def ask_command(self, ctx, *, question):
        """
        Ask the AI a question.
        """
        await ctx.defer()
        answer = await ask_gpt(question)
        pages = paginate_text(answer)
        embed = create_ai_embed(question, pages[0], 1, len(pages))
        view = AIPaginator(ctx, question, pages)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(AICog(bot))
