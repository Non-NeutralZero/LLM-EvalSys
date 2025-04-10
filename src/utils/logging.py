#!/usr/bin/env python3
import logging
import sys
import os
from datetime import datetime


logger = logging.getLogger('llm_evaluation')
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)

def get_logger():
    """Get the application logger"""
    return logger

def log_section(title):
    logger.info(f"\n{'#'*5} {title} {'#'*5}")

def log_error(message, exception=None):
    logger.error(message)
    if exception:
        logger.error(f"Exception details: {str(exception)}")
        import traceback
        logger.error(traceback.format_exc())

def log_success(message):
    logger.info(f"SUCCESS: {message}") 