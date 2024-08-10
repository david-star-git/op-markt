import discord
import aiohttp
import json
import os
import time
import base64
from discord import app_commands
from discord.ext import commands

current_file_path = __file__
current_file_name = os.path.basename(current_file_path)

try:
    with open('data/config.json') as file:
        config = json.load(file)
        print(f"Successfully loaded config.json in {current_file_name}")
except FileNotFoundError:
    print(f"File not found in {current_file_name}.")
except json.JSONDecodeError:
    print(f"Invalid JSON format in {current_file_name}")

embed_color = int(config['embed_hex'], 16)

class MarketCog(commands.Cog):
    def __init__(self, bot):
        """
        Initialize the MarketCog with bot instance and set up API configurations.
        
        Args:
            bot (commands.Bot): The bot instance to which this cog is attached.
        """
        self.bot = bot
        self.api_url = "https://api.opsucht.net/market"
        self.items_file = "data/items.json"
        self.prices_file = "data/prices.json"
        self.config_file = "data/config.json"
        self.load_api_credentials()
        self.load_last_refresh_time()
        self.update_interval = int(config.get("update_interval", 3600))

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

    def load_last_refresh_time(self):
        """
        Load the last refresh time from the configuration file.
        
        If the file or JSON is not valid, initializes last refresh time to 0.
        """
        try:
            with open(self.config_file, "r") as f:
                config = json.load(f)
                self.last_refresh = config.get("last_refresh", 0)
                print(f"Loaded last refresh time: {self.last_refresh}")
        except FileNotFoundError:
            self.last_refresh = 0
            print("Config file not found. Initializing last refresh time to 0.")
        except json.JSONDecodeError:
            self.last_refresh = 0
            print("Invalid JSON format in config file. Initializing last refresh time to 0.")

    def save_last_refresh_time(self):
        """
        Save the last refresh time to the configuration file.
        
        Creates or updates the config file to store the latest refresh time.
        """
        try:
            with open(self.config_file, "r+") as f:
                config = json.load(f)
                config["last_refresh"] = self.last_refresh
                f.seek(0)
                json.dump(config, f, indent=4)
                f.truncate()
        except FileNotFoundError:
            with open(self.config_file, "w") as f:
                json.dump({"last_refresh": self.last_refresh}, f, indent=4)
        except json.JSONDecodeError:
            with open(self.config_file, "w") as f:
                json.dump({"last_refresh": self.last_refresh}, f, indent=4)

    async def refresh_data(self):
        """
        Refresh item and price data from the API if the file is outdated or missing.
        
        Data is refreshed if the last refresh time is older than 60 minutes or if files do not exist.
        """
        if not os.path.exists(self.prices_file) or time.time() - self.last_refresh > self.update_interval:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/items", headers=self.get_headers()) as items_response:
                    async with session.get(f"{self.api_url}/prices", headers=self.get_headers()) as prices_response:
                        if items_response.status == 200 and prices_response.status == 200:
                            items = await items_response.json()
                            prices = await prices_response.json()
                            os.makedirs(os.path.dirname(self.items_file), exist_ok=True)
                            
                            with open(self.items_file, "w") as f:
                                json.dump(items, f)
                            
                            with open(self.prices_file, "w") as f:
                                json.dump(prices, f)
                            
                            self.last_refresh = time.time()
                            self.save_last_refresh_time()
                            print("Refreshed data/items.json and data/prices.json")
                        else:
                            print(f"Failed to refresh data: items status {items_response.status}, prices status {prices_response.status}")

    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        Calculate the Levenshtein distance between two strings.
        
        Args:
            s1 (str): First string.
            s2 (str): Second string.
        
        Returns:
            int: The Levenshtein distance between the two strings.
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
        """Format item names for display, capitalizing each word."""
        return ' '.join(word.capitalize() for word in item_name.replace('_', ' ').split())

    def get_item_image_url(self, item_name: str) -> str:
        """Generate the URL for the item image."""
        formatted_name = item_name.lower().replace(' ', '_')
        return f"https://mc.nerothe.com/img/1.21/minecraft_{formatted_name}.png"

    def format_price(self, price: float) -> str:
        """Format a price with thousand separators and currency symbol."""
        rounded_price = round(price, 1)
        formatted_price = f"{rounded_price:,.1f}".replace(',', ' ').replace('.', ',').replace(' ', '.')
        return formatted_price + " $"

    @app_commands.command(name="price", description="Get the price for an item")
    async def fetch_price(self, interaction: discord.Interaction, item_name: str):
        """
        Command to fetch and display the price for an item.
        
        Args:
            interaction (discord.Interaction): The interaction object for the command.
            item_name (str): The name of the item to fetch the price for.
        """
        await self.refresh_data()
        
        # Load items and prices data
        with open(self.items_file, "r") as f:
            items = json.load(f)
        with open(self.prices_file, "r") as f:
            prices = json.load(f)

        # Find the best match from items list
        best_match = self.find_best_match(item_name, items)
        if best_match:
            item_name_formatted = self.format_item_name(best_match)
            item_image_url = self.get_item_image_url(best_match)
            buy_price = None
            sell_price = None
            category_found = None

            # Find prices in the prices data
            for category, category_items in prices.items():
                if best_match in category_items:
                    category_found = category
                    for price_info in category_items[best_match]:
                        if price_info['orderSide'] == 'BUY':
                            buy_price = price_info['price']
                        elif price_info['orderSide'] == 'SELL':
                            sell_price = price_info['price']
                    break  # Exit loop once the item is found
            
            if category_found:
                embed = discord.Embed(title=item_name_formatted, description=f"**Category**: {category_found}", color=embed_color)
            else:
                embed = discord.Embed(title=item_name_formatted, description=f"**Category**: NOT_FOUND", color=embed_color)
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
            await interaction.response.send_message("No matching item found.")

async def setup(bot: commands.Bot):
    """Setup function to add the MarketCog to the bot."""
    await bot.add_cog(MarketCog(bot))
