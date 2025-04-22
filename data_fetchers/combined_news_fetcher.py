import logging
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

# Import all existing fetchers
from data_fetchers.fetch_us_news_data import fetch_us_news
from data_fetchers.fetch_european_news import fetch_european_news
from data_fetchers.fetch_nordic_news import fetch_nordic_news
from data_fetchers.fetch_baltic_news import fetch_baltic_news
from utils.file_operations import ensure_directory, save_json

logger = logging.getLogger(__name__)

def fetch_all_news_for_symbol(symbol, exchange="US"):
    """Fetch news from all sources for a given stock symbol based on exchange."""
    logger.info(f"Fetching news for {symbol} on {exchange} from all sources")
    
    articles = []
    
    # Determine which fetchers to use based on exchange
    if exchange.upper() in ["US", "NYSE", "NASDAQ", "AMEX"]:
        logger.info(f"Fetching US news for {symbol}")
        us_articles = fetch_us_news(symbol)
        articles.extend(us_articles)
    
    elif exchange.upper() in ["EU", "EURONEXT", "XETRA", "LSE"]:
        logger.info(f"Fetching European news for {symbol}")
        eu_articles = fetch_european_news(symbol)
        articles.extend(eu_articles)
    
    elif exchange.upper() in ["NORDIC", "OMXH", "OMXS", "OMXC"]:
        logger.info(f"Fetching Nordic news for {symbol}")
        nordic_articles = fetch_nordic_news(symbol)
        articles.extend(nordic_articles)
    
    elif exchange.upper() in ["BALTIC", "OMXT", "OMXR", "OMXV"]:
        logger.info(f"Fetching Baltic news for {symbol}")
        baltic_articles = fetch_baltic_news(symbol)
        articles.extend(baltic_articles)
    
    else:
        # Default to US news if exchange is unknown
        logger.warning(f"Unknown exchange {exchange}, defaulting to US news")
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