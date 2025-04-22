#!/usr/bin/env python3
"""
This script configures Python's import system to ensure all NLPStock modules can be imported correctly.
"""

import os
import sys
import site
from pathlib import Path

def setup_paths():
    """
    Configure Python path to ensure all project modules can be imported.
    This helps resolve common import errors in the project.
    """
    # Get the project root directory (one level up from this script)
    project_root = Path(__file__).resolve().parent
    
    # Add the project root to Python's path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Add key subdirectories
    subdirs = [
        "data_fetchers",
        "nlp_processing",
        "summarization",
        "utils"
    ]
    
    for subdir in subdirs:
        subdir_path = project_root / subdir
        if subdir_path.exists() and str(subdir_path) not in sys.path:
            sys.path.insert(0, str(subdir_path))
    
    # Print the updated path for debugging
    print(f"Python path configured. Current sys.path:")
    for p in sys.path:
        print(f"  - {p}")
    
    return True

# Execute the function if this script is run directly
if __name__ == "__main__":
    setup_paths() 