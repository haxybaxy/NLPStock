from typing import Dict, List, Literal
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import certifi
import logging
import os
import requests
import sys
import time
import json
from pathlib import Path
from groq import Groq

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('why_it_moves.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

def create_retry_session(retries, backoff_factor, status_forcelist):
    """Create a retry session for HTTP requests."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


retry_session = create_retry_session(retries=2, backoff_factor=0.3, status_forcelist=(500, 502, 504))


def extract_article_text(article_url: str, timeout=10):
    """Extract text from an article given its URL with a timeout."""
    try:
        response = retry_session.get(article_url, timeout=timeout)
        if response.status_code == 404:
            logger.error(f"Article not found (404): {article_url}")
            return "Full article text not found."
        elif response.status_code != 200:
            logger.error(f"Failed to retrieve the article. Status code: {response.status_code}")
            return "Full article text not found."

        article_soup = BeautifulSoup(response.content, "html.parser")
        article_text_container = article_soup.find("div", class_="main-body-container article-body")
        if article_text_container:
            paragraphs = article_text_container.find_all("p")
            full_text = " ".join([paragraph.get_text() for paragraph in paragraphs])
            return full_text.strip()

        content_tag = article_soup.find("div", class_="caas-body")
        if content_tag:
            return content_tag.text.strip()

        paragraphs = article_soup.find_all("p")
        if paragraphs:
            return "\n".join(paragraph.get_text(strip=True) for paragraph in paragraphs)

        return "Full article text not found."
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while fetching article: {article_url}")
        return "Full article text not found."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching article at {article_url}: {e}")
        return "Full article text not found."


def get_news_articles(symbol: str, exchange: str):
    """Get news articles for the specified stock from local JSON files."""
    news_path = Path(f"STOCK_DB/news/{symbol}_news.json")
    if not news_path.exists():
        logger.warning(f"No news file found for {symbol}")
        return []
    
    try:
        with open(news_path, 'r') as f:
            articles = json.load(f)
            # Take the 5 most recent articles
            return articles[:5] if len(articles) > 5 else articles
    except Exception as e:
        logger.error(f"Error loading news for {symbol}: {e}")
        return []


def process_company_data(symbol: str, exchange: str, news_articles: List[Dict], classification: Literal["gainer", "loser"]):
    """Process the company data and news articles to generate a summary based on classification."""
    direction = "up" if classification == "gainer" else "down" if classification == "loser" else "neutral"
    logger.info(f"Processing data for symbol: {symbol} - Classified as {classification}")

    if not news_articles:
        logger.info(f"No news articles found for {symbol}")
        return {
            "symbol": symbol,
            "exchange": exchange,
            "type": classification,
            "period": "day",
            "summary": f"There are no news currently affecting the stock price, fluctuations might be due to market conditions.",
        }

    # Extract article text for articles that don't have it yet
    articles_with_text = 0
    for article in news_articles:
        url = article.get("url")
        if url and "full_article_text" not in article:
            full_article_text = extract_article_text(url)
            article["full_article_text"] = full_article_text
            if full_article_text != "Full article text not found.":
                articles_with_text += 1

    # Skip summary if all articles have no text
    if articles_with_text == 0:
        logger.info(f"All articles for {symbol} returned 'Full article text not found' - skipping summary")
        return {
            "symbol": symbol,
            "exchange": exchange,
            "type": classification,
            "period": "day",
            "summary": f"There are no news currently affecting the stock price, fluctuations might be due to market conditions.",
        }
    else:
        try:
            summaries = []
            for article in news_articles:
                full_text = article.get("full_article_text")
                if full_text and full_text != "Full article text not found.":
                    summary = summarize_article(full_text, symbol, direction)
                    summaries.append(summary)
                    time.sleep(2)  # 2-second delay between summary requests

            summaries = [s for s in summaries if s]
            if not summaries:
                logger.info(f"No valid summaries generated for {symbol}")
                return {
                    "symbol": symbol,
                    "exchange": exchange,
                    "type": classification,
                    "period": "day",
                    "summary": "No valid article summaries could be generated.",
                }
                
            explanation = summarize_articles(summaries, symbol)
            return {"symbol": symbol, "exchange": exchange, "type": classification, "summary": explanation}
        except Exception as e:
            logger.error(f"Error summarizing articles for {symbol}: {e}")
            return {
                "symbol": symbol,
                "exchange": exchange,
                "type": classification,
                "period": "day",
                "summary": "There was an error generating the summary.",
            }


def classify_company(net_change_percentage: float):
    """Classify the company based on net change percentage."""
    if net_change_percentage > 0:
        return "gainer"
    else:
        return "loser"


def why_it_moves(symbol: str, exchange: str, daily_change_percentage: float):
    """Generate a summary of why a stock is moving and save it locally."""
    classification = classify_company(daily_change_percentage)

    news_articles = get_news_articles(symbol, exchange)
    summary = {
        **process_company_data(symbol, exchange, news_articles, classification),
        "daily_change_percentage": daily_change_percentage,
        "date_generated": datetime.now(timezone.utc).isoformat(),
    }

    # Save the summary to a local file
    output_dir = Path("STOCK_DB/movers")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{symbol}_summary.json"
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)

    logger.info(f"{exchange}/{symbol} mover summary saved to {output_file}")
    return summary


def get_groq_client():
    """Initialize Groq client with API key from environment"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables")
    return Groq(api_key=api_key)


