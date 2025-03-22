from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from dateutil import parser
from dateutil.parser import parse as date_parse
from yahoo_fin import news
import requests


def extract_article_text(article_url):
    response = requests.get(article_url)
    if response.status_code != 200:
        print(f"Failed to retrieve the article. Status code: {response.status_code}")
        return "Full article text not found."

    article_soup = BeautifulSoup(response.content, "html.parser")
    article_text_container = article_soup.find("div", class_="main-body-container article-body")
    if article_text_container:
        paragraphs = article_text_container.find_all("p")
        full_text = " ".join([paragraph.get_text() for paragraph in paragraphs])
        return full_text.strip()
    return "Full article text not found."


def fetch_news_data_globe(symbol):
    url = f"https://www.globenewswire.com/en/search/keyword/{symbol}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")
        return []

    html_content = response.content
    soup = BeautifulSoup(html_content, "html.parser")
    articles = soup.find_all("div", class_="pagnition-row row")

    news_data = []
    current_date = datetime.now(timezone.utc)
    one_month_ago = current_date - timedelta(days=30)

    tzinfos = {
        "ET": -5 * 3600,  # Eastern Time (US & Canada)
        "EET": 2 * 3600,  # Eastern European Time
        "EEST": 3 * 3600,  # Eastern European Summer Time
    }

    for article in articles:
        title_tag = article.find("a", {"data-section": "article-url"})
        description_tag = article.find("span", {"data-section": "article-summary"})
        date_tag = article.find("span", {"data-section": "article-published-date"})

        if title_tag and description_tag:
            title = title_tag.text.strip()
            url = "https://www.globenewswire.com" + title_tag["href"]
            date_str = date_tag.text.strip() if date_tag else "N/A"

            date_iso = "Invalid date format"
            try:
                date = parser.parse(date_str, fuzzy=True, tzinfos=tzinfos)
                date = date.astimezone(timezone.utc)
                date_iso = date.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OverflowError) as e:
                print(f"Error parsing date '{date_str}' for article titled '{title}': {e}")

            try:
                parsed_date = datetime.strptime(date_iso, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                if parsed_date < one_month_ago:
                    continue
            except ValueError:
                pass

            news_data.append(
                {
                    "title": title,
                    "url": url,
                    "date": date_iso,
                }
            )

            if len(news_data) >= 6:
                break

    return news_data


def get_article_details_yahoo(article_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    response = requests.get(article_url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        pub_date_tag = soup.find("time")
        pub_date = pub_date_tag["datetime"] if pub_date_tag else "No publication date found"

        content_tag = soup.find("div", class_="caas-body")
        content = content_tag.text if content_tag else "No content found"

        return pub_date, content
    else:
        print(f"Failed to retrieve the article. Status code: {response.status_code}")
        return "No publication date found", "No content found"


def fetch_news_data_yahoo(symbol):
    articles = news.get_yf_rss(symbol)
    current_date = datetime.now(timezone.utc)
    one_month_ago = current_date - timedelta(days=30)
    filtered_articles = []

    for article in articles:
        pub_date = article["published"]
        article_date = date_parse(pub_date).replace(tzinfo=timezone.utc)

        if article_date < one_month_ago:
            continue
        headline = article["title"]
        url = article["link"]
        pub_date, content = get_article_details_yahoo(url)

        filtered_articles.append(
            {
                "headline": headline,
                "url": url,
                "publication_date": pub_date,
                "full_article_text": content,
            }
        )

        if len(filtered_articles) >= 3:
            break

    return filtered_articles
