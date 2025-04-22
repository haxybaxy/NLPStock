import logging
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

logger = logging.getLogger(__name__)

def create_retry_session(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504)):
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

# Create a session with retry capability
retry_session = create_retry_session()

def extract_article_text(article_url, timeout=15, max_redirects=5):
    """Extract text from an article given its URL with a timeout."""
    if not article_url or article_url == "No URL":
        logger.error("No valid URL provided for article extraction")
        return "Full article text not found."
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        logger.info(f"Extracting article text from: {article_url}")
        response = retry_session.get(
            article_url, 
            timeout=timeout, 
            headers=headers,
            allow_redirects=True
        )
        
        if response.status_code == 404:
            logger.error(f"Article not found (404): {article_url}")
            return "Full article text not found."
        elif response.status_code != 200:
            logger.error(f"Failed to retrieve the article. Status code: {response.status_code}")
            return "Full article text not found."

        # Get the final URL after any redirects
        final_url = response.url
        if final_url != article_url:
            logger.info(f"URL redirected to: {final_url}")
        
        article_soup = BeautifulSoup(response.content, "html.parser")
        
        # Yahoo Finance specific handling
        if "finance.yahoo.com" in final_url:
            content_tag = article_soup.find("div", class_="caas-body")
            if content_tag:
                full_text = content_tag.get_text(separator=" ", strip=True)
                logger.info(f"Successfully extracted Yahoo Finance article: {len(full_text)} characters")
                return full_text

        # Try different article containers for other sites
        article_text_container = article_soup.find("div", class_="main-body-container article-body")
        if article_text_container:
            paragraphs = article_text_container.find_all("p")
            full_text = " ".join([paragraph.get_text() for paragraph in paragraphs])
            return full_text.strip()

        # Try generic article content patterns
        article_container = article_soup.find("article") or article_soup.find("div", class_=lambda c: c and ("article" in c or "content" in c))
        if article_container:
            paragraphs = article_container.find_all("p")
            if paragraphs:
                full_text = " ".join([p.get_text(strip=True) for p in paragraphs])
                if full_text:
                    logger.info(f"Extracted article content from article container: {len(full_text)} characters")
                    return full_text

        # Last resort - just get all paragraphs
        paragraphs = article_soup.find_all("p")
        if paragraphs:
            full_text = "\n".join(paragraph.get_text(strip=True) for paragraph in paragraphs)
            if len(full_text) > 100:  # Ensure we have meaningful content
                logger.info(f"Extracted generic paragraphs: {len(full_text)} characters")
                return full_text

        logger.error(f"Failed to extract content from {final_url}")
        return "Full article text not found."
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while fetching article: {article_url}")
        return "Full article text not found."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching article at {article_url}: {e}")
        return "Full article text not found."
    except Exception as e:
        logger.error(f"Unexpected error extracting article from {article_url}: {e}")
        return "Full article text not found." 