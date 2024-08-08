# OP-Markt Bot Documentation

## Overview

The OP-Markt Bot is a versatile tool designed to enhance the Minecraft experience for the Opsucht community. This bot interacts with the server's market API to provide item prices, supports fuzzy matching to identify Minecraft items, and formats responses to be user-friendly.

## Features

- **Price Retrieval**: Fetches and displays item prices from the Opsucht server’s market.
- **Fuzzy Matching**: Utilizes a sophisticated algorithm to find the closest matching items based on user input.
- **Embed Responses**: Provides formatted and visually appealing responses, including item images and price details.

## Getting Started

### Prerequisites

- Python 3.12 or higher
- Discord.py library (`discord.py` version 2.0 or later)
- `aiohttp` for asynchronous HTTP requests
- JSON files for configuration and item data

### Installation

#### Clone the Repository

1. Clone the repository: `https://github.com/david-star-git/op-markt.git`
2. Change directory: `cd op-markt`

#### Create and Activate a Virtual Environment

1. Create a virtual environment: `python -m venv venv`
2. Activate the virtual environment:
   - On Unix or MacOS: `source venv/bin/activate`
   - On Windows: `venv\Scripts\activate`

#### Install Dependencies

Install the required dependencies: `pip install discord.py aiohttp`

#### Configure API Credentials

1. Create a file named `api.json` in the root directory with your API credentials.

```json
{
    "TOKEN": "DISCORD BOT TOKEN",
    "API-KEY": "OPSCHT API KEY",
    "API-UNAME": "OPSUCHT API USERNAME"
}
```

#### Create a Configuration File

1. Create a file named `data/config.json` with your configuration details.

```json
{
    "name": "OP-Markt",         <- bot username
    "activity": "the market.",  <- bot activity
    "embed_hex": "0x60aefa",    <- embed color
    "last_refresh": 0           <- timestamp of the last data refresh
}
```

### Running the Bot

1. Start the bot: `python bot.py`

## Commands

### `/price <item_name>`

Fetches the price for a specified item. The bot returns both the buy and sell prices, along with an image of the item.

**Example Usage:**

- Command: `/price diamond`

**Response:**

The bot will provide an embed message with:
- Item Name
- Buy Price
- Sell Price
- Item Image

## Fuzzy Matching Algorithm

### Overview

The fuzzy matching algorithm in this bot is designed to handle imperfect user input and still find the most relevant Minecraft item. The algorithm incorporates Levenshtein distance and length-based prioritization to ensure accurate and useful results.

Levenshtein distance was chosen for fuzzy matching in this bot due to its effectiveness in handling small differences between strings. Here are the key reasons:

1. **Error Tolerance**: Levenshtein distance measures how many single-character edits (insertions, deletions, substitutions) are required to transform one string into another. This makes it particularly useful for dealing with common typographical errors or slight misspellings.

2. **Simplicity**: The algorithm is relatively straightforward to implement and understand, making it suitable for the bot's needs without requiring complex setup or computation.

3. **Versatility**: It can be used in various contexts beyond just matching item names, allowing for flexible application in different scenarios where string similarity is important.

4. **Adaptability**: It effectively balances between exact matches and approximate matches, ensuring that users receive relevant results even if their input is not perfectly accurate.

While other algorithms like Jaccard similarity or cosine similarity could also be used for fuzzy matching, Levenshtein distance is favored here due to its direct measurement of edit distance and ease of use for our specific requirements.

### How It Works

- **Levenshtein Distance Calculation**: The algorithm computes the Levenshtein distance between the user’s query and each item name. This distance measures how many single-character edits (insertions, deletions, substitutions) are needed to transform one string into another.

- **Prioritization Logic**:
  - **Substring Matches**: Initially, it looks for items that contain the user’s query as a substring.
  - **Levenshtein Distance**: For substring matches, it calculates the distance and selects the closest match.

- **Handling Special Cases**:
  - If there are no substring matches, the algorithm falls back to a general fuzzy match using Levenshtein distance.
  - Specificity is prioritized when lengths and distances are close.

## Data Refresh

The bot refreshes its data every 60 minutes to ensure that it provides up-to-date information. The timestamp of the last refresh is stored in `data/config.json` under `"last_refresh"`. This approach is designed to avoid excessive API calls and reduce server resource usage, enhancing efficiency. By keeping track of when the last refresh occurred, the bot ensures that it only refreshes data when necessary, thereby minimizing the load on the server and conserving resources. If the bot is restarted, it will remember when the last refresh took place and continue operating efficiently.

## Formatting Prices

The bot formats prices to be user-friendly and consistent. Prices are displayed with thousand separators and one decimal point. For instance, `1000.00` is formatted as `1.000,0 $`.

### Price Formatting Function

The function:
- Rounds prices to one decimal point.
- Formats with thousand separators.
- Appends a currency symbol.

## Embeds and Images

The bot includes item images and formatted responses in Discord embeds. Images are sourced from a specific URL pattern.

### Image URL Format

For an item like `diamond`, the image URL is:

`https://mc.nerothe.com/img/1.21/minecraft_diamond.png`

**Embedded Responses:**

- The embed title is the item name.
- The description includes price information.
- The thumbnail is the item’s image.

## Contributing

If you’d like to contribute to this project, please fork the repository and submit a pull request with your changes. Ensure to follow the coding standards and provide documentation for new features.

## License

This project is licensed under the GNU General Public License. See the [LICENSE](LICENSE) file for details.
