from datetime import timezone
import time
from dateutil import parser
import dotenv
try:
    from dotenv import load_dotenv
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call(["pip", "install", "python-dotenv"])
    from dotenv import load_dotenv
from langdetect import detect, LangDetectException
from pymongo import MongoClient
import certifi
import logging
import os
import sys
import json
from pathlib import Path
from typing import List, Dict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#from config.logging_config import setup_logging
from fetch_baltic_news import fetch_news_for_company as fetch_baltic_news_for_company
from fetch_european_news import fetch_european_news
from fetch_news import fetch_news_data_yahoo, fetch_news_data_globe
from fetch_nordic_news import fetch_news_for_company as fetch_nordic_news_for_company
from fetch_us_news_data import fetch_us_news_data


load_dotenv()

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('news_fetcher.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

start_time = time.time()


def fetch_news(company_info):
    """Fetch news for a company from various sources"""
    symbol = company_info.get("symbol")
    news_articles = []
    
    try:
        # Try to fetch news from different sources
        try:
            us_news = fetch_us_news_data(symbol)
            news_articles.extend(us_news)
        except Exception as e:
            logger.error(f"Error fetching US news for {symbol}: {str(e)}")
        
        try:
            yahoo_news = fetch_news_data_yahoo(symbol)
            news_articles.extend(yahoo_news)
        except Exception as e:
            logger.error(f"Error fetching Yahoo news for {symbol}: {str(e)}")
            
        try:
            globe_news = fetch_news_data_globe(symbol)
            news_articles.extend(globe_news)
        except Exception as e:
            logger.error(f"Error fetching Globe news for {symbol}: {str(e)}")
            
        # Add other news sources as needed
        
        return news_articles
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {str(e)}")
        return []  # Return empty list on error


def normalize_article_fields(article):
    return {
        "title": article.get("title", article.get("headline", "")),
        "date": article.get("date", article.get("publication_date", "")),
        "source": article.get("source", "Unknown"),
        "url": article.get("url", article.get("Message URL", "")),
    }


def is_english(text):
    try:
        return detect(text) == "en"
    except LangDetectException:
        logging.error(f"Failed to detect language for text: {text}")
        return False


def parse_date(date_str):
    try:
        parsed_date = parser.parse(date_str)
        date_object = parsed_date.replace(tzinfo=timezone.utc)
        return date_object.astimezone(timezone.utc)
    except ValueError:
        logging.error(f"Unrecognized date format: {date_str}")
        return None


def insert_news_into_db(client: MongoClient, company, news_data):
    news_collection = client.STOCK_DB.news

    try:
        for article in news_data:
            normalized_article = normalize_article_fields(article)
            if "url" not in normalized_article or not normalized_article["url"]:
                logging.error(f"Missing 'url' in article for {company['symbol']}: {normalized_article}")
                continue

            pub_date = parse_date(normalized_article["date"])
            if pub_date is None:
                logging.error(f"Failed to parse date for article: {normalized_article}")
                continue

            # Check if the article is in English
            if not is_english(normalized_article["title"]):
                logging.info(f"Skipping non-English article for {company['symbol']} on {company['exchange']}")
                continue

            article_data = {
                "symbol": company["symbol"],
                "exchange": company["exchange"],
                "title": normalized_article["title"],
                "publication_date": pub_date,
                "url": normalized_article["url"],
            }

            # This will only insert if the article does not already exist
            news_collection.update_one(
                {
                    "symbol": article_data["symbol"],
                    "exchange": article_data["exchange"],
                    "publication_date": article_data["publication_date"],
                },
                {"$set": article_data},
                upsert=True,
            )
            logging.info(f"Inserted article for {company['symbol']} into news")

    except Exception as e:
        logging.error(f"Error inserting articles for {company['symbol']} in news: {e}")


def fetch_all_news(client):
    company_data_collection = client.STOCK_DB.company_data

    for company in company_data_collection.find():
        company_info = {
            "symbol": company.get("symbol"),
            "company_name": company.get("name"),
            "exchange": company.get("exchange"),
            "country": company.get("country"),
            "gcfIssuerId": company.get("gcfIssuerId"),
        }
        news_articles = fetch_news(company_info)
        insert_news_into_db(client, company_info, news_articles)


def load_stock_data() -> List[Dict]:
    """Load stock data from local JSON file"""
    try:
        data_path = Path("STOCK_DB/STOCK_DB.eod_price_data.json")
        if not data_path.exists():
            logger.error("Stock data file not found at: %s", data_path)
            return []
        
        with open(data_path, 'r') as f:
            data = json.load(f)
            logger.info(f"Successfully loaded {len(data)} stocks from local file")
            return data
    except Exception as e:
        logger.error("Error loading stock data: %s", str(e))
        return []


def save_news_to_file(company_info: Dict, news_articles: List[Dict]):
    """Save news articles to a local JSON file"""
    try:
        output_dir = Path("STOCK_DB/news")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{company_info['symbol']}_news.json"
        with open(output_file, 'w') as f:
            json.dump(news_articles, f, indent=2)
        logger.info(f"Saved news for {company_info['symbol']} to {output_file}")
    except Exception as e:
        logger.error(f"Error saving news for {company_info['symbol']}: {str(e)}")


def fetch_all_news():
    """Fetch news for all companies from local stock data"""
    companies = load_stock_data()
    logger.info(f"Starting news fetch for {len(companies)} companies")
    
    for company in companies:
        try:
            company_info = {
                "symbol": company.get("symbol"),
                "company_name": company.get("name", "Unknown"),
                "exchange": company.get("exchange"),
                "country": company.get("country", "Unknown"),
                "gcfIssuerId": company.get("gcfIssuerId"),
            }
            
            logger.info(f"Fetching news for {company_info['symbol']}")
            news_articles = fetch_news(company_info)
            save_news_to_file(company_info, news_articles)
            
        except Exception as e:
            logger.error(f"Error processing company {company.get('symbol')}: {str(e)}")
            continue


def news_main():
    start_time = time.time()
    logger.info("Starting news collection process")
    
    try:
        fetch_all_news()
        duration = time.time() - start_time
        logger.info(f"News collection completed. Time taken: {duration:.2f} seconds")
    except Exception as e:
        logger.error(f"Fatal error in news collection: {str(e)}")


if __name__ == "__main__":
    news_main()
