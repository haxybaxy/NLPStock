import logging
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

def extract_article_text(article_url, timeout=10):
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
        
        # Try different article containers
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