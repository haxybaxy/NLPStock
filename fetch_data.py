#!/usr/bin/env python3
"""
Fetch data for all stocks in the portfolio.
"""
import os
import sys
from pathlib import Path

# Add project root to path
script_dir = Path(__file__).resolve().parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

# Import required modules
from utils.portfolio_manager import PortfolioManager
from data_fetchers.stock_price_fetcher import update_portfolio_data

def fetch_portfolio_data():
    """Fetch data for all stocks in the portfolio"""
    portfolio_manager = PortfolioManager()
    symbols = portfolio_manager.get_portfolio_symbols()
    
    if not symbols:
        print("Portfolio is empty. Add some stocks first.")
        return False
    
    print(f"Fetching data for symbols: {symbols}")
    results = update_portfolio_data(symbols)
    
    if results:
        print(f"Successfully fetched data for {len(results)} stocks")
        return True
    else:
        print("No data fetched")
        return False

if __name__ == "__main__":
    fetch_portfolio_data() 