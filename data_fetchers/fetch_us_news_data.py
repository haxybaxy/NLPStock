from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse as date_parse
import requests
import logging
from yahoo_fin import news
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data_fetchers.article_extractor import extract_article_text

logger = logging.getLogger(__name__)

def get_article_details_yahoo(article_url):
    """Extract article content and publication date from Yahoo Finance articles"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(article_url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            pub_date_tag = soup.find('time')
            pub_date = pub_date_tag['datetime'] if pub_date_tag else "No publication date found"

            content_tag = soup.find('div', class_='caas-body')
            content = content_tag.text if content_tag else "No content found"

            return pub_date, content
        else:
            logger.warning(f"Failed to retrieve the article. Status code: {response.status_code}")
            return "No publication date found", "No content found"
    except Exception as e:
        logger.error(f"Error retrieving article: {e}")
        return "No publication date found", "No content found"

def fetch_us_news_data(symbol):
    """Fetch US market news for a stock symbol using Yahoo Finance RSS"""
    try:
        logger.info(f"Fetching Yahoo Finance RSS data for {symbol}")
        
        articles = news.get_yf_rss(symbol)
        current_date = datetime.now(timezone.utc)
        one_month_ago = current_date - timedelta(days=30)
        filtered_articles = []

        for article in articles:
            try:
                pub_date = article.get('published', '')
                if not pub_date:
                    continue
                    
                article_date = date_parse(pub_date).replace(tzinfo=timezone.utc)
                
                # Skip articles older than one month
                if article_date < one_month_ago:
                    continue

                title = article.get('title', 'No Title')
                url = article.get('link', article.get('url', ''))
                if not url:
                    continue
                
                # Use our improved article extractor
                full_text = extract_article_text(url)
                
                # Skip if no content was extracted
                if full_text == "Full article text not found.":
                    logger.warning(f"Could not extract content from {url}")
                    continue

                filtered_articles.append({
                    "title": title,
                    "url": url,
                    "source": "Yahoo Finance",
                    "date": pub_date,
                    "full_article_text": full_text
                })

                # Limit to 3 most recent articles
                if len(filtered_articles) >= 3:
                    break
                    
                # Add a small delay between article extractions
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing article for {symbol}: {e}")
                continue

        if filtered_articles:
            logger.info(f"Successfully fetched {len(filtered_articles)} news articles for {symbol}")
        else:
            logger.warning(f"No news articles found for {symbol}")
            
        return filtered_articles
    except Exception as e:
        logger.error(f"Error fetching US news for {symbol}: {e}")
        return []

def fetch_us_news(symbol):
    """Fetch US news for a specific stock symbol"""
    try:
        logger.info(f"Fetching US news data for {symbol}")
        return fetch_us_news_data(symbol)
    except Exception as e:
        logger.error(f"Error fetching US news for {symbol}: {e}")
        return []
