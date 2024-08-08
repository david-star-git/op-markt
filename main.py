import discord
import asyncio
import os
from discord.ext import commands
import json

# Define bot intents for message content access
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance with command prefix and intents
client = commands.Bot(command_prefix="!", intents=intents)

# Retrieve the current file path and name
current_file_path = __file__
current_file_name = os.path.basename(current_file_path)

# Load configuration from 'data/config.json'
try:
    with open('data/config.json') as file:
        config = json.load(file)
        print(f"Successfully loaded config.json in {current_file_name}")
except FileNotFoundError:
    print(f"File not found in {current_file_name}.")
except json.JSONDecodeError:
    print(f"Invalid JSON format in {current_file_name}")

# Load API credentials from 'api.json'
try:
    with open('api.json') as file:
        api = json.load(file)
        print(f"Successfully loaded api.json in {current_file_name}")
except FileNotFoundError:
    print(f"File not found in {current_file_name}.")
except json.JSONDecodeError:
    print(f"Invalid JSON format in {current_file_name}")

async def load_commands():
    """
    Load all command extensions from the 'commands' directory.
    Each Python file in this directory is loaded as a cog.
    """
    for filename in os.listdir('./commands'):
        if filename.endswith('.py'):
            await client.load_extension(f'commands.{filename[:-3]}')

@client.event
async def on_ready():
    """
    Event triggered when the bot has successfully connected to Discord.
    Loads commands, prints the bot's information,
    synchronizes commands, and sets the bot's activity status.
    """
    await load_commands()  # Load command cogs
    print(f"Logged in as {str(client.user)[:-5]} (ID: {client.user.id})")
    
    # Synchronize application commands
    synced = await client.tree.sync()
    print(f"Synced {str(len(synced))} Commands")
    
    # Set the bot's activity status
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{config['activity']}"))

# Run the bot with the token from 'api.json'
client.run(api['TOKEN'])
