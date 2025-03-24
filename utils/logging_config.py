import logging
import sys
from pathlib import Path

def setup_logging(log_file='nlpstock.log', console_level=logging.INFO, file_level=logging.DEBUG):
    """Set up logging configuration for the application."""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,  # Capture all levels
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific levels for handlers
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setLevel(console_level)
        elif isinstance(handler, logging.FileHandler):
            handler.setLevel(file_level)
    
    return logging.getLogger()

def get_logger(name):
    """Get a logger with the specified name."""
    return logging.getLogger(name) 