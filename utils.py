"""
Utility functions for the Legal Judgments Similarity Retrieval System.
Provides logging, text formatting, and common helper functions used across modules.
"""

import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import config

def setup_logging() -> logging.Logger:
    """
    Set up logging configuration for the application.
    Returns a configured logger instance.
    """
    # Create logger
    logger = logging.getLogger('legal_rag')
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Avoid duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger

def format_preview(text: str, max_length: Optional[int] = None) -> str:
    """
    Format text for preview display by truncating and cleaning.
    
    Args:
        text: The text to format
        max_length: Maximum length of preview (uses config default if None)
    
    Returns:
        Formatted preview text
    """
    if max_length is None:
        max_length = config.PREVIEW_LENGTH
    
    # Clean up whitespace and newlines
    clean_text = ' '.join(text.split())
    
    # Truncate if too long
    if len(clean_text) > max_length:
        clean_text = clean_text[:max_length] + "..."
    
    return clean_text

def print_results_table(results: List[Dict[str, Any]]) -> None:
    """
    Print retrieval results in a formatted table.
    
    Args:
        results: List of result dictionaries containing rank, filename, score, preview
    """
    if not results:
        print("No results found.")
        return
    
    # Print header
    print("\n" + "="*100)
    print(f"{'Rank':<6} | {'Filename':<30} | {'Score':<8} | {'Preview':<50}")
    print("="*100)
    
    # Print each result
    for result in results:
        rank = result.get('rank', 'N/A')
        filename = result.get('filename', 'Unknown')[:28]  # Truncate long filenames
        score = f"{result.get('score', 0):.4f}"
        preview = result.get('preview', 'No preview available')[:48]
        
        print(f"{rank:<6} | {filename:<30} | {score:<8} | {preview:<50}")
    
    print("="*100)

def validate_file_size(file_path: Path) -> bool:
    """
    Check if file size is within acceptable limits.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if file size is acceptable, False otherwise
    """
    try:
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        return file_size_mb <= config.MAX_FILE_SIZE_MB
    except Exception:
        return False

def get_file_list(directory: Path, extensions: List[str]) -> List[Path]:
    """
    Get list of files with specified extensions from directory.
    
    Args:
        directory: Directory to search
        extensions: List of file extensions to include (e.g., ['.pdf', '.txt'])
        
    Returns:
        List of Path objects for matching files
    """
    files = []
    
    if not directory.exists():
        return files
    
    for ext in extensions:
        # Use glob to find files with the extension (case insensitive)
        files.extend(directory.glob(f"*{ext}"))
        files.extend(directory.glob(f"*{ext.upper()}"))
    
    # Filter by file size
    valid_files = [f for f in files if validate_file_size(f)]
    
    return sorted(valid_files)

def safe_filename(filename: str) -> str:
    """
    Clean filename for safe storage and display.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Remove path separators and clean up the name
    safe_name = Path(filename).name
    return safe_name

def print_banner():
    """Print welcome banner for the application."""
    banner = """
    ╔════════════════════════════════════════════════════════════════╗
    ║              Legal Judgments Similarity Retrieval System       ║
    ║                    Powered by BGE Embeddings & ChromaDB       ║
    ╚════════════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_separator(char="─", length=80):
    """Print a separator line."""
    print(char * length)