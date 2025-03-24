import json
import csv
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def ensure_directory(directory_path):
    """Ensure that a directory exists, creating it if necessary."""
    Path(directory_path).mkdir(parents=True, exist_ok=True)
    return directory_path

def save_json(data, filepath):
    """Save data to a JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug(f"Data saved to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving data to {filepath}: {e}")
        return False

def load_json(filepath):
    """Load data from a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.debug(f"Data loaded from {filepath}")
        return data
    except FileNotFoundError:
        logger.warning(f"File not found: {filepath}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {filepath}")
        return None
    except Exception as e:
        logger.error(f"Error loading data from {filepath}: {e}")
        return None

def save_csv(data, filepath, fieldnames=None):
    """Save data to a CSV file."""
    try:
        if not fieldnames and data:
            fieldnames = data[0].keys()
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        logger.debug(f"Data saved to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving data to {filepath}: {e}")
        return False

def load_csv(filepath):
    """Load data from a CSV file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = list(reader)
        
        logger.debug(f"Data loaded from {filepath}")
        return data
    except FileNotFoundError:
        logger.warning(f"File not found: {filepath}")
        return None
    except Exception as e:
        logger.error(f"Error loading data from {filepath}: {e}")
        return None 