def summarize_article(text: str, symbol: str, direction: str) -> str:
    """Summarize article text using Groq API"""
    client = get_groq_client()
    
    prompt = f"""
    Analyze this news article about {symbol} stock and explain how it might relate to the stock moving {direction}. 
    Focus on key factors that could influence stock price.
    
    Article text: {text}
    """
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="mixtral-8x7b-32768",  # or your preferred Groq model
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error getting summary from Groq: {e}")
        return ""


def summarize_articles(summaries: List[str], symbol: str) -> str:
    """Combine multiple article summaries using Groq API"""
    client = get_groq_client()
    
    prompt = f"""
    Based on these news summaries about {symbol}, provide a concise explanation of why the stock might be moving:
    
    {' '.join(summaries)}
    """
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="mixtral-8x7b-32768",  # or your preferred Groq model
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error getting combined summary from Groq: {e}")
        return "Unable to generate summary due to an error."


def process_all_stocks():
    """Process all stocks that have news data and generate summaries."""
    news_dir = Path("STOCK_DB/news")
    if not news_dir.exists():
        logger.error("News directory not found")
        return
    
    # Get all news files
    news_files = list(news_dir.glob("*_news.json"))
    logger.info(f"Found {len(news_files)} stocks with news data")
    
    for news_file in news_files:
        try:
            # Extract symbol from filename (remove _news.json)
            symbol = news_file.stem.replace("_news", "")
            
            # Default to NASDAQ exchange if not known
            exchange = "NASDAQ"
            
            # Use a random change percentage for demonstration
            # In a real scenario, you would get this from price data
            import random
            daily_change = random.uniform(-5.0, 5.0)
            
            logger.info(f"Processing {symbol} with change {daily_change:.2f}%")
            summary = why_it_moves(symbol, exchange, daily_change)
            
            # Print a brief version of the summary
            print(f"\n{symbol} ({exchange}) - Change: {daily_change:.2f}%")
            print(f"Classification: {summary['type']}")
            print(f"Summary: {summary['summary'][:200]}...\n")
            
            # Add a small delay to avoid rate limiting
            time.sleep(3)
            
        except Exception as e:
            logger.error(f"Error processing {news_file.name}: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # If arguments provided, process specific stock
        exchange = str(sys.argv[1])
        symbol = str(sys.argv[2])
        daily_change = float(sys.argv[3]) if len(sys.argv) > 3 else 0.01
        
        summary = why_it_moves(symbol, exchange, daily_change)
        print(f"\n{symbol} ({exchange}) - Change: {daily_change:.2f}%")
        print(f"Classification: {summary['type']}")
        print(f"Summary: {summary['summary']}\n")
    else:
        # Process all stocks with news data
        process_all_stocks()
