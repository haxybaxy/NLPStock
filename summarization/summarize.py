import logging
from transformers import pipeline
from NLPStock.summarization.llm_client import LLMClient

logger = logging.getLogger(__name__)

# Initialize the summarization pipeline
try:
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
except Exception as e:
    logger.error(f"Error initializing summarization pipeline: {e}")
    summarizer = None

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
        summary = client.generate(prompt)
        
        # Post-process with BART if available
        if summarizer:
            try:
                final_summary_result = summarizer(summary, max_length=100, min_length=60, do_sample=False)
                if isinstance(final_summary_result, list):
                    final_summary = final_summary_result[0]["summary_text"]
                else:
                    final_summary = summary
                
                # Post-process to remove sentences with unwanted phrases
                phrases_to_avoid = ["several factors", "combination of factors", "various factors"]
                sentences = final_summary.split(". ")
                filtered_sentences = [
                    sentence for sentence in sentences if not any(phrase in sentence.lower() for phrase in phrases_to_avoid)
                ]
                return ". ".join(filtered_sentences)
            except Exception as e:
                logger.error(f"Error in BART summarization: {e}")
                return summary
        else:
            return summary
    except Exception as e:
        logger.error(f"Error combining summaries: {e}")
        return "Unable to generate summary due to an error." 