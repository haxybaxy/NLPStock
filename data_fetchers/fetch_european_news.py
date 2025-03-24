from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse as date_parse
from yahoo_fin import news
import requests

def get_article_details_yahoo(article_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(article_url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        pub_date_tag = soup.find('time')
        pub_date = pub_date_tag['datetime'] if pub_date_tag else "No publication date found"

        content_tag = soup.find('div', class_='caas-body')
        content = content_tag.text if content_tag else "No content found"

        return pub_date, content
    else:
        print(f"Failed to retrieve the article. Status code: {response.status_code}")
        return "No publication date found", "No content found"

def fetch_european_news(symbol):
    articles = news.get_yf_rss(symbol)
    current_date = datetime.now(timezone.utc)
    one_month_ago = current_date - timedelta(days=30)
    filtered_articles = []

    for article in articles:
        pub_date = article['published']
        article_date = date_parse(pub_date).replace(tzinfo=timezone.utc)

        if article_date < one_month_ago:
            continue

        headline = article['title']
        url = article['url']
        pub_date, content = get_article_details_yahoo(url)

        filtered_articles.append({
            'headline': headline,
            'url': url,
            'publication_date': pub_date,
            'full_article_text': content,
        })

        if len(filtered_articles) >= 3:
            break

    return filtered_articles

