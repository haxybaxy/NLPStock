# NLPStock: Stock Movement Analysis with NLP

NLPStock is a comprehensive tool that analyzes news articles to explain stock price movements. It fetches financial news from various sources, processes the text using Natural Language Processing (NLP) techniques, and generates explanations for why stocks are moving up or down.

## Features

- **Multi-Source News Fetching**: Collects news from US, European, Nordic, and Baltic sources
- **Advanced NLP Processing**: Extracts key sentences, named entities, and keywords from articles
- **LLM-Powered Summarization**: Uses Groq's LLama 3 model to generate insightful explanations
- **Modular Architecture**: Clean separation between data fetching, NLP processing, and summarization

## Directory Structure 

NLPStock/
├── data_fetchers/ # Fetch news from various sources
├── nlp_processing/ # Process news articles
├── summarization/ # Summarize news articles
└── utils/ # Utility functions
└── STOCK_DB/ # Stock data and news articles
├── run.py # Main entry point
└── requirements.txt # Dependencies

## Installation

1. Clone the repository:
git clone https://github.com/evaks1/NLPStock.git
cd NLPStock

2. Install dependencies:
pip install -r requirements.txt

3. Create and activate virtual environment:
python -m venv venv
source venv/bin/activate # Linux/Mac
venv\Scripts\activate # Windows

4. Create a `.env` file in the root directory with your API keys:
GROQ_API_KEY=your_groq_api_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key
## Usage

1. Fetch news for a specific stock:
python run.py --symbol AAPL --exchange US --change 1.5 --fetch-news

2. Fetch news for multiple stocks from a file:
python run.py --symbols-file symbols.txt --exchanges-file exchanges.txt --fetch-news

3. Process all stocks in the database:
python run.py --all

Where `symbols.txt` contains one symbol per line and `exchanges.txt` contains the corresponding exchanges.

## Command Line Arguments

- `--symbol`: Stock symbol to analyze (e.g., AAPL, MSFT)
- `--exchange`: Stock exchange (default: US)
- `--change`: Daily change percentage (default: 0.01)
- `--all`: Process all stocks with news data
- `--fetch-news`: Fetch news before analysis
- `--symbols-file`: Path to a file containing symbols to fetch news for
- `--exchanges-file`: Path to a file containing exchanges for the symbols

## Example Output

For each stock, the script will:
1. Fetch news articles
2. Process the articles to extract key information
3. Generate an explanation for the stock movement
4. Save the results to the database

## How It Works

1. **News Fetching**: The system fetches recent news articles about the specified stock from various financial news sources.

2. **Text Processing**: Articles are processed using NLP techniques to:
   - Extract key sentences relevant to stock movement
   - Identify named entities (companies, people, locations)
   - Extract important keywords and financial terms

3. **Summarization**: The processed text is sent to an LLM (Groq's LLama 3) which generates a concise explanation of why the stock is moving.

4. **Classification**: Based on the price change, the stock is classified as a "gainer" or "loser", and the summary is tailored accordingly.

## Requirements

- Python 3.8+
- NLTK
- spaCy
- Groq API access
- BeautifulSoup4
- Requests

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [NLTK](https://www.nltk.org/) for natural language processing
- [spaCy](https://spacy.io/) for named entity recognition
- [Groq](https://groq.com/) for LLM API access
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) for web scraping
