import discord
import aiosqlite
import aiohttp
from discord import app_commands
from discord.ext import commands
import json

async def get_minecraft_uuid(username: str) -> str:
    """Retrieves the UUID of a Minecraft user based on their username."""
    url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("id")
    return None

class ViewRep(commands.Cog):
    """A Discord Cog that allows users to view the reputation of a Minecraft user."""

    def __init__(self, bot: commands.Bot):
        """Initializes the ViewRep cog."""
        self.bot = bot
        self.config_file = "data/config.json"

        # Load the config file and set embed color
        with open(self.config_file, "r") as f:
            self.config = json.load(f)
        self.embed_color = int(self.config['embed_hex'], 16)

    @app_commands.command(name="view_rep", description="View the reputation of a Minecraft user")
    async def view_rep(self, interaction: discord.Interaction, username: str):
        """
        A slash command that retrieves and displays the reputation of a Minecraft user.

        Args:
            interaction (discord.Interaction): The interaction object that represents the command invocation.
            username (str): The Minecraft username to look up.

        Sends:
            An embedded message showing the positive, negative, and overall reputation of the specified Minecraft user,
            or a message indicating that the user has no reputations.
        """
        # Retrieve the UUID of the Minecraft user
        uuid = await get_minecraft_uuid(username)
        if not uuid:
            await interaction.response.send_message(
                f"Der Benutzername **{username}** existiert nicht in Minecraft.", 
                ephemeral=True, 
                delete_after=5
            )
            return

        # Connect to the SQLite database
        async with aiosqlite.connect("data/reputation.db") as db:
            # Retrieve all reputations received by the user
            cursor = await db.execute("SELECT reputation FROM reputation WHERE receiver_uuid = ?", (uuid,))
            reputations = await cursor.fetchall()

        # Check if the user has received any reputations
        if reputations:
            # Calculate the number of positive and negative reputations
            positive_reps = sum(rep[0] for rep in reputations if rep[0] > 0)
            negative_reps = sum(rep[0] for rep in reputations if rep[0] < 0)
            overall_rep = positive_reps + negative_reps

            # Create an embed to display the reputation statistics
            embed = discord.Embed(title=f"__Reputation von {username}__", color=self.embed_color)
            embed.set_thumbnail(url=f"https://mc-heads.net/avatar/{uuid}/100")
            embed.add_field(name=f"Positive Reputationen", value=str(positive_reps), inline=False)
            embed.add_field(name=f"Negative Reputationen", value=str(negative_reps), inline=False)
            embed.add_field(name=f"Gesamtreputation", value=str(overall_rep), inline=False)

            await interaction.response.send_message(embed=embed)
        else:
            # Send a message indicating that the user has no reputations
            await interaction.response.send_message(
                f"**{username}** hat keine Reputationen.", 
                delete_after=5
            )

async def setup(bot: commands.Bot):
    """Asynchronous setup function to add the ViewRep cog to the bot."""
    await bot.add_cog(ViewRep(bot))
