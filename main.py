import discord
import asyncio
import os
from discord.ext import commands
import json
import os
import aiosqlite

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="!", intents=intents)

current_file_path = __file__
current_file_name = os.path.basename(current_file_path)
try:
    with open('data/config.json') as file:
        config = json.load(file)
        print(f"successfully loaded config.json in {current_file_name}")
except FileNotFoundError:
    print(f"File not found in {current_file_name}.")
except json.JSONDecodeError:
    print(f"Invalid json format in {current_file_name}")

try:
    with open('api.json') as file:
        api = json.load(file)
        print(f"successfully loaded api.json in {current_file_name}")
except FileNotFoundError:
    print(f"File not found in {current_file_name}.")
except json.JSONDecodeError:
    print(f"Invalid json format in {current_file_name}")

# Initialize the database
async def init_db():
    async with aiosqlite.connect("reputation.db") as db:
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

async def load_commands():
    for filename in os.listdir('./commands'):
        if filename.endswith('.py'):
            await client.load_extension(f'commands.{filename[:-3]}')

@client.event
async def on_ready():
    await init_db()
    await load_commands()
    print(f"logged in as {str(client.user)[:-5]} (ID: {client.user.id})")
    synced = await client.tree.sync()
    print(f"Synced {str(len(synced))} Commands")
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{config['activity']}"))

client.run(api['TOKEN'])
