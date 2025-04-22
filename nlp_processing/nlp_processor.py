import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Use relative imports
from nlp_processing.text_preprocessing import extract_key_sentences
from nlp_processing.entity_extraction import extract_named_entities
from nlp_processing.keyword_extraction import extract_keywords

logger = logging.getLogger(__name__)

def process_article(article, company_name, ticker):
    """Process an article to extract key information"""
    if not article:
        logger.warning("Empty article passed to process_article")
        return None
    
    # Get the full article text
    text = article.get('full_article_text')
    
    # Log the fields in the article for debugging
    logger.debug(f"Article fields: {list(article.keys())}")
    
    if not text or text == "Full article text not found.":
        logger.warning(f"Missing or invalid article text for article with title: {article.get('title', 'No title')}")
        return None
    
    # Extract key information
    processed_data = {
        'title': article.get('title', article.get('headline', '')),
        'url': article.get('url', article.get('link', '')),
        'date': article.get('date', article.get('publication_date', '')),
        'key_sentences': extract_key_sentences(text, company_name, ticker),
        'named_entities': extract_named_entities(text),
        'keywords': extract_keywords(text)
    }
    
    # Create a condensed version for the LLM
    condensed_text = f"Title: {processed_data['title']}\n\n"
    condensed_text += f"Key information: {processed_data['key_sentences']}\n\n"
    
    # Add named entities
    if processed_data['named_entities']:
        condensed_text += "Named entities:\n"
        for entity_type, entities in processed_data['named_entities'].items():
            if entity_type in ['ORG', 'PERSON', 'GPE', 'MONEY', 'PERCENT', 'DATE']:
                condensed_text += f"- {entity_type}: {', '.join(entities[:5])}\n"
    
    # Add keywords
    if processed_data['keywords']:
        condensed_text += f"Keywords: {', '.join(processed_data['keywords'])}\n"
    
    processed_data['condensed_text'] = condensed_text
    return processed_data

def process_articles_batch(articles, company_name, ticker):
    """Process a batch of articles"""
    processed_articles = []
    
    for article in articles:
        processed = process_article(article, company_name, ticker)
        if processed:
            processed_articles.append(processed)
    
    logger.info(f"Processed {len(processed_articles)} articles out of {len(articles)} for {company_name} ({ticker})")
    return processed_articles 