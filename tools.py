import os, json, requests

def get_stock_price(ticker):
    """
    Get the current stock price for a given ticker symbol.

    Args:
        ticker (str): The stock ticker symbol.
    Returns:
        float: The current stock price.
    """
    # Placeholder implementation - replace with actual stock price fetching logic
    return 100.0

# youtube search tool; needs google api to be implemented.
def dummy_youtube_search(query):
    """
    Search for YouTube videos based on a query.

    Args:
        query (str): The search query.
    Returns:
        list: A list of dictionaries containing video titles and URLs.
    """
    # Placeholder implementation - replace with actual YouTube search logic
    return [
        {"title": "Video 1", "url": "https://www.youtube.com/watch?v=video1"},
        {"title": "Video 2", "url": "https://www.youtube.com/watch?v=video2"},
    ]

def search_youtube(query: str, max_results: int = 5, YT_KEY: str = os.getenv("YOUTUBE_API_KEY")):
    """
    Search for YouTube videos based on a query using the YouTube Data API.

    Args:
        query (str): The search query.
        max_results (int): The maximum number of results to return.
        YT_KEY (str): The YouTube Data API key.
    Returns:
        list: A list of dictionaries containing video titles, channels, and URLs.
    """
    if not YT_KEY:
        return {"error": "YOUTUBE_API_KEY is not set."}

    try:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={"part": "snippet", "q": query, "type": "video",
                    "maxResults": max_results, "key": YT_KEY},
            timeout=10,
        )
        r.raise_for_status()
        return [
            {
                "title": i["snippet"]["title"],
                "channel": i["snippet"]["channelTitle"],
                "url": f"https://www.youtube.com/watch?v={i['id']['videoId']}",
            }
            for i in r.json().get("items", [])
        ]
    except requests.exceptions.Timeout:
        return {"error": "YouTube search timed out."}
    except requests.exceptions.HTTPError as e:
        return {"error": f"YouTube API returned an error: {e}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error during YouTube search: {e}"}
    except (KeyError, ValueError) as e:
        return {"error": f"Unexpected YouTube API response: {e}"}

def send_telegram_message(text: str, chat_id: str = os.getenv("TELEGRAM_CHAT_ID"), bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN")):
    """
    Send a message to a Telegram chat via the Telegram Bot API.

    Args:
        text (str): The message text to send.
        chat_id (str): The target chat ID (defaults to TELEGRAM_CHAT_ID).
        bot_token (str): The Telegram bot token (defaults to TELEGRAM_BOT_TOKEN).
    Returns:
        dict: The Telegram API response, or a dict with an "error" key on failure.
    """
    if not bot_token:
        return {"error": "TELEGRAM_BOT_TOKEN is not set."}
    if not chat_id:
        return {"error": "TELEGRAM_CHAT_ID is not set."}

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            return {"error": f"Telegram API error: {data.get('description')}"}
        return {"ok": True, "message_id": data["result"]["message_id"]}
    except requests.exceptions.Timeout:
        return {"error": "Telegram request timed out."}
    except requests.exceptions.HTTPError as e:
        return {"error": f"Telegram API returned an error: {e}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error sending Telegram message: {e}"}
    except (KeyError, ValueError) as e:
        return {"error": f"Unexpected Telegram API response: {e}"}

tools = [
    {
        "name": "get_stock_price",
        "description": "Get the current stock price for a given ticker symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol.",
                }
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "dummy_youtube_search",
        "description": "Search for YouTube videos based on a query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_youtube",
        "description": "Search for YouTube videos based on a query using the YouTube Data API.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "The maximum number of results to return.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "send_telegram_message",
        "description": "Send a message to a Telegram chat via the Telegram Bot API.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The message text to send.",
                }
            },
            "required": ["text"],
        },
    },

]
