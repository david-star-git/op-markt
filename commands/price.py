import discord
import aiohttp
import json
import os
import time
import base64
from discord import app_commands
from discord.ext import commands

# Retrieve the current file path and name
current_file_path = __file__
current_file_name = os.path.basename(current_file_path)

# Load the configuration from 'data/config.json'
try:
    with open('data/config.json') as file:
        config = json.load(file)
        print(f"Successfully loaded config.json in {current_file_name}")
except FileNotFoundError:
    print(f"File not found in {current_file_name}.")
except json.JSONDecodeError:
    print(f"Invalid JSON format in {current_file_name}")

# Set embed color from configuration
embed_color = int(config['embed_hex'], 16)

class MarketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://api.opsucht.net/market"
        self.items_file = "data/items.json"
        self.load_api_credentials()
        self.last_refresh = 0

    def load_api_credentials(self):
        """Load API credentials from 'api.json'."""
        with open("api.json", "r") as f:
            credentials = json.load(f)
            self.api_key = credentials["API-KEY"]
            self.api_uname = credentials["API-UNAME"]

    def get_headers(self):
        """Generate headers for API requests with Basic Auth."""
        auth_str = f"{self.api_uname}:{self.api_key}"
        b64_auth_str = base64.b64encode(auth_str.encode()).decode()
        return {
            "Authorization": f"Basic {b64_auth_str}",
            "User-Agent": f"{self.api_uname}"
        }

    async def refresh_items(self):
        """Refresh item data from the API if the file is outdated or missing."""
        if not os.path.exists(self.items_file) or time.time() - self.last_refresh > 3600:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/items", headers=self.get_headers()) as response:
                    if response.status == 200:
                        items = await response.json()
                        os.makedirs(os.path.dirname(self.items_file), exist_ok=True)
                        with open(self.items_file, "w") as f:
                            json.dump(items, f)
                        self.last_refresh = time.time()
                        print("Refreshed data/items.json")
                    else:
                        print(f"Failed to refresh items: {response.status}")

    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        Calculate the Levenshtein distance between two strings.
        Args:
            s1 (str): First string.
            s2 (str): Second string.
        Returns:
            int: Levenshtein distance between s1 and s2.
        """
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

    def find_best_match(self, query: str, items: list[str]) -> str:
        """
        Find the best matching item from a list based on the query string using fuzzy matching.
        Args:
            query (str): Query string to match.
            items (list[str]): List of item names to search.
        Returns:
            str: The best matching item name.
        """
        query = query.lower()
        
        # Find items that contain the query as a substring
        containing_matches = [item for item in items if query in item.lower()]
        
        if containing_matches:
            # Use Levenshtein distance to find the closest match among substring matches
            closest_match = None
            lowest_distance = float('inf')
            
            for item in containing_matches:
                distance = self.levenshtein_distance(query, item.lower())
                if distance < lowest_distance:
                    closest_match = item
                    lowest_distance = distance
            
            return closest_match
        
        # If no substring matches, use Levenshtein distance for fuzzy matching
        closest_match = None
        lowest_distance = float('inf')
        
        for item in items:
            distance = self.levenshtein_distance(query, item.lower())
            if distance < lowest_distance:
                closest_match = item
                lowest_distance = distance
        
        return closest_match

    def format_item_name(self, item_name: str) -> str:
        """
        Format item names for display, capitalizing each word.
        Args:
            item_name (str): The item name to format.
        Returns:
            str: Formatted item name.
        """
        return ' '.join(word.capitalize() for word in item_name.replace('_', ' ').split())

    def get_item_image_url(self, item_name: str) -> str:
        """
        Generate the URL for the item image.
        Args:
            item_name (str): The item name to create the URL for.
        Returns:
            str: The URL of the item image.
        """
        formatted_name = item_name.lower().replace(' ', '_')
        return f"https://mc.nerothe.com/img/1.21/minecraft_{formatted_name}.png"

    def format_price(self, price: float) -> str:
        """
        Format a price with thousand separators and currency symbol.
        Args:
            price (float): The price to format.
        Returns:
            str: Formatted price with currency symbol.
        """
        rounded_price = round(price, 1)
        formatted_price = f"{rounded_price:,.1f}".replace(',', ' ').replace('.', ',').replace(' ', '.')
        return formatted_price + " $"

    @app_commands.command(name="price", description="Get the price for an item")
    async def fetch_price(self, interaction: discord.Interaction, item_name: str):
        """
        Command to fetch and display the price for an item.
        Args:
            interaction (discord.Interaction): The interaction that triggered the command.
            item_name (str): The name of the item to fetch the price for.
        """
        await self.refresh_items()
        with open(self.items_file, "r") as f:
            items = json.load(f)

        best_match = self.find_best_match(item_name, items)
        if best_match:
            item_name_formatted = self.format_item_name(best_match)
            item_image_url = self.get_item_image_url(best_match)
            buy_price = None
            sell_price = None
            
            # Fetch prices from the API
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/price/{best_match}", headers=self.get_headers()) as response:
                    if response.status == 200:
                        price_data = await response.json()
                        
                        for price_info in price_data.get(best_match, []):
                            if price_info['orderSide'] == 'BUY':
                                buy_price = price_info['price']
                            elif price_info['orderSide'] == 'SELL':
                                sell_price = price_info['price']
                        
                        # Create an embed message with price details
                        embed = discord.Embed(title=item_name_formatted, description=f"Prices for {item_name_formatted}", color=embed_color)
                        embed.set_thumbnail(url=item_image_url)
                        
                        if buy_price is not None:
                            embed.add_field(name="Buy Price", value=self.format_price(buy_price), inline=True)
                        else:
                            embed.add_field(name="Buy Price", value="Not available", inline=True)
                        
                        if sell_price is not None:
                            embed.add_field(name="Sell Price", value=self.format_price(sell_price), inline=True)
                        else:
                            embed.add_field(name="Sell Price", value="Not available", inline=True)
                        
                        embed.set_footer(text=f"{config['name']} • JinglingJester")
                        await interaction.response.send_message(embed=embed)
                    else:
                        await interaction.response.send_message(f"Failed to fetch the price. HTTP Status: {response.status}")
        else:
            await interaction.response.send_message("No matching item found.")

async def setup(bot: commands.Bot):
    """Setup function to add the MarketCog to the bot."""
    await bot.add_cog(MarketCog(bot))
