import discord
import asyncio
import os
import json
import aiohttp
import base64
from discord.ext import commands
from datetime import datetime as dt, date
import aiosqlite

# Define bot intents for message content access
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance with command prefix and intents
client = commands.Bot(command_prefix="!", intents=intents)

# Load configuration from 'data/config.json'
current_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
try:
    with open('data/config.json') as file:
        config = json.load(file)
        print(f"[{current_time}] Successfully loaded config.json in {os.path.basename(__file__)}")
except FileNotFoundError:
    print(f"[{current_time}] File not found in {os.path.basename(__file__)}.")
except json.JSONDecodeError:
    print(f"[{current_time}] Invalid JSON format in {os.path.basename(__file__)}")

# Load API credentials from 'api.json'
current_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
try:
    with open('api.json') as file:
        api = json.load(file)
        print(f"[{current_time}] Successfully loaded api.json in {os.path.basename(__file__)}")
except FileNotFoundError:
    print(f"[{current_time}] File not found in {os.path.basename(__file__)}.")
except json.JSONDecodeError:
    print(f"[{current_time}] Invalid JSON format in {os.path.basename(__file__)}")

def get_headers():
    """Generate headers for API requests with Basic Auth."""
    auth_str = f"{api['API-UNAME']}:{api['API-KEY']}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()
    return {
        "Authorization": f"Basic {b64_auth_str}",
        "User-Agent": f"{api['API-UNAME']}"
    }

async def fetch_api_data(url):
    """Fetch data from the API and return the JSON response."""
    async with aiohttp.ClientSession(headers=get_headers()) as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                current_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{current_time}] Failed to fetch data from {url}: {response.status}")
                return None

async def fetch_market_data():
    """Fetch market data from the API and save it to items.json and prices.json."""
    headers = get_headers()
    
    async with aiohttp.ClientSession() as session:
        try:
            # Fetch items data
            async with session.get("https://api.opsucht.net/market/items", headers=headers) as response:
                items_data = await response.json()
                with open("data/items.json", "w") as f:
                    json.dump(items_data, f, indent=4)
                print(f"[{dt.now().strftime('%Y-%m-%d %H:%M:%S')}] Saved items to data/items.json")
            
            # Fetch prices data
            async with session.get("https://api.opsucht.net/market/prices", headers=headers) as response:
                prices_data = await response.json()
                with open("data/prices.json", "w") as f:
                    json.dump(prices_data, f, indent=4)
                print(f"[{dt.now().strftime('%Y-%m-%d %H:%M:%S')}] Saved prices to data/prices.json")
                
            return prices_data

        except Exception as e:
            print(f"[{dt.now().strftime('%Y-%m-%d %H:%M:%S')}] Error fetching market data: {e}")
            return None

async def save_daily_prices():
    """Save the current day's prices to a file named with the current date."""
    today = date.today().strftime("%d-%m-%Y")
    daily_prices_file = f"data/prices/{today}.json"

    # Ensure the directory exists
    os.makedirs(os.path.dirname(daily_prices_file), exist_ok=True)

    # Fetch and save today's prices to the daily file
    current_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    prices_data = await fetch_market_data()

    if prices_data:
        try:
            with open(daily_prices_file, "w") as f:
                json.dump(prices_data, f, indent=4)
            print(f"[{current_time}] Saved daily prices to {daily_prices_file}")
        except Exception as e:
            print(f"[{current_time}] Error saving daily prices: {e}")

async def cleanup_old_files():
    """Delete files older than 30 days."""
    today = date.today()
    for filename in os.listdir("data/prices"):
        if filename.endswith(".json"):
            file_date = dt.strptime(filename[:-5], "%d-%m-%Y").date()
            if (today - file_date).days > 30:
                os.remove(os.path.join("data/prices", filename))
                current_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{current_time}] Deleted old file: {filename}")

async def periodic_refresh():
    """Periodically refresh and save price data every 60 minutes."""
    while True:
        try:
            await save_daily_prices()  # Save the daily prices
            await cleanup_old_files()  # Clean up old price files
        except Exception as e:
            current_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] Error during periodic refresh: {e}")
        await asyncio.sleep(3600)  # Wait for 60 minutes

async def load_cogs():
    """Load all cogs from the 'commands' directory."""
    cogs_directory = "commands"
    for filename in os.listdir(cogs_directory):
        if filename.endswith(".py") and filename != "__init__.py":
            cog_name = filename[:-3]  # Remove ".py" extension
            current_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                await client.load_extension(f'{cogs_directory}.{cog_name}')
                print(f"[{current_time}] Successfully loaded {cog_name}.")
            except Exception as e:
                print(f"[{current_time}] Failed to load {cog_name}: {e}")

# Initialize the database
async def init_db():
    async with aiosqlite.connect("data/reputation.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS reputation (
                            id INTEGER PRIMARY KEY,
                            giver_id TEXT NOT NULL,
                            receiver_uuid TEXT NOT NULL,
                            reputation INTEGER NOT NULL,
                            UNIQUE(giver_id, receiver_uuid))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY,
                            uuid TEXT NOT NULL,
                            username TEXT NOT NULL)""")
        await db.commit()

@client.event
async def on_ready():
    """Triggered when the bot has successfully connected to Discord."""
    current_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    await init_db()
    await load_cogs()  # Load the Cogs
    print(f"[{current_time}] Logged in as {str(client.user)[:-5]} (ID: {client.user.id})")
    
    # Synchronize application commands
    synced = await client.tree.sync()
    print(f"[{current_time}] Synced {str(len(synced))} Commands")
    
    # Set the bot's activity status
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{config['activity']}"))
    
    # Start the periodic data refresh task
    client.loop.create_task(periodic_refresh())

# Run the bot with the token from 'api.json'
client.run(api['TOKEN'])
