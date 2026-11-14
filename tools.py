import os, json, re, requests
from urllib.parse import parse_qs, urlparse

def get_stock_price(ticker: str):
    """
    Get the current stock price for a given ticker symbol using Yahoo Finance (no API key needed).

    Args:
        ticker (str): The stock ticker symbol (e.g. "AAPL").
    Returns:
        float: The current stock price, or a dict with an "error" key on failure.
    """
    try:
        r = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}",
            params={"range": "1d", "interval": "1d"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        r.raise_for_status()
        results = r.json()["chart"]["result"]
        if not results:
            return {"error": f"No price found for ticker '{ticker}'."}
        price = results[0]["meta"]["regularMarketPrice"]
        return float(price)
    except requests.exceptions.Timeout:
        return {"error": "Stock price request timed out."}
    except requests.exceptions.HTTPError as e:
        return {"error": f"Stock API returned an error: {e}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error fetching stock price: {e}"}
    except (KeyError, IndexError, TypeError, ValueError) as e:
        return {"error": f"Unexpected stock API response: {e}"}

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

def get_youtube_transcript(video_url: str, language: str = "en"):
    """
    Fetch the transcript for a YouTube video URL or video ID.

    Args:
        video_url (str): A YouTube video URL or 11-character video ID.
        language (str): Preferred transcript language code (defaults to English).
    Returns:
        str: The transcript text, or a dict with an "error" key on failure.
    """
    value = video_url.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        video_id = value
    else:
        parsed = urlparse(value if "://" in value else f"//{value}")
        hostname = (parsed.hostname or "").lower()
        if hostname == "youtu.be":
            video_id = parsed.path.strip("/").split("/")[0]
        elif (
            hostname == "youtube.com"
            or hostname.endswith(".youtube.com")
            or hostname == "youtube-nocookie.com"
            or hostname.endswith(".youtube-nocookie.com")
        ):
            query_id = parse_qs(parsed.query).get("v", [""])[0]
            path_parts = parsed.path.strip("/").split("/")
            video_id = query_id or (
                path_parts[1]
                if len(path_parts) > 1 and path_parts[0] in {"embed", "shorts", "live"}
                else ""
            )
        else:
            video_id = ""

    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        return {"error": "Provide a valid YouTube video URL or 11-character video ID."}
    if not language.strip():
        return {"error": "The transcript language must not be empty."}

    try:
        from youtube_transcript_api import (
            YouTubeTranscriptApi,
            YouTubeTranscriptApiException,
        )
    except ImportError:
        return {"error": "Install the dependency with: pip install youtube-transcript-api"}

    try:
        transcript = YouTubeTranscriptApi().fetch(
            video_id,
            languages=[language.strip()],
        )
        return "\n".join(snippet.text for snippet in transcript)
    except YouTubeTranscriptApiException as e:
        return {"error": f"Could not retrieve YouTube transcript: {e}"}

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
        "name": "get_youtube_transcript",
        "description": "Fetch the transcript for a YouTube video URL or video ID. Use the transcript to answer questions or summarize the video.",
        "input_schema": {
            "type": "object",
            "properties": {
                "video_url": {
                    "type": "string",
                    "description": "A YouTube video URL or 11-character video ID.",
                },
                "language": {
                    "type": "string",
                    "description": "Preferred transcript language code, such as 'en'. Defaults to English.",
                },
            },
            "required": ["video_url"],
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
