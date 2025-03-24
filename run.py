#!/usr/bin/env python3
import sys
import os
import argparse
import logging

# Initialize paths
import init_paths

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

def main():
    """Main entry point for the NLPStock application."""
    logger.info("Starting NLPStock application")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='NLPStock - Stock News Analysis')
    parser.add_argument('--symbol', type=str, help='Stock symbol to analyze')
    parser.add_argument('--exchange', type=str, default='US', help='Stock exchange (default: US)')
    parser.add_argument('--change', type=float, default=0.01, help='Daily change percentage (default: 0.01)')
    parser.add_argument('--all', action='store_true', help='Process all stocks with news data')
    parser.add_argument('--fetch-news', action='store_true', help='Fetch news before analysis')
    parser.add_argument('--symbols-file', type=str, help='Path to a file containing symbols to fetch news for')
    parser.add_argument('--exchanges-file', type=str, help='Path to a file containing exchanges for the symbols')
    
    args = parser.parse_args()
    
    # Fetch news if requested
    if args.fetch_news or args.symbols_file:
        from NLPStock.data_fetchers.combined_news_fetcher import fetch_all_news_for_symbol, fetch_news_from_file
        
        if args.symbols_file:
            # Fetch news for symbols from file
            fetch_news_from_file(args.symbols_file, args.exchanges_file)
        elif args.symbol:
            # Fetch news for a single symbol
            logger.info(f"Fetching news for {args.symbol} on {args.exchange}")
            fetch_all_news_for_symbol(args.symbol, args.exchange)
    
    # Import here to avoid circular imports
    from NLPStock.summarization.why_it_moves_simple import why_it_moves, process_all_stocks
    
    # Process stocks
    if args.all:
        logger.info("Processing all stocks with news data")
        process_all_stocks()
    elif args.symbol:
        logger.info(f"Processing single stock: {args.symbol} on {args.exchange} with change {args.change}%")
        summary = why_it_moves(args.symbol, args.exchange, args.change)
        print(f"\n{args.symbol} ({args.exchange}) - Change: {args.change:.2f}%")
        print(f"Classification: {summary['type']}")
        print(f"Summary: {summary['summary']}\n")
    else:
        parser.print_help()
        logger.info("No action specified, exiting")

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