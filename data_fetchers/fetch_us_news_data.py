from bs4 import BeautifulSoup
from datetime import datetime
import requests
import logging

logger = logging.getLogger(__name__)

def fetch_us_news(symbol):
    """Fetch news for US stocks from MarketBeat with improved error handling."""
    # Try both NASDAQ and NYSE URLs
    exchanges = ["NASDAQ", "NYSE"]
    news_data = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    
    for exchange in exchanges:
        url = f"https://www.marketbeat.com/stocks/{exchange}/{symbol}/"
        logger.info(f"Trying to fetch news from {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise exception for 4XX/5XX status codes
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Try different possible selectors for the news section
            news_section = None
            possible_selectors = [
                "div.fade-bottom",
                "div.news-feed",
                "div.news-articles",
                "section.company-news"
            ]
            
            for selector in possible_selectors:
                news_section = soup.select_one(selector)
                if news_section:
                    logger.info(f"Found news section using selector: {selector}")
                    break
            
            if not news_section:
                logger.warning(f"No news section found for {symbol} on {exchange}")
                continue  # Try next exchange
            
            # Try different possible selectors for articles
            articles = []
            article_selectors = [
                "div.mt-1.bg-white.light-shadow.d-flex",
                "div.news-item",
                "article",
                "div.article-item"
            ]
            
            for selector in article_selectors:
                articles = news_section.select(selector)
                if articles:
                    logger.info(f"Found articles using selector: {selector}")
                    break
            
            if not articles:
                logger.warning(f"No articles found for {symbol} on {exchange}")
                continue  # Try next exchange
            
            count = 0
            for article in articles:
                if count >= 3:
                    break
                
                # Try different selectors for title
                title_element = None
                title_selectors = ["a.d-block.mb-1", "a.headline", "h3 a", "h4 a", "a.title"]
                for selector in title_selectors:
                    title_element = article.select_one(selector)
                    if title_element:
                        break
                
                title = title_element.text.strip() if title_element else "No title"
                
                url = title_element["href"] if title_element and "href" in title_element.attrs else "No URL"
                if url != "No URL" and not url.startswith("http"):
                    url = "https://www.marketbeat.com" + url
                
                # Try different selectors for source/date
                source_element = None
                date_element = None
                meta_selectors = ["div.byline.mb-1", "div.meta", "div.date", "span.date"]
                for selector in meta_selectors:
                    element = article.select_one(selector)
                    if element:
                        source_element = element
                        date_element = element
                        break
                
                source = "MarketBeat"
                if source_element:
                    text = source_element.text.strip()
                    if "|" in text:
                        source = text.split("|")[-1].strip()
                
                date_str = "No date"
                if date_element:
                    text = date_element.text.strip()
                    if "|" in text:
                        date_str = text.split("|")[0].strip()
                    else:
                        date_str = text
                
                date_iso = "Invalid date format"
                date_formats = [
                    "%B %d at %I:%M %p", 
                    "%B %d, %Y", 
                    "%b %d, %Y", 
                    "%Y-%m-%d", 
                    "%m/%d/%Y"
                ]
                
                for fmt in date_formats:
                    try:
                        if "at" in date_str and fmt == "%B %d at %I:%M %p":
                            date = datetime.strptime(date_str, fmt).replace(year=datetime.now().year)
                        else:
                            date = datetime.strptime(date_str, fmt)
                        date_iso = date.isoformat() + "Z"
                        break
                    except ValueError:
                        continue
                
                if date_iso == "Invalid date format":
                    logger.warning(f"Error parsing date '{date_str}' for symbol {symbol}")
                
                news_data.append({
                    "title": title,
                    "url": url,
                    "source": source,
                    "date": date_iso
                })
                
                count += 1
            
            # If we found articles, no need to try other exchanges
            if news_data:
                break
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching news for {symbol} on {exchange}: {e}")
            continue  # Try next exchange
    
    # If MarketBeat fails, try to use Yahoo Finance as a fallback
    if not news_data:
        logger.info(f"No news found on MarketBeat for {symbol}, trying Yahoo Finance fallback")
        try:
            from .fetch_news import fetch_news_data_yahoo
            yahoo_articles = fetch_news_data_yahoo(symbol)
            for article in yahoo_articles:
                news_data.append({
                    "title": article.get("headline", "No title"),
                    "url": article.get("url", "No URL"),
                    "source": "Yahoo Finance",
                    "date": article.get("publication_date", "Invalid date format")
                })
            logger.info(f"Found {len(news_data)} articles from Yahoo Finance for {symbol}")
        except Exception as e:
            logger.error(f"Error using Yahoo Finance fallback for {symbol}: {e}")
    
    return news_data
