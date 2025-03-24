import requests
import logging
import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def fetch_alpha_vantage_news(symbol, limit=3):
    """
    Fetch news for a stock symbol using Alpha Vantage News API.
    
    Args:
        symbol (str): Stock symbol (e.g., AAPL)
        limit (int): Maximum number of articles to return
        
    Returns:
        list: List of news articles with title, url, source, date, and full text
    """
    # Get API key from environment variable
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        logger.error("Alpha Vantage API key not found. Set ALPHA_VANTAGE_API_KEY in your .env file.")
        return []
    
    # Base URL for Alpha Vantage News API
    base_url = "https://www.alphavantage.co/query"
    
    # Parameters for the API request
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": symbol,
        "apikey": api_key,
        "limit": 50  # Request more than we need to filter by relevance
    }
    
    try:
        logger.info(f"Fetching news for {symbol} from Alpha Vantage with API key: {api_key[:4]}...")
        response = requests.get(base_url, params=params)
        
        if response.status_code != 200:
            logger.error(f"Alpha Vantage API returned status code {response.status_code}")
            logger.error(f"Response content: {response.text[:200]}...")
            return []
        
        data = response.json()
        
        if "feed" not in data:
            logger.warning(f"No news feed found in Alpha Vantage response for {symbol}")
            logger.debug(f"Response keys: {data.keys()}")
            if "Note" in data:
                logger.warning(f"Alpha Vantage API note: {data['Note']}")
            return []
        
        # Filter articles by relevance score and get the most relevant ones
        articles = data["feed"]
        logger.info(f"Found {len(articles)} articles in Alpha Vantage feed for {symbol}")
        
        # Sort by relevance score (if available) or by time
        for article in articles:
            # Calculate relevance based on ticker sentiment if available
            relevance = 0
            if "ticker_sentiment" in article:
                for ticker_sent in article["ticker_sentiment"]:
                    if ticker_sent["ticker"] == symbol:
                        # Use relevance_score if available, otherwise use sentiment score
                        relevance = float(ticker_sent.get("relevance_score", ticker_sent.get("ticker_sentiment_score", 0)))
                        break
            article["relevance"] = relevance
        
        # Sort by relevance (higher is better)
        articles.sort(key=lambda x: x["relevance"], reverse=True)
        
        # Get the top articles
        top_articles = articles[:limit]
        
        # Format the results
        news_data = []
        for article in top_articles:
            # Get the full text by making a request to the URL
            full_text = get_article_full_text(article["url"])
            
            # If full text extraction failed, use the summary provided by Alpha Vantage
            if full_text.startswith("Full article text not available") or full_text.startswith("Error retrieving"):
                full_text = article.get("summary", "No summary available")
                logger.info(f"Using Alpha Vantage summary instead of full text for article: {article.get('title', 'Unknown title')}")
            
            # Format the date
            try:
                date_obj = datetime.strptime(article["time_published"], "%Y%m%dT%H%M%S")
                formatted_date = date_obj.isoformat() + "Z"
            except (ValueError, KeyError):
                formatted_date = article.get("time_published", "Unknown date")
            
            news_data.append({
                "title": article.get("title", "No title"),
                "url": article.get("url", "No URL"),
                "source": article.get("source", "Alpha Vantage"),
                "date": formatted_date,
                "full_article_text": full_text
            })
            
            # Add a delay to avoid rate limiting
            time.sleep(1)
        
        logger.info(f"Processed {len(news_data)} articles for {symbol} from Alpha Vantage")
        return news_data
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching news from Alpha Vantage for {symbol}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching news from Alpha Vantage for {symbol}: {e}")
        return []

def get_article_full_text(url):
    """
    Get the full text of an article from its URL using a combination of methods.
    
    Args:
        url (str): URL of the article
        
    Returns:
        str: Full text of the article
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        
        # Add retry logic with exponential backoff
        max_retries = 3
        retry_delay = 2  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=10)
                
                # If we get rate limited, wait and retry
                if response.status_code == 429:
                    if attempt < max_retries - 1:  # Don't sleep on the last attempt
                        sleep_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Rate limited (429). Waiting {sleep_time} seconds before retry {attempt+1}/{max_retries}")
                        time.sleep(sleep_time)
                        continue
                
                response.raise_for_status()  # Raise exception for other error codes
                
                if response.status_code == 200:
                    # Try to use BeautifulSoup for article extraction
                    from bs4 import BeautifulSoup
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Remove script and style elements
                    for script in soup(["script", "style", "nav", "header", "footer"]):
                        script.decompose()
                    
                    # Try to find the article content using common selectors
                    article_selectors = [
                        "article", 
                        ".article-body", 
                        ".article-content",
                        ".story-body",
                        ".story-content",
                        ".post-content",
                        ".entry-content",
                        "main",
                        ".caas-body",
                        "#article-body",
                        ".article__body",
                        ".article-text",
                        ".article__content",
                        ".content-article",
                        ".article"
                    ]
                    
                    for selector in article_selectors:
                        article_content = soup.select_one(selector)
                        if article_content:
                            # Get all paragraphs within the article content
                            paragraphs = article_content.find_all('p')
                            if paragraphs:
                                text = "\n".join(p.get_text().strip() for p in paragraphs)
                                if len(text) > 100:  # Ensure we got meaningful text
                                    logger.info(f"Successfully extracted article text using selector: {selector}")
                                    return text
                    
                    # If no article content found with selectors, get all paragraphs
                    paragraphs = soup.find_all('p')
                    if paragraphs:
                        # Filter out short paragraphs that are likely not part of the main content
                        main_paragraphs = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50]
                        if main_paragraphs:
                            text = "\n".join(main_paragraphs)
                            if len(text) > 100:  # Ensure we got meaningful text
                                logger.info(f"Successfully extracted article text using all paragraphs")
                                return text
                    
                    # Last resort: get all text
                    text = soup.get_text().strip()
                    if len(text) > 200:  # Higher threshold for raw text
                        logger.info(f"Successfully extracted article text using raw text")
                        return text
                    
                    logger.warning(f"Failed to extract meaningful text from {url}")
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    sleep_time = retry_delay * (2 ** attempt)
                    logger.warning(f"Request error: {e}. Waiting {sleep_time} seconds before retry {attempt+1}/{max_retries}")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to retrieve the article after {max_retries} attempts: {e}")
        
        # If we get here, we couldn't extract the text
        logger.error(f"Could not extract article text from {url}")
        
        # For Alpha Vantage, we can use the summary they provide instead of the full text
        return "Full article text not available. Please check the URL directly."
        
    except Exception as e:
        logger.error(f"Error getting full text from {url}: {e}")
        return "Error retrieving full text" 