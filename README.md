# NLPStock: AI-Powered Stock Movement Analysis

NLPStock is a robust platform that combines financial data with natural language processing and large language models (LLMs) to analyze stock movements and generate insightful explanations.

## Features

- **Portfolio Management**: Track customizable portfolios of stocks
- **Real-time Stock Data**: Fetch stock price data through Yahoo Finance
- **News Integration**: Collect relevant news from multiple sources for better context
- **NLP Processing**: Extract key information from news articles using NLP techniques
- **LLM-Powered Analysis**: Generate explanations for stock movements using Groq API
- **Interactive Dashboard**: Monitor and analyze your portfolio via a Streamlit interface

## Project Structure

```
NLPStock/
├── data_fetchers/              # Fetches stock and news data
│   ├── stock_price_fetcher.py  # YFinance integration for stock data
│   ├── fetch_news.py           # Generic news fetcher
│   ├── fetch_us_news_data.py   # US market specific news
│   ├── fetch_alpha_vantage_news.py  # Alpha Vantage news API
│   ├── fetch_european_news.py  # European market news
│   ├── fetch_nordic_news.py    # Nordic market news
│   ├── fetch_baltic_news.py    # Baltic market news
│   ├── combined_news_fetcher.py # Orchestrates all news sources
│   └── article_extractor.py    # Extracts full text from news URLs
├── nlp_processing/             # NLP components
│   ├── text_preprocessing.py   # Clean and prepare news text
│   ├── entity_extraction.py    # Extract named entities from text
│   ├── keyword_extraction.py   # Extract keywords from articles
│   └── nlp_processor.py        # Orchestrates NLP pipeline
├── summarization/              # LLM integration
│   ├── llm_client.py           # Groq API client
│   ├── summarize.py            # Article summarization
│   ├── why_it_moves.py         # Generate stock movement explanations
│   └── why_it_moves_simple.py  # Simplified explanation generator
├── utils/                      # Helper utilities
│   ├── portfolio_manager.py    # Portfolio data management
│   ├── stock_analyzer.py       # Main analysis coordinator
│   ├── file_operations.py      # File handling utilities
│   └── logging_config.py       # Logging setup
├── STOCK_DB/                   # Local data storage
│   ├── news/                   # Stored news articles
│   ├── prices/                 # Stock price data
│   ├── nlp_data/               # Processed NLP results
│   ├── analysis/               # Stock movement analysis
│   ├── movers/                 # Daily movers summaries
│   └── portfolios/             # User portfolio definitions
└── app.py                      # Streamlit dashboard
```

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/NLPStock.git
cd NLPStock
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your API keys:
```
GROQ_API_KEY=your_groq_api_key 
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key
```

## Obtaining API Keys

To use all features of NLPStock, you'll need to register for the following API keys:

### Groq API Key
1. Sign up for a free account at [Groq's website](https://console.groq.com/signup)
2. After signing in, navigate to the API section
3. Generate a new API key
4. Copy the key to your `.env` file as `GROQ_API_KEY`

### Alpha Vantage API Key
1. Register for a free API key at [Alpha Vantage](https://www.alphavantage.co/support/#api-key)
2. Fill out the registration form
3. You'll receive your API key via email or on their website
4. Copy the key to your `.env` file as `ALPHA_VANTAGE_API_KEY`

Note that the free tier of Alpha Vantage has rate limits (typically 5 API calls per minute and 500 per day). For more extensive usage, consider their premium plans.

## Usage

### Running the Streamlit Dashboard

```bash
streamlit run app.py
```

This will launch the interactive dashboard where you can:
- Create and manage portfolios
- Add and remove stocks
- Update stock price data
- Analyze moving stocks
- View detailed movement explanations
- Explore related news articles

### Using the CLI for Analysis

For headless operation, you can use the StockAnalyzer directly:

```bash
python -m utils.stock_analyzer
```

This will:
1. Update price data for all stocks in your default portfolio
2. Fetch the latest news articles
3. Identify stocks with significant movement
4. Generate explanations for why these stocks are moving
5. Output the results to the console and save them to the STOCK_DB/analysis directory

## News Data Sources

NLPStock fetches news from multiple sources to provide comprehensive coverage:

- **US Markets**: Yahoo Finance, Alpha Vantage News API
- **European Markets**: Dedicated European financial news APIs
- **Nordic Markets**: Nasdaq Nordic News API
- **Baltic Markets**: Specialized Baltic exchange news feeds

## NLP Processing Pipeline

The application processes news data through several stages:

1. **Text Preprocessing**: Clean and normalize text, remove stopwords
2. **Key Sentence Extraction**: Identify sentences most relevant to stock movement
3. **Entity Extraction**: Using spaCy to extract companies, people, locations, etc.
4. **Keyword Extraction**: Using YAKE algorithm to identify important keywords

## Stock Movement Analysis

When analyzing why a stock is moving, NLPStock:

1. Fetches historical price data and calculates daily change
2. Collects recent news articles from multiple sources
3. Processes news with the NLP pipeline
4. Sends the processed data to the LLM (Groq) for analysis
5. Generates a summary explanation of why the stock might be moving

## Development

### Adding a New News Source

1. Create a new fetcher in the `data_fetchers` directory
2. Implement the fetcher following the pattern in existing fetchers
3. Update `combined_news_fetcher.py` to include your new source

### Customizing NLP Processing

The NLP pipeline is modular and can be extended:
- Add new extractors to the `nlp_processing` directory
- Update `nlp_processor.py` to incorporate your changes

## Troubleshooting

- **Missing Data**: If you see "No data available" in the dashboard, try clicking "Generate Test Data" or "Update Portfolio Data"
- **Empty Analysis**: If no analysis is generated, ensure you have added API keys to the `.env` file
- **API Rate Limits**: If you encounter errors with external APIs, you may need to wait due to rate limiting
- **Pipeline Errors**: Check the logs in `streamlit_app.log` for detailed error information

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
