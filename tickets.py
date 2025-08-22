import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio

# -------------------------
# Ticket Config
# -------------------------
MODERATOR_ROLE_ID = 1407630846294491169
ARTIST_ROLE_ID = 1407630978469466112
ADMIN_ROLE_ID = 1407630846294491170
TICKET_CHANNEL_ID = 1407630847703781427
TICKET_LOG_CHANNEL_ID = 1407656944164016138
TICKET_TIMEOUT = 3600  # 1 hour

# -------------------------
# Ticket Close Button
# -------------------------
class ThreadCloseView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        thread = interaction.channel
        guild = interaction.guild
        log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)

        if isinstance(thread, discord.Thread):
            await thread.edit(archived=True, locked=True)
            if log_channel:
                await log_channel.send(f"📝 Ticket `{thread.name}` closed by {interaction.user.mention}")
            try:
                await interaction.response.send_message("✅ Ticket closed!", ephemeral=True)
            except discord.errors.Forbidden:
                pass
        else:
            await interaction.response.send_message("⚠️ This is not a ticket thread.", ephemeral=True)

# -------------------------
# Ticket Open Buttons
# -------------------------
class TicketOpenView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎶 Request Song", style=discord.ButtonStyle.primary, custom_id="req_song")
    async def request_song(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "Song Request")

    @discord.ui.button(label="🎤 Request Cover", style=discord.ButtonStyle.secondary, custom_id="req_cover")
    async def request_cover(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "Cover Request")

    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        guild = interaction.guild
        log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)

        # Create private thread
        thread = await interaction.channel.create_thread(
            name=f"{ticket_type} - {interaction.user.display_name}",
            type=discord.ChannelType.private_thread,
            invitable=False
        )
        await thread.add_user(interaction.user)

        # Send intro message with close button
        await thread.send(
            content=f"👋 Hi {interaction.user.mention}, thank you for opening a **{ticket_type}** ticket!\n"
                    f"Please describe your request below.",
            view=ThreadCloseView()
        )

        # Log ticket
        if log_channel:
            await log_channel.send(
                f"📩 New **{ticket_type}** ticket opened by {interaction.user.mention} → {thread.mention}"
            )

        # Start auto-close task
        asyncio.create_task(self.auto_close_ticket(thread, ticket_type))

        await interaction.response.send_message(
            f"✅ Your **{ticket_type}** ticket has been created: {thread.mention}", ephemeral=True
        )

    async def auto_close_ticket(self, thread, ticket_type: str):
        await asyncio.sleep(TICKET_TIMEOUT - 300)  # 5-minute warning
        try:
            await thread.send(f"⚠ This {ticket_type} ticket will be closed in 5 minutes due to inactivity.")
        except discord.errors.Forbidden:
            return

        await asyncio.sleep(300)
        try:
            await thread.edit(archived=True, locked=True)
            log_channel = thread.guild.get_channel(TICKET_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f"📝 {ticket_type} ticket `{thread.name}` auto-closed due to inactivity.")
        except discord.errors.Forbidden:
            pass

# -------------------------
# Ticket System Cog
# -------------------------
class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup_tickets")
    @commands.has_permissions(administrator=True)
    async def setup_tickets_command(self, ctx):
        """Admin can post the ticket panel manually"""
        view = TicketOpenView()
        embed = discord.Embed(
            title="🎟️ Open a Ticket",
            description=(
                "Choose an option below:\n\n"
                "🎶 **Request Song** – suggest a new original song\n"
                "🎤 **Request Cover** – suggest a cover song\n\n"
                "A private thread will be created where you can talk with the team."
            ),
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed, view=view)
        try: await ctx.message.delete()
        except discord.Forbidden: pass

# -------------------------
# Cog Setup (for hybrid)
# -------------------------
async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
