#!/bin/bash

# NLPStock Runner Script for macOS

# First, check if we're in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    # We're not in a virtual environment, try to activate it
    if [ -d "venv" ]; then
        echo "Activating virtual environment..."
        source venv/bin/activate
        if [[ -z "$VIRTUAL_ENV" ]]; then
            echo "ERROR: Failed to activate virtual environment. Please run: source venv/bin/activate"
            exit 1
        fi
    else
        echo "Virtual environment not found. Creating one..."
        python3 -m venv venv
        source venv/bin/activate
        echo "Installing required dependencies..."
        pip install -r requirements.txt
    fi
fi

# Create required directories with macOS-friendly mkdir
mkdir -p STOCK_DB/news
mkdir -p STOCK_DB/prices
mkdir -p STOCK_DB/portfolios
mkdir -p STOCK_DB/analysis
mkdir -p STOCK_DB/movers

# Check for Groq API key
if grep -q "GROQ_API_KEY = \"\"" .env || ! grep -q "GROQ_API_KEY" .env; then
    echo "ERROR: Groq API key not set. Please add your API key to the .env file."
    echo "Edit the .env file and add: GROQ_API_KEY = \"your-api-key-here\""
    exit 1
fi

# Check for required packages in the virtual environment
echo "Checking required packages..."
pip install streamlit yfinance pandas nltk groq python-dotenv

# Download NLTK data if needed
if ! python -c "import nltk; nltk.data.find('tokenizers/punkt')" &> /dev/null; then
    echo "Downloading NLTK data..."
    python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
fi

# Check command line arguments
if [ "$1" = "streamlit" ] || [ "$1" = "app" ]; then
    echo "Starting Streamlit app..."
    streamlit run app.py
elif [ "$1" = "analyze" ]; then
    echo "Running stock analyzer..."
    python stock_analyzer.py
elif [ "$1" = "fetch" ]; then
    echo "Fetching stock data..."
    python -c "from data_fetchers.stock_price_fetcher import update_portfolio_data; from utils.portfolio_manager import PortfolioManager; update_portfolio_data(PortfolioManager().get_portfolio_symbols())"
elif [ "$1" = "help" ] || [ "$1" = "--help" ]; then
    echo "NLPStock Runner Script for macOS"
    echo "Usage: ./run.sh [command]"
    echo ""
    echo "Available commands:"
    echo "  app, streamlit  - Start the Streamlit web app"
    echo "  analyze         - Run the stock analyzer"
    echo "  fetch           - Fetch stock data for portfolio"
    echo "  help, --help    - Display this help message"
    echo ""
    echo "If no command is provided, the Streamlit app will be started."
else
    echo "Starting Streamlit app (default)..."
    streamlit run app.py
fi 