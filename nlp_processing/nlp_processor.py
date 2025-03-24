import logging
from NLPStock.nlp_processing.text_preprocessing import extract_key_sentences
from NLPStock.nlp_processing.entity_extraction import extract_named_entities
from NLPStock.nlp_processing.keyword_extraction import extract_keywords

logger = logging.getLogger(__name__)

def process_article(article, company_name, ticker):
    """Process an article to extract key information"""
    if not article:
        return None
    
    # Get the full article text if not already present
    if 'full_article_text' not in article or not article['full_article_text']:
        return None
    
    text = article['full_article_text']
    if text == "Full article text not found." or not text:
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
    
    return processed_articles 