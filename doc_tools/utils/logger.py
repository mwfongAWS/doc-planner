"""Logging utilities."""

import logging
import sys
from pathlib import Path
from typing import Optional

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a logger with the specified name and level.
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure logger if it hasn't been configured yet
    if not logger.handlers:
        logger.setLevel(level)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
    
    return logger

def setup_file_logging(log_dir: Optional[Path] = None) -> None:
    """Set up file logging.
    
    Args:
        log_dir: Log directory
    """
    if log_dir is None:
        log_dir = Path.home() / ".aws-doc-tools" / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "aws-doc-tools.log"
    
    # Configure root logger
    root_logger = logging.getLogger()
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(file_handler)