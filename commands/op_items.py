import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiohttp
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
import asyncio
import urllib.parse

class DataFetcher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.json_file_path = 'data/op_items_data.json'
        self.config_file = "data/config.json"

        with open(self.config_file, "r") as f:
            self.config = json.load(f)
            self.embed_color = int(self.config['embed_hex'], 16)

    async def download_data(self, url):
        """Download data from the given URL and return the parsed HTML content."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    return BeautifulSoup(html, 'html.parser')
                else:
                    return None

    def levenshtein_distance(self, s1, s2):
        """Calculate the Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    async def find_best_match(self, query, items):
        """Find the best matching item based on the query."""
        query = query.lower()
        best_match = None
        min_distance = float('inf')
        for category, category_items in items.items():
            for item_name, item_data in category_items.items():
                distance = self.levenshtein_distance(query, item_name.lower())
                if distance < min_distance:
                    min_distance = distance
                    best_match = (category, item_name, item_data)
        return best_match

    def load_existing_prices(self):
        """Load existing prices from the JSON file if it exists."""
        if os.path.exists(self.json_file_path):
            with open(self.json_file_path, 'r') as f:
                return json.load(f)
        return {}

    def get_price_from_existing_data(self, item_name, existing_data):
        """Get the price from existing data if available."""
        for category, items in existing_data.items():
            if item_name in items:
                return items[item_name].get('price', 'N/A')
        return 'N/A'
    
    def format_item_name(self, item_name):
        """Format the item name to replace underscores with spaces, decode URL-encoded names, and capitalize each word."""
        name_without_extension = os.path.splitext(item_name)[0]  # Remove the .png extension
        decoded_name = urllib.parse.unquote(name_without_extension)  # Decode the URL-encoded string
        return decoded_name.replace('_', ' ').title()  # Replace underscores and capitalize words

    async def update_json_with_prices(self, interaction):
        # Check if the last update was more than an hour ago
        if not hasattr(self, 'last_updated') or datetime.now() - self.last_updated > timedelta(hours=1):
            urls = [
                "https://wiki.opsucht.net/op/spitzhacken/",
                "https://wiki.opsucht.net/op/schwerter/",
                "https://wiki.opsucht.net/op/aexte/",
                "https://wiki.opsucht.net/op/schaufeln/",
                "https://wiki.opsucht.net/op/hacken/",
                "https://wiki.opsucht.net/op/ruestungen/",
                "https://wiki.opsucht.net/op/schilde/",
                "https://wiki.opsucht.net/op/boegen/",
                "https://wiki.opsucht.net/op/armbrueste/",
                "https://wiki.opsucht.net/op/angeln/",
                "https://wiki.opsucht.net/op/talismane/",
                "https://wiki.opsucht.net/op/fluegel/",
                "https://wiki.opsucht.net/op/plueschtiere/",
                "https://wiki.opsucht.net/op/sonstiges/"
            ]

            items_data = {}
            existing_data = self.load_existing_prices()

            # Download and parse data from each URL
            for url in urls:
                category = url.split('/')[-2]
                # Replace "ue", "oe", "ae" with "ü", "ö", "ä"
                category = category.replace("ue", "ü").replace("oe", "ö").replace("ae", "ä")
                # Encode the category
                encoded_category = urllib.parse.quote(category)

                soup = await self.download_data(url)
                if soup:
                    items_data.setdefault(encoded_category, {})  # Ensure the encoded category exists in the dictionary
                    for img in soup.find_all("img"):
                        src = img.get("src")
                        if "assets/op" in src:
                            item_name = src.split("/")[-1]
                            # Check existing data for price
                            price = self.get_price_from_existing_data(item_name, existing_data)
                            item_data = {
                                "price": price
                            }
                            items_data[encoded_category][item_name] = item_data

            # Save updated data to JSON file
            with open(self.json_file_path, 'w') as f:
                json.dump(items_data, f, indent=4)

            # Log the update
            self.last_updated = datetime.now()  # Update last_updated variable
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] Updated {self.json_file_path}")

    @app_commands.command(name="op_items", description="Get the price for an op-item")
    @app_commands.describe(query="The name of the item to search for")
    async def fetch_items(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()  # Acknowledge the command before doing long operations

        await self.update_json_with_prices(interaction)

        # Load updated items data
        with open(self.json_file_path, 'r') as f:
            items_data = json.load(f)

        # Fuzzy find the best match
        best_match = await self.find_best_match(query, items_data)
        if best_match:
            category, item_name, item_data = best_match
            formatted_item_name = self.format_item_name(item_name)

            decoded_category = urllib.parse.unquote(category)
            embed = discord.Embed(
                title=formatted_item_name,
                description = f"**Kategorie**: {decoded_category.title()}\n**Preis**: {item_data['price']}"
            )
            item_image_url = f"https://wiki.opsucht.net/assets/op/item/{category}/{item_name}"
            lore_image_url = f"https://wiki.opsucht.net/assets/op/lore/{category}/{item_name}"
            embed.set_thumbnail(url=item_image_url)
            embed.set_image(url=lore_image_url)
            embed.color = self.embed_color
            embed.set_footer(text=f"{self.config['name']} • JinglingJester")

            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("No items found matching your query.")

async def setup(bot):
    await bot.add_cog(DataFetcher(bot))
