#!/usr/bin/env python3
"""
Add a stock to the portfolio.
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

def add_stock(symbol):
    """Add a stock to the portfolio"""
    if not symbol:
        print("Error: No symbol provided")
        return False
        
    portfolio_manager = PortfolioManager()
    result = portfolio_manager.add_stock(symbol)
    
    if result:
        print(f"Added {symbol} to portfolio")
    else:
        print(f"{symbol} is already in portfolio")
    
    # Print current portfolio
    symbols = portfolio_manager.get_portfolio_symbols()
    print(f"Current portfolio: {symbols}")
    
    return result

if __name__ == "__main__":
    if len(sys.argv) > 1:
        symbol = sys.argv[1].upper()
        add_stock(symbol)
    else:
        print("Usage: python add_stock.py SYMBOL")
        print("Example: python add_stock.py AAPL") 