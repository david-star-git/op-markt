import discord
import aiosqlite
import aiohttp
from discord import app_commands
from discord.ext import commands

async def get_minecraft_uuid(username: str) -> str:
    """Fetches the Minecraft UUID for a given username using the Mojang API."""
    url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("id")
    return None

class giveRep(commands.Cog):
    """A Discord Cog that allows users to give reputation (Positive or Negative) to Minecraft users."""

    def __init__(self, bot: commands.Bot):
        """Initializes the Rep cog."""
        self.bot = bot

    @app_commands.command(name="give_rep", description="Give reputation to a Minecraft user")
    @app_commands.describe(reputation="Choose Positive or Negative")
    async def giveRep(self, interaction: discord.Interaction, username: str, reputation: str):
        """
        A slash command that allows users to give a Positive or Negative reputation to a Minecraft user.

        Args:
            interaction (discord.Interaction): The interaction object that represents the command invocation.
            username (str): The Minecraft username of the recipient.
            reputation (str): The type of reputation to give ("Positive" or "Negative").

        Sends:
            A message to the user indicating whether the reputation was successfully given, changed, or if an error occurred.
        """
        # Validate the reputation input
        if reputation not in ["Positive", "Negative"]:
            await interaction.response.send_message(
                f"Ungültiger Reputationstyp. Bitte wähle '**Positive**' oder '**Negative**'.", 
                ephemeral=True, 
                delete_after=10
            )
            return

        # Fetch the Minecraft UUID for the given username
        uuid = await get_minecraft_uuid(username)
        if not uuid:
            await interaction.response.send_message(
                f"Der Benutzername **{username}** existiert nicht in Minecraft.", 
                ephemeral=True, 
                delete_after=10
            )
            return

        # Determine the reputation value (+1 for Positive, -1 for Negative)
        reputation_value = 1 if reputation == "Positive" else -1

        # Interact with the SQLite database
        async with aiosqlite.connect("data/reputation.db") as db:
            # Check if the user exists in the users table
            cursor = await db.execute("SELECT * FROM users WHERE uuid = ?", (uuid,))
            user = await cursor.fetchone()

            # If the user does not exist, insert them into the users table
            if not user:
                await db.execute("INSERT INTO users (uuid, username) VALUES (?, ?)", (uuid, username))
                await db.commit()

            # Check if the giver has already given reputation to the receiver
            cursor = await db.execute("SELECT * FROM reputation WHERE giver_id = ? AND receiver_uuid = ?", (interaction.user.id, uuid))
            entry = await cursor.fetchone()

            if entry:
                current_rep = entry[3]
                # If the reputation already exists and is the same, notify the user
                if current_rep == reputation_value:
                    await interaction.response.send_message(
                        f"Du hast bereits eine **{reputation}** Reputation an **{username}** vergeben.", 
                        ephemeral=True, 
                        delete_after=10
                    )
                else:
                    # If the reputation exists but is different, update it
                    await db.execute("UPDATE reputation SET reputation = ? WHERE giver_id = ? AND receiver_uuid = ?",
                                     (reputation_value, interaction.user.id, uuid))
                    await db.commit()
                    await interaction.response.send_message(
                        f"Du hast deine Reputation für **{username}** auf **{reputation}** geändert.", 
                        ephemeral=True, 
                        delete_after=10
                    )
            else:
                # If no reputation exists, insert the new reputation entry
                await db.execute("INSERT INTO reputation (giver_id, receiver_uuid, reputation) VALUES (?, ?, ?)",
                                 (interaction.user.id, uuid, reputation_value))
                await db.commit()
                await interaction.response.send_message(
                    f"Du hast eine **{reputation}** Reputation an **{username}** vergeben.", 
                    ephemeral=True, 
                    delete_after=10
                )

    @giveRep.autocomplete('reputation')
    async def rep_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocompletes the reputation field with "Positive" and "Negative" options."""
        return [
            discord.app_commands.Choice(name="Positive", value="Positive"),
            discord.app_commands.Choice(name="Negative", value="Negative")
        ]

async def setup(bot: commands.Bot):
    """Asynchronous setup function to add the Rep cog to the bot."""
    await bot.add_cog(giveRep(bot))
