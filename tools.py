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
    }
]