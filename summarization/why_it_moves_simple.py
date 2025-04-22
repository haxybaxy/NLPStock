from typing import Dict, List, Literal
from datetime import datetime, timezone
import logging
import time
import json
from pathlib import Path
import sys
import os

# Fix imports to be relative
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data_fetchers.article_extractor import extract_article_text
from nlp_processing.nlp_processor import process_articles_batch
from utils.file_operations import ensure_directory, load_json, save_json
from summarization.llm_client import LLMClient

logger = logging.getLogger(__name__)

# Create a simple LLM client that generates a default summary
def summarize_article(article_text, symbol, direction):
    """Summarize a single article about a stock"""
    if not article_text or article_text == "Full article text not found.":
        return None
    
    client = LLMClient()
    
    prompt = f"""
    Analyze this processed news information about {symbol} stock and explain how it might relate to the stock moving {direction}. 
    Focus on key factors that could influence stock price.
    
    Processed information: {article_text}
    """
    
    try:
        return client.generate(prompt)
    except Exception as e:
        logger.error(f"Error summarizing article: {e}")
        return None

def summarize_articles(article_summaries, symbol):
    """Combine multiple article summaries into a single explanation"""
    if not article_summaries:
        return "No valid articles found to summarize."
    
    valid_summaries = [summary for summary in article_summaries if summary]
    if not valid_summaries:
        return "No valid summaries to combine."
    
    client = LLMClient()
    
    prompt = f"""
    Based on these news summaries about {symbol}, provide a concise explanation of why the stock might be moving:
    
    {' '.join(valid_summaries)}
    """
    
    try:
        return client.generate(prompt)
    except Exception as e:
        logger.error(f"Error combining summaries: {e}")
        return "Unable to generate summary due to an error."

def get_news_articles(symbol: str):
    """Get news articles for the specified stock from local JSON files."""
    news_path = Path(f"STOCK_DB/news/{symbol}_news.json")
    if not news_path.exists():
        logger.warning(f"No news file found for {symbol}")
        return []
    
    try:
        articles = load_json(news_path)
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

    # Count articles with text and extract text for those without it
    articles_with_text = 0
    for article in news_articles:
        # Check if the article already has the full text
        if "full_article_text" in article and article["full_article_text"] != "Full article text not found.":
            articles_with_text += 1
            continue
            
        # Try fetching the article content if not already present
        url = article.get("url", "")
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
            # Process articles with NLP to extract key information
            processed_articles = process_articles_batch(news_articles, symbol, symbol)
            
            # Print the processed text after NLP
            print("\n" + "="*80)
            print(f"PROCESSED TEXT AFTER NLP FOR {symbol}:")
            print("="*80)
            
            # Save processed articles data for future reference
            processed_data = []
            summaries = []

            for i, article in enumerate(processed_articles):
                # Print the condensed text
                condensed_text = article.get('condensed_text', '')
                if condensed_text:
                    print(f"\nArticle {i+1}:")
                    print("-" * 40)
                    print(condensed_text)
                    print("-" * 40)
                    
                    # Save all the processed information
                    article_data = {
                        "title": article.get('title', 'No title'),
                        "url": article.get('url', ''),
                        "date": article.get('date', ''),
                        "key_sentences": article.get('key_sentences', ''),
                        "named_entities": article.get('named_entities', {}),
                        "keywords": article.get('keywords', []),
                        "condensed_text": condensed_text
                    }
                    processed_data.append(article_data)
                    
                    # Generate summary
                    summary = summarize_article(condensed_text, symbol, direction)
                    if summary:
                        summaries.append(summary)
                        # Store the summary with the article data
                        article_data["summary"] = summary
                    time.sleep(2)  # 2-second delay between summary requests

            summaries = [s for s in summaries if s]
            if not summaries:
                logger.info(f"No valid summaries generated for {symbol}")
                result = {
                    "symbol": symbol,
                    "exchange": exchange,
                    "type": classification,
                    "period": "day",
                    "summary": "No valid article summaries could be generated.",
                    "processed_articles": processed_data
                }
            else:
                explanation = summarize_articles(summaries, symbol)
                result = {
                    "symbol": symbol, 
                    "exchange": exchange, 
                    "type": classification, 
                    "summary": explanation,
                    "processed_articles": processed_data
                }

            # Save the NLP processed data to a separate file
            output_dir = ensure_directory("STOCK_DB/nlp_data")
            output_file = Path(output_dir) / f"{symbol}_nlp_data.json"
            save_json(processed_data, output_file)
            logger.info(f"NLP data for {symbol} saved to {output_file}")
            
            return result
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
    
    # When there's no news data, create a default summary
    if not Path(f"STOCK_DB/news/{symbol}_news.json").exists():
        summary = {
            "symbol": symbol,
            "exchange": exchange,
            "type": classification,
            "period": "day",
            "summary": f"No news data available for {symbol}. The stock's movement of {daily_change_percentage:.2f}% may be related to market conditions or unreported news.",
            "daily_change_percentage": daily_change_percentage,
            "date_generated": datetime.now(timezone.utc).isoformat(),
        }
    else:
        news_articles = get_news_articles(symbol)
        result = process_company_data(symbol, exchange, news_articles, classification)
        summary = {
            **result,
            "daily_change_percentage": daily_change_percentage,
            "date_generated": datetime.now(timezone.utc).isoformat(),
        }

    # Save the summary to a local file
    output_dir = ensure_directory("STOCK_DB/movers")
    output_file = Path(output_dir) / f"{symbol}_summary.json"
    save_json(summary, output_file)

    logger.info(f"{exchange}/{symbol} mover summary saved to {output_file}")
    return summary

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