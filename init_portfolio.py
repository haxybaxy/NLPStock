#!/usr/bin/env python3
"""
Initialize the default portfolio with some common stock symbols.
"""
import os
import sys
from pathlib import Path

# Add project root to path
script_dir = Path(__file__).resolve().parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

# Import the portfolio manager
from utils.portfolio_manager import PortfolioManager

def initialize_portfolio():
    """Initialize the portfolio with default stocks"""
    portfolio_manager = PortfolioManager()
    
    # Default stocks to add
    default_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
    
    # Add each stock
    for symbol in default_stocks:
        portfolio_manager.add_stock(symbol)
    
    # Print the result
    symbols = portfolio_manager.get_portfolio_symbols()
    print(f"Portfolio initialized with default stocks: {symbols}")
    
    return len(symbols)

if __name__ == "__main__":
    initialize_portfolio() 