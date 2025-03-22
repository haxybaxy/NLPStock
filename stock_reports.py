import json
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.logging_config import setup_logging
from news.summarize import groq_manager, send_prompt, retry
from news.why_it_moves import why_it_moves

intel_text = open("news/intel_text.txt", "r").read()

load_dotenv()

setup_logging()
logger = logging.getLogger(__name__)


def get_key_stats(symbol: str, exchange: str, client: MongoClient):
    db = client.STOCK_DB
    statistics = db.statistics.find_one(
        {"symbol": symbol, "exchange": exchange},
        {
            "_id": 0,
            "close_price": 1,
            "daily_change": 1,
            "daily_change_percentage": 1,
            "market_capitalization": 1,
            "trailing_annual_dividend_yield": 1,
        },
    )
    fundamentals = list(
        db.fundamental_data.aggregate(
            [
                {
                    "$match": {
                        "symbol": symbol,
                        "exchange": exchange,
                    }
                },
                {"$project": {"annual_statements": {"$slice": ["$annual_statements", 2]}}},
                {"$unwind": "$annual_statements"},
                {
                    "$project": {
                        "_id": 0,
                        "total_revenue": "$annual_statements.total_revenue",
                        "basic_eps": "$annual_statements.basic_eps",
                        "net_debt": "$annual_statements.net_debt",
                    }
                },
            ]
        )
    )
    eps_yoy_growth = (fundamentals[0]["basic_eps"] - fundamentals[1]["basic_eps"]) / fundamentals[1]["basic_eps"]
    revenue_yoy_growth = (fundamentals[0]["total_revenue"] - fundamentals[1]["total_revenue"]) / fundamentals[1][
        "total_revenue"
    ]
    
    return statistics | fundamentals[0] | {"eps_yoy_growth": eps_yoy_growth, "revenue_yoy_growth": revenue_yoy_growth}


def generate_bigger_picture(text: str):
    prompt = f"Provide a 'bigger picture' summary of the stock based on the following text:\n\n"
    prompt += text
    return retry(send_prompt, prompt=prompt)


def generate_whats_next(template: dict):
    prompt = f"Act as a financial analyst and in a few sentences explain what to expect next for the stock based on the following information:\n\n"
    prompt += json.dumps(template)
    return retry(send_prompt, prompt=prompt)


def generate_report(symbol: str, exchange: str, client: MongoClient):
    template = {
        "symbol": symbol,
        "exchange": exchange,
        "slug": "google-why-it-moves",  # TODO: generate slug
        "key_stats": None,
        "content_en": {
            "title": "Google Why It Moves",  # TODO: generate title
            "why_it_moves": None,
            "company_overview": None,
            "bigger_picture": None,
            "whats_next": None,
        },
    }

    try:
        template["content_en"]["why_it_moves"] = (
            "GOOGL, Alphabet Inc.'s parent company, is moving up due to a meeting with the Trump transition team. The meeting may lead to increased government contracts and advertising revenue for the company. GOOGL is up 1.7% to $1,071.50. Gogle is down 1.3% to £1,051."
        )
        template["key_stats"] = get_key_stats(symbol, exchange, client)
        template["content_en"]["company_overview"] = client.STOCK_DB.company_data.find_one(
            {"symbol": symbol, "exchange": exchange}, {"_id": 0, "description": 1}
        ).get("description")
        template["content_en"]["bigger_picture"] = generate_bigger_picture(intel_text)
        template["content_en"]["whats_next"] = generate_whats_next(template)
    except Exception as e:
        logger.error(f"Failed to generate report for {exchange}/{symbol}: {e}")

    client.STOCK_DB.articles.insert_one(template)


if __name__ == "__main__":
    client = MongoClient(os.getenv("DB_URI"), tlsCAFile=certifi.where())

    exchange = str(sys.argv[1])
    symbol = str(sys.argv[2])

    generate_report(symbol, exchange, client)
