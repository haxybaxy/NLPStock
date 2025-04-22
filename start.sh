#!/bin/bash

# Simple startup script for NLPStock

# Activate the virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Make sure we have the right packages
pip install streamlit yfinance pandas nltk groq python-dotenv

# Start the Streamlit app
echo "Starting NLPStock Streamlit app..."
streamlit run app.py 