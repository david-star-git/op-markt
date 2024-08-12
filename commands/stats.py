import discord
import aiosqlite
from discord import app_commands
from discord.ext import commands

class Stats(commands.Cog):
    """A Discord Cog that allows users to check the reputation statistics of a user."""
    def __init__(self, bot: commands.Bot):
        """Initializes the Stats cog."""
        self.bot = bot

    @app_commands.command(name="stats", description="Check the reputation stats of a user")
    async def stats(self, interaction: discord.Interaction, user: discord.User):
        """
        A slash command that allows users to check the reputation statistics of a user.

        Args:
            interaction (discord.Interaction): The interaction object that represents the command invocation.
            user (discord.User): The Discord user whose reputation statistics are to be checked.

        Sends:
            A message indicating the number of positive and negative reputations the user has given, or a message indicating that the user has not given any reputations.
        """
        # Connect to the SQLite database
        async with aiosqlite.connect("data/reputation.db") as db:
            # Retrieve all reputations given by the user
            cursor = await db.execute("SELECT reputation FROM reputation WHERE giver_id = ?", (user.id,))
            reputations = await cursor.fetchall()

        # Check if the user has given any reputations
        if reputations:
            # Calculate the number of positive and negative reputations
            positive_reps = sum(rep[0] for rep in reputations if rep[0] > 0)
            negative_reps = sum(rep[0] for rep in reputations if rep[0] < 0)
            # Send a message with the user's reputation stats
            await interaction.response.send_message(
                f"**{user.mention}** hat **{positive_reps}** positive und **{negative_reps}** negative Reputationen vergeben."
            )
        else:
            # Send a message indicating that the user has not given any reputations
            await interaction.response.send_message(
                f"**{user.mention}** hat keine Reputationen vergeben.", 
                delete_after=5
            )

async def setup(bot: commands.Bot):
    """Asynchronous setup function to add the Stats cog to the bot."""
    await bot.add_cog(Stats(bot))
