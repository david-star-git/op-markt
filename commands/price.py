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
import requests
from discord import File

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

    def find_best_match(self, query: str, items_dict: dict) -> tuple[str, str]:
        """
        Find the best matching item from a dictionary of English and German names based on the query string.

        First, it tries to find a substring match, and if multiple matches are found, it uses fuzzy matching to select the best one.
        If no substring matches are found, it falls back to full fuzzy matching.

        Args:
            query (str): Query string to match.
            items_dict (dict): Dictionary where keys are English names and values are German names.

        Returns:
            tuple: The best matching English and German item names.
        """
        query = query.lower()

        # First, perform a substring search on both English and German names
        substring_matches = [(eng_name, ger_name) for eng_name, ger_name in items_dict.items()
                            if query in eng_name.lower() or query in ger_name.lower()]

        # If we have substring matches, use fuzzy matching to sort them
        if substring_matches:
            closest_match_eng = None
            closest_match_ger = None
            lowest_distance = float('inf')

            for eng_name, ger_name in substring_matches:
                distance_eng = self.levenshtein_distance(query, eng_name.lower())
                distance_ger = self.levenshtein_distance(query, ger_name.lower())

                # Prioritize the closest match between English and German
                if distance_eng < lowest_distance:
                    closest_match_eng = eng_name
                    closest_match_ger = ger_name
                    lowest_distance = distance_eng
                if distance_ger < lowest_distance:
                    closest_match_eng = eng_name
                    closest_match_ger = ger_name
                    lowest_distance = distance_ger

            return closest_match_eng, closest_match_ger

        # If no substring matches, fall back to full fuzzy matching
        closest_match_eng = None
        closest_match_ger = None
        lowest_distance = float('inf')

        for eng_name, ger_name in items_dict.items():
            distance_eng = self.levenshtein_distance(query, eng_name.lower())
            distance_ger = self.levenshtein_distance(query, ger_name.lower())

            # Prioritize the closest match between English and German
            if distance_eng < distance_ger:
                if distance_eng < lowest_distance:
                    closest_match_eng = eng_name
                    closest_match_ger = ger_name
                    lowest_distance = distance_eng
            else:
                if distance_ger < lowest_distance:
                    closest_match_eng = eng_name
                    closest_match_ger = ger_name
                    lowest_distance = distance_ger

        return closest_match_eng, closest_match_ger

    def generate_price_history_graph(self, item_name_eng: str, item_name_display: str, prices_dir: str) -> io.BytesIO:
        """
        Generate a graph showing the price history for the given item over the last 14 days.

        Args:
            item_name_eng (str): The English name of the item for looking up prices.
            item_name_display (str): The name of the item (English or German) to display in the graph.
            prices_dir (str): The directory containing the daily price JSON files.

        Returns:
            io.BytesIO: The graph image as a file-like object.
        """
        # Prepare to collect price data
        buy_prices = {}
        sell_prices = {}

        # Get the date for the current day and the date for 14 days ago
        end_date = datetime.now()
        start_date = end_date - timedelta(days=13)  # Adjust to include the last 14 days

        # Loop through the last 14 days and collect prices
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%d-%m-%Y")
            price_file = os.path.join(prices_dir, f"{date_str}.json")

            if os.path.exists(price_file):
                with open(price_file, "r") as f:
                    daily_prices = json.load(f)
                    for category, items in daily_prices.items():
                        if item_name_eng in items:
                            for price_info in items[item_name_eng]:
                                if price_info['orderSide'] == 'BUY':
                                    buy_prices[date_str] = price_info['price']
                                elif price_info['orderSide'] == 'SELL':
                                    sell_prices[date_str] = price_info['price']

            # Move to the next day
            current_date += timedelta(days=1)

        # Create a list of all dates in the range
        dates = [start_date + timedelta(days=i) for i in range(14)]  # Last 14 days
        dates_str = [date.strftime("%d-%m-%Y") for date in dates]

        # Prepare buy and sell values with default 0 if no price data is available
        buy_values = [buy_prices.get(date_str, 0) for date_str in dates_str]
        sell_values = [sell_prices.get(date_str, 0) for date_str in dates_str]

        # Plotting the graph
        plt.figure(figsize=(12, 6))
        plt.plot(dates, buy_values, label='Kaufpreis', color='blue', marker='o', linestyle='-')
        plt.plot(dates, sell_values, label='Verkaufspreis', color='red', marker='o', linestyle='-')
        plt.xlabel('Datum')
        plt.ylabel('Preis')

        # Use the appropriate display name for the title
        formatted_item_name = self.format_item_name(item_name_display)
        plt.title(f'Preisverlauf für {formatted_item_name}', color='white')
        plt.legend()

        # Format x-axis to show all dates in the range
        plt.gca().xaxis.set_major_locator(mdates.DayLocator())
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d-%m-%Y'))
        plt.gca().set_xticks(dates)  # Ensure ticks match all dates
        plt.gcf().autofmt_xdate()  # Automatically format dates on x-axis

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
        """Get the item image URL from the local directory, API, or fallback image."""
        formatted_name = item_name.lower().replace(' ', '_')
        local_image_path = f"data/items/minecraft_{formatted_name}.png"
        fallback_image = "data/imagenotfound.png"
        
        # Check if the image exists locally
        if os.path.exists(local_image_path):
            return local_image_path  # Return the local path for sending as a file

        # Try to get the image from the API if it doesn't exist locally
        url = f"https://img.mc-api.io/{formatted_name}.png"
        try:
            response = requests.get(url)
            if response.status_code == 200 and 'image' in response.headers['Content-Type']:
                return url  # Return the URL for the embed thumbnail
        except requests.RequestException:
            pass  # Fallback if any exception occurs

        # If all fails, return the fallback image
        return fallback_image  # Return fallback local path

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

        # Find the best match from items list (using substring first, then fuzzy if needed)
        best_match_eng, best_match_ger = self.find_best_match(item_name, items)
        
        if best_match_eng:
            # Always use the English name for internal operations like price lookup
            item_name_formatted = self.format_item_name(best_match_eng)

            # Determine the display name based on user query (use German if closer, else English)
            display_name = best_match_ger if item_name.lower() in best_match_ger.lower() else best_match_eng

            item_image_url = self.get_item_image_url(best_match_eng)  # Always use English name for URL lookup

            # Find the price using the English name
            buy_price = None
            sell_price = None
            category_found = None

            for category, category_items in prices.items():
                if best_match_eng in category_items:
                    category_found = category
                    for price_info in category_items[best_match_eng]:
                        if price_info['orderSide'] == 'BUY':
                            buy_price = price_info['price']
                        elif price_info['orderSide'] == 'SELL':
                            sell_price = price_info['price']
                    break

            # Create the embed
            embed = discord.Embed(title=self.format_item_name(display_name), 
                                description=f"**Kategorie**: {category_found or 'NOT_FOUND'}", 
                                color=self.embed_color)

            # Initialize files list for attachments
            files = []

            # Check if the image is local or a URL
            if os.path.exists(item_image_url):
                # If it's a local file, send it as an attachment
                file = File(item_image_url, filename="image.png")
                files.append(file)
                embed.set_thumbnail(url="attachment://image.png")
            else:
                # Use the API image URL directly in the embed
                embed.set_thumbnail(url=item_image_url)

            # Add buy and sell prices
            embed.add_field(name="Kaufpreis", value=self.format_price(buy_price) if buy_price else "Nicht verfügbar", inline=True)
            embed.add_field(name="Verkaufspreis", value=self.format_price(sell_price) if sell_price else "Nicht verfügbar", inline=True)

            # Generate price history graph and add it to the embed
            prices_dir = 'data/prices'
            graph_image = self.generate_price_history_graph(best_match_eng, display_name, prices_dir)
            if graph_image:
                graph_file = File(graph_image, filename='price_history.png')
                files.append(graph_file)
                embed.set_image(url="attachment://price_history.png")
            
            # Set footer and send message
            embed.set_footer(text=f"{self.config['name']} • JinglingJester")
            await interaction.response.send_message(embed=embed, files=files)
        else:
            await interaction.response.send_message("Kein passender Item gefunden.")

async def setup(bot: commands.Bot):
    """Setup function to add the MarketCog to the bot."""
    await bot.add_cog(MarketCog(bot))