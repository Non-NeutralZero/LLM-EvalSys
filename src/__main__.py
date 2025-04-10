#!/usr/bin/env python3
"""
LLM Evaluation Workflow main entry point.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.evaluation.workflow import main
if __name__ == "__main__":
    sys.exit(main()) 