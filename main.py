import discord
import asyncio
import os
import time
import json
import aiohttp
import base64
from discord.ext import commands
import datetime

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

def get_headers():
    """Generate headers for API requests with Basic Auth."""
    auth_str = f"{api['API-UNAME']}:{api['API-KEY']}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()
    return {
        "Authorization": f"Basic {b64_auth_str}",
        "User-Agent": f"{api['API-UNAME']}"
    }


async def save_daily_prices():
    """Save the current day's prices to a file named with the current date."""
    prices_file = "data/prices.json"
    today = datetime.date.today().strftime("%d-%m-%Y")
    daily_prices_file = f"data/prices/{today}.json"

    # Ensure the directory exists
    os.makedirs(os.path.dirname(daily_prices_file), exist_ok=True)

    # Save today's prices to the daily file
    try:
        with open(prices_file, "r") as f:
            prices_data = json.load(f)
        
        with open(daily_prices_file, "w") as f:
            json.dump(prices_data, f, indent=4)

        print(f"Saved daily prices to {daily_prices_file}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error saving daily prices: {e}")

async def cleanup_old_files():
    """Delete files older than 30 days."""
    today = datetime.date.today()
    for filename in os.listdir("data/prices"):
        if filename.endswith(".json"):
            file_date = datetime.datetime.strptime(filename[:-5], "%d-%m-%Y").date()
            if (today - file_date).days > 30:
                os.remove(os.path.join("data/prices", filename))
                print(f"Deleted old file: {filename}")

async def periodic_refresh():
    """Periodically refresh and save price data every 60 minutes."""
    while True:
        try:
            await save_daily_prices()  # Save the daily prices
            await cleanup_old_files()  # Clean up old price files
        except Exception as e:
            print(f"Error during periodic refresh: {e}")
        await asyncio.sleep(3600)  # Wait for 60 minutes


async def load_cogs():
    """
    Load all cogs from the 'commands' directory.
    """
    cogs_directory = "commands"
    for filename in os.listdir(cogs_directory):
        if filename.endswith(".py") and filename != "__init__.py":
            cog_name = filename[:-3]  # Remove ".py" extension
            try:
                await client.load_extension(f'{cogs_directory}.{cog_name}')
                print(f"Successfully loaded {cog_name}.")
            except Exception as e:
                print(f"Failed to load {cog_name}: {e}")

@client.event
async def on_ready():
    """
    Event triggered when the bot has successfully connected to Discord.
    Loads commands, prints the bot's information,
    synchronizes commands, and sets the bot's activity status.
    """
    await load_cogs()  # Load the MarketCog
    print(f"Logged in as {str(client.user)[:-5]} (ID: {client.user.id})")
    
    # Synchronize application commands
    synced = await client.tree.sync()
    print(f"Synced {str(len(synced))} Commands")
    
    # Set the bot's activity status
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{config['activity']}"))
    
    # Start the periodic data refresh task
    client.loop.create_task(periodic_refresh())

# Run the bot with the token from 'api.json'
client.run(api['TOKEN'])
