import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)

class PortfolioManager:
    """
    Manages user portfolios including add/remove stocks and persist data.
    """
    def __init__(self, storage_dir: str = "STOCK_DB/portfolios"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.default_portfolio_path = self.storage_dir / "default_portfolio.json"
        self._ensure_default_portfolio()
    
    def _ensure_default_portfolio(self):
        """Ensure the default portfolio file exists"""
        if not self.default_portfolio_path.exists():
            logger.info("Creating default portfolio")
            self.save_portfolio({"stocks": []}, "default_portfolio.json")
    
    def get_portfolio(self, name: str = "default_portfolio.json") -> Dict:
        """Get a portfolio by name"""
        portfolio_path = self.storage_dir / name
        
        if not portfolio_path.exists():
            logger.warning(f"Portfolio {name} not found, returning empty portfolio")
            return {"stocks": []}
        
        try:
            with open(portfolio_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading portfolio {name}: {e}")
            return {"stocks": []}
    
    def save_portfolio(self, portfolio: Dict, name: str = "default_portfolio.json") -> bool:
        """Save a portfolio to disk"""
        try:
            portfolio_path = self.storage_dir / name
            with open(portfolio_path, 'w') as f:
                json.dump(portfolio, f, indent=2)
            logger.info(f"Portfolio saved to {portfolio_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving portfolio {name}: {e}")
            return False
    
    def get_portfolio_symbols(self, name: str = "default_portfolio.json") -> List[str]:
        """Get a list of symbols in a portfolio"""
        portfolio = self.get_portfolio(name)
        return [stock["symbol"] for stock in portfolio.get("stocks", [])]
    
    def add_stock(self, symbol: str, name: str = "default_portfolio.json") -> bool:
        """Add a stock to a portfolio"""
        portfolio = self.get_portfolio(name)
        stocks = portfolio.get("stocks", [])
        
        # Check if stock already exists
        if any(stock["symbol"] == symbol for stock in stocks):
            logger.info(f"Stock {symbol} already in portfolio {name}")
            return False
        
        # Add the stock
        stocks.append({"symbol": symbol})
        portfolio["stocks"] = stocks
        
        # Save the updated portfolio
        return self.save_portfolio(portfolio, name)
    
    def remove_stock(self, symbol: str, name: str = "default_portfolio.json") -> bool:
        """Remove a stock from a portfolio"""
        portfolio = self.get_portfolio(name)
        stocks = portfolio.get("stocks", [])
        
        # Filter out the stock to remove
        updated_stocks = [stock for stock in stocks if stock["symbol"] != symbol]
        
        # If no stocks were removed, return False
        if len(updated_stocks) == len(stocks):
            logger.info(f"Stock {symbol} not found in portfolio {name}")
            return False
        
        portfolio["stocks"] = updated_stocks
        return self.save_portfolio(portfolio, name)
    
    def list_portfolios(self) -> List[str]:
        """List all available portfolios"""
        return [f.name for f in self.storage_dir.glob("*.json")]

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    manager = PortfolioManager()
    manager.add_stock("AAPL")
    manager.add_stock("MSFT")
    manager.add_stock("GOOGL")
    
    print(f"Portfolio symbols: {manager.get_portfolio_symbols()}")
    print(f"Available portfolios: {manager.list_portfolios()}") 