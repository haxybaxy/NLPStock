# NLPStock Makefile for macOS

# Define Python and pip executables
PYTHON := python3
PIP := pip3

# Virtual environment directory
VENV := venv

# Default target
.PHONY: all
all: setup run

# Setup virtual environment and install dependencies
.PHONY: setup
setup: $(VENV)/bin/activate create-dirs

$(VENV)/bin/activate:
	$(PYTHON) -m venv $(VENV)
	. $(VENV)/bin/activate && $(PIP) install -r requirements.txt
	. $(VENV)/bin/activate && $(PYTHON) -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
	@echo "Virtual environment created and dependencies installed"

# Create necessary directories
.PHONY: create-dirs
create-dirs:
	mkdir -p STOCK_DB/news
	mkdir -p STOCK_DB/prices
	mkdir -p STOCK_DB/portfolios
	mkdir -p STOCK_DB/analysis
	mkdir -p STOCK_DB/movers
	@echo "Directories created"

# Check if API key is set in .env
.PHONY: check-api-key
check-api-key:
	@if ! grep -q "GROQ_API_KEY" .env || grep -q "GROQ_API_KEY = \"\"" .env; then \
		echo "ERROR: GROQ_API_KEY not set in .env file"; \
		echo "Please add your Groq API key to the .env file"; \
		exit 1; \
	else \
		echo "API key found"; \
	fi

# Run the Streamlit app
.PHONY: run
run: check-api-key
	@echo "Starting Streamlit app..."
	. $(VENV)/bin/activate && PYTHONPATH=. streamlit run app.py

# Run the stock analyzer
.PHONY: analyze
analyze: check-api-key
	@echo "Running stock analyzer..."
	. $(VENV)/bin/activate && PYTHONPATH=. $(PYTHON) stock_analyzer.py

# Fetch stock data
.PHONY: fetch
fetch: check-api-key
	@echo "Fetching stock data..."
	. $(VENV)/bin/activate && PYTHONPATH=. $(PYTHON) fetch_data.py

# Add stock to the portfolio
.PHONY: add-stock
add-stock:
	@read -p "Enter stock symbol to add: " symbol; \
	echo "Adding $$symbol to portfolio..."; \
	. $(VENV)/bin/activate && PYTHONPATH=. $(PYTHON) add_stock.py $$symbol

# Initialize with some default stocks
.PHONY: init-portfolio
init-portfolio:
	@echo "Initializing portfolio with some default stocks..."
	. $(VENV)/bin/activate && PYTHONPATH=. $(PYTHON) init_portfolio.py

# Debug environment
.PHONY: debug
debug:
	@echo "Debugging environment..."
	. $(VENV)/bin/activate && PYTHONPATH=. $(PYTHON) -c "import sys; import os; print(f'Python version: {sys.version}'); print(f'PYTHONPATH: {os.environ.get(\"PYTHONPATH\", \"Not set\")}'); print('Checking imports:'); for module in ['pandas', 'nltk', 'streamlit', 'yfinance', 'groq']: try: exec(f'import {module}; print(f\"{module} version: {module.__version__}\")', globals()); except (ImportError, AttributeError) as e: print(f'{module}: Error - {e}')"

# Clean up
.PHONY: clean
clean:
	rm -rf $(VENV)
	rm -f *.log
	rm -f streamlit_app.log
	@echo "Cleaned up virtual environment and log files"

# Simple direct run without environment setup (for troubleshooting)
.PHONY: direct-run
direct-run:
	@echo "Starting Streamlit app directly (no environment setup)..."
	PYTHONPATH=. streamlit run app.py

# Help
.PHONY: help
help:
	@echo "NLPStock Makefile Usage for macOS:"
	@echo "  make setup          - Set up virtual environment and install dependencies"
	@echo "  make run            - Run the Streamlit app"
	@echo "  make analyze        - Run the stock analyzer"
	@echo "  make fetch          - Fetch stock data for portfolio"
	@echo "  make add-stock      - Add a stock to the portfolio"
	@echo "  make init-portfolio - Initialize portfolio with default stocks"
	@echo "  make debug          - Run diagnostics on the environment"
	@echo "  make direct-run     - Run Streamlit directly (troubleshooting)"
	@echo "  make clean          - Clean up virtual environment and log files"
	@echo "  make help           - Display this help message" 