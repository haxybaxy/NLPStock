#!/usr/bin/env python3
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime

# Initialize paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nlpstock.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from data_fetchers.stock_price_fetcher import update_portfolio_data, get_moving_stocks
from utils.portfolio_manager import PortfolioManager
from summarization.why_it_moves_simple import why_it_moves

class StockAnalyzer:
    """
    Combines portfolio tracking, data fetching, and analysis for stocks.
    """
    def __init__(self):
        self.portfolio_manager = PortfolioManager()
        self.output_dir = Path("STOCK_DB/analysis")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def update_portfolio_stocks(self, portfolio_name: str = "default_portfolio.json") -> Dict:
        """Update stock data for a portfolio"""
        symbols = self.portfolio_manager.get_portfolio_symbols(portfolio_name)
        
        if not symbols:
            logger.warning(f"Portfolio {portfolio_name} is empty")
            return {}
        
        logger.info(f"Updating data for {len(symbols)} stocks in portfolio {portfolio_name}")
        return update_portfolio_data(symbols)
    
    def find_moving_stocks(self, portfolio_name: str = "default_portfolio.json", threshold: float = 2.0) -> Dict:
        """Find stocks with significant price movements"""
        symbols = self.portfolio_manager.get_portfolio_symbols(portfolio_name)
        
        if not symbols:
            logger.warning(f"Portfolio {portfolio_name} is empty")
            return {}
        
        logger.info(f"Finding stocks with movements >= {threshold}% in portfolio {portfolio_name}")
        return get_moving_stocks(symbols, threshold)
    
    def analyze_moving_stocks(self, portfolio_name: str = "default_portfolio.json", threshold: float = 2.0) -> List[Dict]:
        """Analyze why stocks are moving and generate summaries"""
        moving_stocks = self.find_moving_stocks(portfolio_name, threshold)
        
        if not moving_stocks:
            logger.info(f"No stocks with movements >= {threshold}% found in portfolio {portfolio_name}")
            return []
        
        results = []
        for symbol, stock_data in moving_stocks.items():
            logger.info(f"Analyzing movement for {symbol}: {stock_data['change_pct']:.2f}%")
            
            # Get exchange from stock data or default to NASDAQ
            exchange = stock_data.get("exchange", "NASDAQ")
            
            # Generate the "why it moves" analysis
            try:
                summary = why_it_moves(symbol, exchange, stock_data["change_pct"])
                results.append(summary)
                
                # Save individual summary
                self._save_analysis(summary, f"{symbol}_analysis.json")
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
        
        return results
    
    def _save_analysis(self, analysis: Dict, filename: str) -> None:
        """Save analysis results to a file"""
        output_path = self.output_dir / filename
        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        logger.info(f"Analysis saved to {output_path}")
    
    def get_latest_analysis(self, symbol: str) -> Optional[Dict]:
        """Get the latest analysis for a symbol"""
        analysis_path = self.output_dir / f"{symbol}_analysis.json"
        
        if not analysis_path.exists():
            logger.warning(f"No analysis found for {symbol}")
            return None
        
        try:
            with open(analysis_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading analysis for {symbol}: {e}")
            return None

def main():
    """Main entry point for the stock analyzer"""
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables
    
    analyzer = StockAnalyzer()
    portfolio_name = "default_portfolio.json"
    threshold = 2.0
    
    # Update portfolio data
    analyzer.update_portfolio_stocks(portfolio_name)
    
    # Find and analyze moving stocks
    results = analyzer.analyze_moving_stocks(portfolio_name, threshold)
    
    if results:
        print(f"\nAnalyzed {len(results)} moving stocks:")
        for result in results:
            symbol = result["symbol"]
            summary = result["summary"]
            print(f"\n{symbol} - {result.get('daily_change_percentage', 0):.2f}%")
            print(f"Summary: {summary}")
    else:
        print("\nNo moving stocks found for analysis.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        logger.exception("Exception occurred")
        sys.exit(1) 