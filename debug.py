#!/usr/bin/env python3
"""
Diagnostic script to check environment and imports.
"""
import sys
import os
import importlib
from pathlib import Path

# Add project root to path
script_dir = Path(__file__).resolve().parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

def check_module(module_name):
    """Check if a module can be imported and get its version if available"""
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", "unknown")
        return f"{module_name}: OK (version {version})"
    except ImportError as e:
        return f"{module_name}: FAILED - {str(e)}"
    except Exception as e:
        return f"{module_name}: ERROR - {str(e)}"

def run_diagnostics():
    """Run system diagnostics and print results"""
    print("\n===== NLPStock Diagnostics =====\n")
    
    # System information
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    
    # Check directories
    print("\n----- Directory Structure -----")
    required_dirs = [
        "STOCK_DB",
        "STOCK_DB/news",
        "STOCK_DB/prices",
        "STOCK_DB/portfolios",
        "STOCK_DB/analysis",
        "STOCK_DB/movers",
        "data_fetchers",
        "nlp_processing",
        "summarization",
        "utils"
    ]
    
    for dir_name in required_dirs:
        path = Path(dir_name)
        if path.exists() and path.is_dir():
            print(f"{dir_name}: OK")
        else:
            print(f"{dir_name}: MISSING")
    
    # Check key files
    print("\n----- Key Files -----")
    key_files = [
        ".env",
        "app.py",
        "stock_analyzer.py",
        "requirements.txt",
        "setup_paths.py",
        "utils/portfolio_manager.py",
        "data_fetchers/stock_price_fetcher.py",
        "summarization/llm_client.py",
        "summarization/why_it_moves.py"
    ]
    
    for file_name in key_files:
        path = Path(file_name)
        if path.exists() and path.is_file():
            print(f"{file_name}: OK")
        else:
            print(f"{file_name}: MISSING")
    
    # Check package imports
    print("\n----- Package Imports -----")
    packages = [
        "pandas",
        "numpy",
        "nltk",
        "streamlit",
        "yfinance",
        "groq",
        "dotenv",
        "requests",
        "bs4"  # BeautifulSoup
    ]
    
    for package in packages:
        print(check_module(package))
    
    # Check project modules
    print("\n----- Project Module Imports -----")
    try:
        from utils.portfolio_manager import PortfolioManager
        print("utils.portfolio_manager: OK")
    except Exception as e:
        print(f"utils.portfolio_manager: FAILED - {e}")
    
    try:
        from data_fetchers.stock_price_fetcher import update_portfolio_data
        print("data_fetchers.stock_price_fetcher: OK")
    except Exception as e:
        print(f"data_fetchers.stock_price_fetcher: FAILED - {e}")
    
    try:
        from summarization.llm_client import LLMClient
        print("summarization.llm_client: OK")
    except Exception as e:
        print(f"summarization.llm_client: FAILED - {e}")
    
    # Check Groq API key
    print("\n----- API Key Check -----")
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GROQ_API_KEY", "")
    if api_key and api_key != "":
        print("GROQ_API_KEY: SET")
    else:
        print("GROQ_API_KEY: NOT SET - Add your API key to the .env file")
    
    print("\n===== End of Diagnostics =====\n")

if __name__ == "__main__":
    run_diagnostics() 