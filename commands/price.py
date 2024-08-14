import discord
import aiohttp
import json
import os
import time
import base64
from discord import app_commands
from discord.ext import commands
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
from datetime import datetime, timedelta
import pandas as pd
import io
from datetime import datetime as dt

# Retrieve the current file path and name
current_file_path = __file__
current_file_name = os.path.basename(current_file_path)

# Load configuration from 'data/config.json'
current_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
try:
    with open('data/config.json') as file:
        config = json.load(file)
        print(f"[{current_time}] Successfully loaded config.json in {current_file_name}")
except FileNotFoundError:
    print(f"[{current_time}] File not found in {current_file_name}.")
except json.JSONDecodeError:
    print(f"[{current_time}] Invalid JSON format in {current_file_name}")

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

        # Load the config file and set embed color
        with open(self.config_file, "r") as f:
            self.config = json.load(f)
        self.embed_color = int(self.config['embed_hex'], 16)

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

    def generate_price_history_graph(self, item_name: str, prices_dir: str) -> io.BytesIO:
        """
        Generate a graph showing the price history for the given item over the past 30 days.
        
        Args:
            item_name (str): The name of the item to generate the price history for.
            prices_dir (str): The directory containing the daily price JSON files.
            
        Returns:
            io.BytesIO: The graph image as a file-like object.
        """
        # Prepare to collect price data
        buy_prices = {}
        sell_prices = {}
        dates = []
        buy_values = []
        sell_values = []

        # Get the date for the current day and the date for 30 days ago
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        # Loop through the past 30 days and collect prices
        current_date = end_date
        while current_date >= start_date:
            date_str = current_date.strftime("%d-%m-%Y")
            price_file = os.path.join(prices_dir, f"{date_str}.json")

            if os.path.exists(price_file):
                with open(price_file, "r") as f:
                    daily_prices = json.load(f)
                    for category, items in daily_prices.items():
                        if item_name in items:
                            for price_info in items[item_name]:
                                if price_info['orderSide'] == 'BUY':
                                    buy_prices[date_str] = price_info['price']
                                elif price_info['orderSide'] == 'SELL':
                                    sell_prices[date_str] = price_info['price']
            
            # Move to the previous day
            current_date -= timedelta(days=1)
        
        # Create buy and sell value lists, adding only dates where at least one price exists
        for date in sorted(set(list(buy_prices.keys()) + list(sell_prices.keys()))):
            dates.append(date)
            buy_values.append(buy_prices.get(date, 0))
            sell_values.append(sell_prices.get(date, 0))

        # Plotting the graph
        plt.figure(figsize=(10, 6))
        plt.plot(dates, buy_values, label='Kaufpreis', color='blue', marker='o')
        plt.plot(dates, sell_values, label='Verkaufspreis', color='red', marker='o')
        plt.xlabel('Datum')
        plt.ylabel('Preis')
        
        # Format item name for the title
        formatted_item_name = self.format_item_name(item_name)
        plt.title(f'Preisverlauf für {formatted_item_name}', color='white')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Format y-axis labels
        def format_func(value, tick_number):
            if value >= 1_000_000:
                return f'{value/1_000_000:.0f}M'
            elif value >= 1_000:
                return f'{value/1_000:.0f}K'
            else:
                return f'{value:.0f}'

        plt.gca().yaxis.set_major_formatter(ticker.FuncFormatter(format_func))

        # Set the background color to be transparent
        plt.gcf().patch.set_facecolor('none')
        plt.gca().set_facecolor('none')
        plt.gca().spines['top'].set_visible(False)
        plt.gca().spines['right'].set_visible(False)
        plt.gca().spines['left'].set_color('white')
        plt.gca().spines['bottom'].set_color('white')
        plt.gca().yaxis.label.set_color('white')
        plt.gca().xaxis.label.set_color('white')
        plt.gca().tick_params(axis='both', colors='white')
        plt.grid(True, linestyle='--', alpha=0.5, color='white')

        # Save the plot to a BytesIO object
        image_stream = io.BytesIO()
        plt.savefig(image_stream, format='png', bbox_inches='tight', transparent=True)
        image_stream.seek(0)
        plt.close()

        return image_stream

    def format_item_name(self, item_name: str) -> str:
        """Format item names for display, capitalizing each word."""
        return ' '.join(word.capitalize() for word in item_name.split('_'))

    def get_item_image_url(self, item_name: str) -> str:
        """Generate the URL for the item image."""
        formatted_name = item_name.lower().replace(' ', '_')
        return f"https://mc.nerothe.com/img/1.21/minecraft_{formatted_name}.png"

    def format_price(self, price: int) -> str:
        """Format price with thousand separators."""
        return f"{price:,}".replace(",", ".") + " Coins"

    async def get_price(self, item_name: str) -> dict[str, int]:
        """
        Get the buy and sell prices for a specific item from the local 'prices.json' file.
        
        Args:
            item_name (str): The item name to search for prices.
        
        Returns:
            dict[str, int]: A dictionary containing buy and sell prices.
        """
        try:
            with open(self.prices_file, "r") as f:
                prices_data = json.load(f)
            for category, items in prices_data.items():
                if item_name in items:
                    return items[item_name]
        except FileNotFoundError:
            return {"buy": 0, "sell": 0}

    @app_commands.command(name="price", description="Get the price for an item")
    async def fetch_price(self, interaction: discord.Interaction, item_name: str):
        """
        Command to fetch and display the price for an item.
        
        Args:
            interaction (discord.Interaction): The interaction object for the command.
            item_name (str): The name of the item to fetch the price for.
        """
        
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
                embed = discord.Embed(title=item_name_formatted, description=f"**Kategorie**: {category_found}", color=self.embed_color)
            else:
                embed = discord.Embed(title=item_name_formatted, description=f"**Kategorie**: NOT_FOUND", color=self.embed_color)
            
            embed.set_thumbnail(url=item_image_url)

            if buy_price is not None:
                embed.add_field(name="Kaufpreis", value=self.format_price(buy_price), inline=True)
            else:
                embed.add_field(name="Kaufpreis", value="Nicht verfügbar", inline=True)

            if sell_price is not None:
                embed.add_field(name="Verkaufspreis", value=self.format_price(sell_price), inline=True)
            else:
                embed.add_field(name="Verkaufspreis", value="Nicht verfügbar", inline=True)

            # Generate price history graph and add it to the embed
            prices_dir = 'data/prices'
            graph_image = self.generate_price_history_graph(best_match, prices_dir)
            file = discord.File(fp=graph_image, filename='price_history.png')
            embed.set_image(url="attachment://price_history.png")
            
            embed.set_footer(text=f"{config['name']} • JinglingJester")

            await interaction.response.send_message(embed=embed, file=file)
        else:
            await interaction.response.send_message("Kein passender Item gefunden.")

async def setup(bot: commands.Bot):
    """Setup function to add the MarketCog to the bot."""
    await bot.add_cog(MarketCog(bot))
