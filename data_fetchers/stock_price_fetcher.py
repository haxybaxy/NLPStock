import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Union, Optional
import json
import numpy as np

logger = logging.getLogger(__name__)

# Custom JSON encoder to handle pandas Timestamp objects and numpy types
class PandasJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        return super().default(obj)

def fetch_stock_data(symbols: List[str], period: str = "1d", interval: str = "1d") -> Dict[str, pd.DataFrame]:
    """
    Fetch stock data for a list of symbols using yfinance.
    
    Args:
        symbols: List of stock symbols
        period: Time period to fetch (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
    
    Returns:
        Dictionary with symbols as keys and dataframes as values
    """
    results = {}
    
    for symbol in symbols:
        try:
            logger.info(f"Fetching data for {symbol} - period: {period}, interval: {interval}")
            data = yf.download(symbol, period=period, interval=interval, progress=False)
            
            if data.empty:
                logger.warning(f"No data returned for {symbol}")
                continue
                
            results[symbol] = data
            logger.info(f"Successfully fetched data for {symbol}: {len(data)} rows")
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
    
    return results

def get_moving_stocks(symbols: List[str], threshold: float = 2.0) -> Dict[str, Dict]:
    """
    Identify stocks that have moved beyond a certain percentage threshold in the last day.
    
    Args:
        symbols: List of stock symbols to check
        threshold: Percentage threshold (absolute value) to consider a stock as "moving"
    
    Returns:
        Dictionary of moving stocks with percentage changes
    """
    stock_data = fetch_stock_data(symbols, period="2d", interval="1d")
    moving_stocks = {}
    
    for symbol, data in stock_data.items():
        if len(data) >= 2:  # Need at least 2 days to calculate a change
            # Calculate percentage change from previous close to latest close
            prev_close = float(data['Close'].iloc[-2])
            current_close = float(data['Close'].iloc[-1])
            
            # Use scalar values, not pandas Series
            pct_change = ((current_close - prev_close) / prev_close) * 100
            
            if abs(pct_change) >= threshold:
                moving_stocks[symbol] = {
                    "symbol": symbol,
                    "price": current_close, 
                    "change_pct": pct_change,
                    "direction": "up" if pct_change > 0 else "down",
                    "date": data.index[-1].strftime("%Y-%m-%d")
                }
                logger.info(f"{symbol} moved {pct_change:.2f}% - added to moving stocks")
    
    return moving_stocks

def get_stock_info(symbol: str) -> Dict:
    """
    Get detailed information about a specific stock.
    
    Args:
        symbol: Stock symbol
    
    Returns:
        Dictionary containing stock information
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Extract the most important information
        stock_info = {
            "symbol": symbol,
            "name": info.get("shortName", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "country": info.get("country", ""),
            "exchange": info.get("exchange", ""),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", 0),
            "dividend_yield": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0,
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow", 0),
        }
        
        # Convert any numpy values to native Python types
        for key, value in stock_info.items():
            if isinstance(value, (np.integer, np.floating)):
                stock_info[key] = float(value) if isinstance(value, np.floating) else int(value)
        
        return stock_info
    except Exception as e:
        logger.error(f"Error fetching info for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}

def make_json_serializable(obj):
    """
    Recursively convert a nested structure of dictionaries and lists to be JSON serializable.
    Handles pandas Timestamps, numpy types, and other non-serializable objects.
    """
    if isinstance(obj, dict):
        return {make_json_serializable(k): make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return str(obj)  # Convert tuples to strings
    elif isinstance(obj, pd.Timestamp):
        return obj.strftime('%Y-%m-%d')
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    else:
        return obj

def save_stock_data(data: Dict, filename: str):
    """Save stock data to a JSON file with custom encoder for pandas objects"""
    output_dir = Path("STOCK_DB/prices")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / filename
    
    # Convert to JSON serializable format
    processed_data = make_json_serializable(data)
    
    try:
        with open(output_path, 'w') as f:
            json.dump(processed_data, f, indent=2)
        logger.info(f"Stock data saved to {output_path}")
    except TypeError as e:
        logger.error(f"JSON serialization error: {e}")
        # Fallback to a simpler format
        simple_data = {}
        for symbol, stock_data in data.items():
            simple_data[symbol] = {
                "info": {
                    "symbol": symbol,
                    "name": stock_data.get("info", {}).get("name", ""),
                    "price": float(stock_data.get("info", {}).get("price", 0))
                },
                "last_updated": datetime.now().isoformat()
            }
        with open(output_path, 'w') as f:
            json.dump(simple_data, f, indent=2)
        logger.info(f"Simplified stock data saved to {output_path}")

def update_portfolio_data(symbols: List[str]):
    """Update data for all stocks in a portfolio"""
    # Fetch daily data for all symbols
    daily_data = fetch_stock_data(symbols, period="1mo", interval="1d")
    
    # Process and save the data
    processed_data = {}
    for symbol, data in daily_data.items():
        if not data.empty:
            try:
                # Convert to simple dictionary with string dates
                prices = {}
                for i in range(min(30, len(data))):
                    idx = data.index[-(i+1)]
                    date_str = idx.strftime('%Y-%m-%d')
                    row_dict = {}
                    for col in data.columns:
                        val = data[col].iloc[-(i+1)]
                        # Convert numpy values to native Python types
                        if isinstance(val, (np.integer, np.floating)):
                            row_dict[col] = float(val)
                        else:
                            row_dict[col] = val
                    prices[date_str] = row_dict
                
                processed_data[symbol] = {
                    "prices": prices,
                    "info": get_stock_info(symbol),
                    "last_updated": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Error processing data for {symbol}: {e}")
    
    # Save the data
    save_stock_data(processed_data, "portfolio_data.json")
    return processed_data

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    portfolio = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    update_portfolio_data(portfolio)
    moving = get_moving_stocks(portfolio)
    print(f"Moving stocks: {moving}") 