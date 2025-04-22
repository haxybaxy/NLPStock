# NLPStock: Stock Movement Analysis with NLP and LLMs

NLPStock is a powerful tool that combines financial data with natural language processing and LLMs to analyze stock movements and generate insightful explanations.

## Features

- **Portfolio Management**: Track stocks in your personalized portfolio
- **Automated Data Fetching**: Get real-time stock data using yfinance
- **Movement Detection**: Identify stocks with significant price movements
- **AI-Powered Analysis**: Generate explanations for why stocks are moving using news data and LLMs
- **Streamlit Dashboard**: Interactive UI for monitoring and analyzing your portfolio

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd NLPStock
```

2. Make sure you have the following prerequisites installed:
   - Python 3.8 or higher
   - make (standard on macOS)
   - pip

3. Add your Groq API key to the `.env` file:
```
GROQ_API_KEY = "your-api-key-here"
```

4. Use the Makefile to set up and run the project:
```bash
# Install dependencies and set up the environment
make setup

# Initialize your portfolio with some default stocks
make init-portfolio
```

## Usage

### Using the Makefile (Recommended for macOS)

The project includes a Makefile that simplifies common operations:

```bash
# Start the Streamlit app
make run

# Run the stock analysis
make analyze

# Fetch latest stock data for your portfolio
make fetch

# Add a new stock to your portfolio
make add-stock

# Run diagnostics if you're having issues
make debug

# See all available commands
make help
```

### Running the Streamlit App Directly

```bash
# Activate the virtual environment first
source venv/bin/activate

# Then run Streamlit
streamlit run app.py
```

## Working with Your Portfolio

1. Start by initializing your portfolio with some default stocks:
```bash
make init-portfolio
```

2. Add more stocks as needed:
```bash
make add-stock
# When prompted, enter the ticker symbol (e.g., AAPL, MSFT)
```

3. Update stock data:
```bash
make fetch
```

4. Analyze moving stocks:
```bash
make analyze
```

5. View the analysis in the Streamlit app:
```bash
make run
```

## Project Structure

- `app.py` - Streamlit web application
- `stock_analyzer.py` - Main analysis coordinator
- `data_fetchers/` - Scripts for fetching stock and news data
  - `stock_price_fetcher.py` - yfinance integration for stock data
  - `fetch_news.py` - News data collection
- `nlp_processing/` - NLP components
  - `text_preprocessing.py` - Clean and prepare text
  - `entity_extraction.py` - Extract entities from text
- `summarization/` - LLM integration
  - `llm_client.py` - Groq API client
  - `why_it_moves.py` - Generate stock movement explanations
- `utils/` - Helper utilities
  - `portfolio_manager.py` - Portfolio data management
  - `file_operations.py` - File handling utilities
- `STOCK_DB/` - Data storage directory

## Troubleshooting

If you encounter issues:

1. Run the diagnostics:
```bash
make debug
```

2. Check that your Groq API key is set correctly in the `.env` file

3. Make sure all dependencies are installed:
```bash
make setup
```

4. If imports are failing, try:
```bash
python setup_paths.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 