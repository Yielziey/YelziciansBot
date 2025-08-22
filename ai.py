import os
import openai
import asyncio
import discord
from discord.ui import View, Button
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# -------------------------
# GPT Query Function
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
                max_tokens=300
            )
        )
        answer = response.choices[0].message.content.strip()
        return answer
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return "Sorry, I couldn't process that question."

# -------------------------
# Pagination Utilities
# -------------------------
def paginate_text(text: str, max_chars=1000):
    """
    Split long text into pages for Discord embeds.
    """
    pages = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_chars:
            pages.append(current)
            current = line
        else:
            current += line + "\n"
    if current:
        pages.append(current)
    return pages

def create_ai_embed(question: str, answer_part: str, page_num: int, total_pages: int):
    embed = discord.Embed(
        title="🤖 AI Answer",
        description=answer_part,
        color=discord.Color.purple()
    )
    embed.set_footer(text=f"Q: {question} | Page {page_num}/{total_pages}")
    return embed

# -------------------------
# AI Paginator View
# -------------------------
class AIPaginator(View):
    def __init__(self, ctx, question, pages):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.question = question
        self.pages = pages
        self.current_page = 0
        self.message = None  # store sent message

    async def update_message(self):
        embed = create_ai_embed(self.question, self.pages[self.current_page], self.current_page + 1, len(self.pages))
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

    @discord.ui.button(label="Regenerate 🔄", style=discord.ButtonStyle.primary)
    async def regenerate(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()  # acknowledge
        new_answer = await ask_gpt(self.question)
        self.pages = paginate_text(new_answer)
        self.current_page = 0
        await self.update_message()
