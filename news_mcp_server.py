import os

import requests
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("News Search")


@mcp.tool()
def search_news(query: str, max_results: int = 5) -> list[dict]:
    """Search recent news articles by keyword."""
    api_key = os.getenv("GNEWS_API_KEY")
    if not api_key:
        return [{"error": "GNEWS_API_KEY is not set."}]

    max_results = max(1, min(max_results, 10))
    try:
        response = requests.get(
            "https://gnews.io/api/v4/search",
            params={"q": query, "max": max_results, "apikey": api_key},
            timeout=10,
        )
        response.raise_for_status()
        articles = response.json().get("articles", [])
        return [
            {
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "source": article.get("source", {}).get("name", ""),
                "url": article.get("url", ""),
                "published_at": article.get("publishedAt", ""),
            }
            for article in articles
        ]
    except requests.exceptions.Timeout:
        return [{"error": "News request timed out."}]
    except requests.exceptions.HTTPError as error:
        return [{"error": f"News API returned an HTTP error: {error}"}]
    except requests.exceptions.RequestException as error:
        return [{"error": f"Network error searching news: {error}"}]
    except (KeyError, TypeError, ValueError) as error:
        return [{"error": f"Unexpected news API response: {error}"}]


@mcp.tool()
def get_headlines(category: str = "general", country: str = "us") -> list[dict]:
    """Get top headlines for a category and country."""
    api_key = os.getenv("GNEWS_API_KEY")
    if not api_key:
        return [{"error": "GNEWS_API_KEY is not set."}]

    allowed_categories = {
        "general", "world", "nation", "business", "technology",
        "entertainment", "sports", "science", "health",
    }
    category = category.lower().strip()
    if category not in allowed_categories:
        return [{"error": f"Unsupported category '{category}'."}]

    try:
        response = requests.get(
            "https://gnews.io/api/v4/top-headlines",
            params={
                "category": category,
                "country": country.lower().strip() or "us",
                "max": 10,
                "apikey": api_key,
            },
            timeout=10,
        )
        response.raise_for_status()
        articles = response.json().get("articles", [])
        return [
            {
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "source": article.get("source", {}).get("name", ""),
                "url": article.get("url", ""),
                "published_at": article.get("publishedAt", ""),
            }
            for article in articles
        ]
    except requests.exceptions.Timeout:
        return [{"error": "News request timed out."}]
    except requests.exceptions.HTTPError as error:
        return [{"error": f"News API returned an HTTP error: {error}"}]
    except requests.exceptions.RequestException as error:
        return [{"error": f"Network error fetching headlines: {error}"}]
    except (KeyError, TypeError, ValueError) as error:
        return [{"error": f"Unexpected news API response: {error}"}]


if __name__ == "__main__":
    mcp.run(transport="stdio")
