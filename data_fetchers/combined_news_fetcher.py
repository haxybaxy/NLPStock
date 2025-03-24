import logging
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import all existing fetchers with correct function names
from .fetch_us_news_data import fetch_us_news
from .fetch_european_news import fetch_european_news
# Fix the imports for Nordic and Baltic news
from .fetch_nordic_news import fetch_news_for_company as fetch_nordic_news
from .fetch_baltic_news import fetch_news_for_company as fetch_baltic_news
from ..utils.file_operations import ensure_directory, save_json
from .fetch_alpha_vantage_news import fetch_alpha_vantage_news

logger = logging.getLogger(__name__)

def fetch_all_news_for_symbol(symbol, exchange="US"):
    """Fetch news from all sources for a given stock symbol based on exchange."""
    logger.info(f"Fetching news for {symbol} on {exchange} from all sources")
    
    articles = []
    
    # Determine which fetchers to use based on exchange
    if exchange.upper() in ["US", "NYSE", "NASDAQ", "AMEX"]:
        logger.info(f"Fetching US news for {symbol}")
        
        # Try Alpha Vantage first as it's more reliable
        logger.info(f"Trying Alpha Vantage for {symbol}")
        alpha_articles = fetch_alpha_vantage_news(symbol)
        
        if alpha_articles:
            logger.info(f"Found {len(alpha_articles)} articles from Alpha Vantage for {symbol}")
            articles.extend(alpha_articles)
        else:
            # Fall back to other sources if Alpha Vantage fails
            logger.info(f"No articles found from Alpha Vantage for {symbol}, trying MarketBeat")
            us_articles = fetch_us_news(symbol)
            articles.extend(us_articles)
    
    elif exchange.upper() in ["EU", "EURONEXT", "XETRA", "LSE"]:
        logger.info(f"Fetching European news for {symbol}")
        eu_articles = fetch_european_news(symbol)
        articles.extend(eu_articles)
    
    elif exchange.upper() in ["NORDIC", "OMXH", "OMXS", "OMXC"]:
        logger.info(f"Fetching Nordic news for {symbol}")
        # For Nordic news, we need to provide both symbol and gcfIssuerId
        # You'll need to implement a mapping or lookup for gcfIssuerId
        gcfIssuerId = get_gcf_issuer_id(symbol)  # You need to implement this function
        if gcfIssuerId:
            nordic_articles = fetch_nordic_news(symbol, gcfIssuerId)
            articles.extend(nordic_articles)
        else:
            logger.warning(f"No gcfIssuerId found for Nordic symbol {symbol}")
    
    elif exchange.upper() in ["BALTIC", "OMXT", "OMXR", "OMXV"]:
        logger.info(f"Fetching Baltic news for {symbol}")
        # For Baltic news, we need to provide both symbol and gcfIssuerId
        # You'll need to implement a mapping or lookup for gcfIssuerId
        gcfIssuerId = get_gcf_issuer_id(symbol)  # You need to implement this function
        if gcfIssuerId:
            baltic_articles = fetch_baltic_news(symbol, gcfIssuerId)
            articles.extend(baltic_articles)
        else:
            logger.warning(f"No gcfIssuerId found for Baltic symbol {symbol}")
    
    else:
        # Default to US news if exchange is unknown
        logger.warning(f"Unknown exchange {exchange}, defaulting to US news")
        alpha_articles = fetch_alpha_vantage_news(symbol)
        if alpha_articles:
            articles.extend(alpha_articles)
        else:
            us_articles = fetch_us_news(symbol)
            articles.extend(us_articles)
    
    # Save the articles to a local file
    if articles:
        output_dir = ensure_directory("STOCK_DB/news")
        output_file = Path(output_dir) / f"{symbol}_news.json"
        save_json(articles, output_file)
        logger.info(f"Saved {len(articles)} news articles for {symbol} to {output_file}")
    else:
        logger.warning(f"No news articles found for {symbol}")
    
    return articles

# Helper function to get gcfIssuerId for Nordic and Baltic exchanges
def get_gcf_issuer_id(symbol):
    """
    Get the gcfIssuerId for a given symbol.
    You'll need to implement this with your own mapping logic.
    """
    # This is a placeholder - replace with your actual mapping
    symbol_to_issuer_id = {
        # Add your mappings here, for example:
        # "NOKIA": "12345",
        # "ERICSSON": "67890",
    }
    
    return symbol_to_issuer_id.get(symbol)

def fetch_news_for_symbols(symbols, exchanges=None, delay=2):
    """Fetch news for multiple stock symbols with a delay between requests."""
    results = {}
    
    if exchanges is None:
        # Default all exchanges to US
        exchanges = ["US"] * len(symbols)
    elif len(exchanges) != len(symbols):
        # If exchanges list is provided but length doesn't match symbols
        logger.warning("Number of exchanges doesn't match number of symbols, defaulting all to US")
        exchanges = ["US"] * len(symbols)
    
    for i, symbol in enumerate(symbols):
        exchange = exchanges[i]
        logger.info(f"Processing symbol: {symbol} on {exchange}")
        
        articles = fetch_all_news_for_symbol(symbol, exchange)
        results[symbol] = articles
        
        # Add a delay to avoid rate limiting
        if delay > 0 and i < len(symbols) - 1:  # No delay after the last symbol
            logger.debug(f"Waiting {delay} seconds before next request")
            time.sleep(delay)
    
    return results

def fetch_news_from_file(symbols_file, exchanges_file=None, delay=2):
    """Fetch news for symbols listed in a file."""
    try:
        # Read symbols from file
        with open(symbols_file, 'r') as f:
            symbols = [line.strip() for line in f if line.strip()]
        
        # Read exchanges from file if provided
        exchanges = None
        if exchanges_file:
            try:
                with open(exchanges_file, 'r') as f:
                    exchanges = [line.strip() for line in f if line.strip()]
            except Exception as e:
                logger.error(f"Error reading exchanges file: {e}")
        
        logger.info(f"Fetching news for {len(symbols)} symbols from file")
        return fetch_news_for_symbols(symbols, exchanges, delay)
    
    except Exception as e:
        logger.error(f"Error reading symbols file: {e}")
        return {} 