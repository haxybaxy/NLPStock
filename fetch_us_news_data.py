from bs4 import BeautifulSoup
from datetime import datetime
import requests


def fetch_us_news_data(symbol):
    url = f"https://www.marketbeat.com/stocks/NASDAQ/{symbol}/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    news_data = []
    news_section = soup.find("div", class_="fade-bottom")

    if not news_section:
        print(f"No news section found for symbol {symbol}")
        return news_data

    articles = news_section.find_all("div", class_="mt-1 bg-white light-shadow d-flex")

    count = 0
    for article in articles:
        if count >= 3:
            break

        title_element = article.find("a", class_="d-block mb-1")
        title = title_element.text.strip() if title_element else "No title"

        url = title_element["href"] if title_element and "href" in title_element.attrs else "No URL"
        if not url.startswith("http"):
            url = "https://www.marketbeat.com" + url

        source_element = article.find("div", class_="byline mb-1")
        source = source_element.text.strip().split("|")[-1].strip() if source_element else "No source"

        date_element = article.find("div", class_="byline mb-1")
        date_str = date_element.text.strip().split("|")[0].strip() if date_element else "No date"

        date_iso = "Invalid date format"
        date_formats = ["%B %d at %I:%M %p", "%B %d, %Y"]  # List of formats

        for fmt in date_formats:
            try:

                if "at" in date_str and fmt == "%B %d at %I:%M %p":
                    date = datetime.strptime(date_str, fmt).replace(year=datetime.now().year)
                else:
                    date = datetime.strptime(date_str, fmt)
                date_iso = date.isoformat() + "Z"
                break
            except ValueError:
                continue

        if date_iso == "Invalid date format":
            print(f"Error parsing date '{date_str}' for symbol {symbol}")

        news_data.append({"title": title, "url": url, "source": source, "date": date_iso})

        count += 1

    return news_data
