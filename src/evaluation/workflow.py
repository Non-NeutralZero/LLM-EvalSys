#!/usr/bin/env python3
import os
import time
import argparse
import sys
from typing import List, Optional

from ..utils.config import DEFAULT_S3_BUCKET, DEFAULT_MAX_WORKERS, DEFAULT_LAMBDA_FUNCTION_NAME, TMP_DIR
from ..utils.logging import get_logger, log_section, log_error, log_success
from ..data.excel_processor import convert_excel_to_json
from ..data.storage import get_output_json_path
from ..generation.response_generator import process_input_json
from ..evaluation.json_validator import process_json_data

logger = get_logger()

def generate_model_responses(bucket_name: str, input_json_key: str, 
                             max_workers: int = DEFAULT_MAX_WORKERS, 
                             lambda_function_name: Optional[str] = None) -> bool:
    """
    Generate model responses for each question in the input JSON
    
    Args:
        bucket_name (str): S3 bucket name
        input_json_key (str): S3 key for the input JSON file
        max_workers (int): Maximum number of concurrent workers
        lambda_function_name (str): Name of Lambda function to invoke for response generation
        
    Returns:
        bool: True if successful
    """
    try:
        log_section("GENERATING MODEL RESPONSES")
        
        success = process_input_json(bucket_name, input_json_key, max_workers, lambda_function_name)
        if not success:
            log_error("Failed to generate model responses")
            return False
            
        log_success("Generated model responses")
        return True
    
    except Exception as e:
        log_error("Error in generate_model_responses", e)
        return False

def evaluate_model_responses(bucket_name: str, input_json_key: str) -> bool:
    """

    Evaluate model responses against provided expected answers
    
    Args:
        input_json_key (str): S3 key for the input JSON file
    """
    try:
        log_section("EVALUATING MODEL RESPONSES")
        
        output_json_key = get_output_json_path(input_json_key)
        
        os.makedirs(TMP_DIR, exist_ok=True)
        local_path = f"{TMP_DIR}/{os.path.basename(output_json_key)}"
        
        success = process_json_data(input_json_key, local_path, bucket_name)
        if not success:
            log_error("Failed to evaluate model responses")
            return False
            
        log_success("Evaluated model responses")
        return True
    
    except Exception as e:
        log_error("Error in evaluate_model_responses", e)
        return False

def run_etl_workflow(bucket_name: str, file_key: str, 
                     max_workers: int = DEFAULT_MAX_WORKERS, 
                     skip_steps: Optional[List[int]] = None, 
                     lambda_function_name: Optional[str] = None) -> bool:
    """
    Run the full ETL workflow starting from the Excel file initially provided by product team
    Returns:
        bool: True if successful
    """
    if skip_steps is None:
        skip_steps = []
    
    try:
        log_section("STARTING ETL WORKFLOW")
        logger.info(f"Processing file: s3://{bucket_name}/{file_key}")
        start_time = time.time()
        
        os.makedirs(TMP_DIR, exist_ok=True)
        
        if 1 not in skip_steps:
            log_section("1: CONVERTING EXCEL TO JSON")
            success = convert_excel_to_json(bucket_name, file_key)
            if not success:
                log_error("Failed to convert Excel to JSON")
                return False

        input_json_key = file_key.replace('.xlsx', '_input.json').replace('.xls', '_input.json')
        if not input_json_key.endswith('_input.json'):
            input_json_key = f"{os.path.splitext(file_key)[0]}_input.json"
        
        if 2 not in skip_steps:
            success = generate_model_responses(bucket_name, input_json_key, max_workers, lambda_function_name)
            if not success:
                return False
        
        if 3 not in skip_steps:
            success = evaluate_model_responses(bucket_name, input_json_key)
            if not success:
                return False
        
        total_time = time.time() - start_time
        log_section("WORKFLOW COMPLETED")
        logger.info(f"ETL workflow finished in {total_time:.2f} seconds")
        
        # output paths
        output_json_key = get_output_json_path(input_json_key)
        logger.info(f"\nOutput files:")
        logger.info(f"- Input JSON: s3://{bucket_name}/{input_json_key}")
        logger.info(f"- Output JSON with evaluations: s3://{bucket_name}/{output_json_key}")
        
        return True
    
    except Exception as e:
        log_error("ETL workflow failed", e)
        return False

def main():
    """
    ETL workflow command line tool
    """
    parser = argparse.ArgumentParser(description="LLM Evaluation ETL Workflow")
    parser.add_argument("file_key", help="S3 key for the input file (Excel or JSON)")
    parser.add_argument("--bucket", default=DEFAULT_S3_BUCKET, help="S3 bucket name")
    parser.add_argument("--workers", type=int, default=DEFAULT_MAX_WORKERS, help="Maximum number of concurrent workers")
    parser.add_argument("--skip", type=int, nargs="+", help="Steps to skip (1=excel conversion, 2=generation, 3=evaluation)")
    parser.add_argument("--lambda-function", default=DEFAULT_LAMBDA_FUNCTION_NAME, 
                       help="Name of the Lambda function to invoke for response generation")
    
    args = parser.parse_args()
    
    success = run_etl_workflow(args.bucket, args.file_key, args.workers, args.skip, args.lambda_function)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 