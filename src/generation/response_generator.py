#!/usr/bin/env python3
import json
import uuid
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Tuple, Optional

from ..utils.config import DEFAULT_S3_BUCKET, DEFAULT_MAX_WORKERS, DEFAULT_LAMBDA_FUNCTION_NAME, TMP_DIR
from ..utils.logging import get_logger, log_error
from ..data.storage import read_json_from_s3, write_json_to_s3

logger = get_logger()

def invoke_retrieval_lambda(question: str, session_id: str = "", 
                           lambda_function_name: Optional[str] = None) -> Tuple[str, str]:
    """
    Invoke the Lambda function to retrieve and generate an answer
    Returns:
        tuple: (raw_answer, extracted_answer)
    """
    try:
        import boto3
        lambda_client = boto3.client('lambda')
        user_id_int = int(time.time() * 1000)
        
        lambda_function_name = lambda_function_name or DEFAULT_LAMBDA_FUNCTION_NAME
        
        logger.info(f"Invoking {lambda_function_name} Lambda with question: {question}")
        
        payload = {
            "userId": user_id_int,
            "question": question,
            "sessionId": session_id
        }
        
        response = lambda_client.invoke(
            FunctionName=lambda_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        logger.debug(f"Lambda response metadata: {response}")
        raw_answer = response['Payload'].read().decode('utf-8')
        logger.debug(f"Payload content (raw): {raw_answer}")
        
        if "errorType" in raw_answer and "Sandbox.Timedout" in raw_answer:
            error_message = "The model took too long to respond (timeout after 30 seconds). re-run the script."
            logger.warning(f"Lambda timeout: {error_message}")
            return error_message, error_message
            
        extracted_answer = ""
        if raw_answer:
            if '<sessionId>' in raw_answer:
                extracted_answer = raw_answer.split('<sessionId>')[0].strip()
            else:
                extracted_answer = raw_answer.strip()
                
            if "errorType" in raw_answer and "errorMessage" in raw_answer:
                try:
                    error_data = json.loads(raw_answer)
                    if "errorMessage" in error_data:
                        error_message = f"Error: {error_data['errorMessage']}"
                        logger.warning(f"Lambda error: {error_message}")
                        return error_message, error_message
                except json.JSONDecodeError:
                    pass
        
        logger.debug(f"Payload content (extracted): {extracted_answer}")
        return raw_answer, extracted_answer
            
    except Exception as e:
        error_message = f"Error invoking Lambda: {str(e)}"
        log_error(error_message, e)
        return error_message, error_message


def process_input_json(bucket_name: str, input_json_key: str, 
                      max_workers: int = DEFAULT_MAX_WORKERS, 
                      lambda_function_name: Optional[str] = None) -> bool:
    """
    Reads an input JSON file, generates answers for each question, and stores the results.
    """
    try:
        import json
        import boto3
        
        logger.info(f"Reading input JSON from s3://{bucket_name}/{input_json_key}")
        
        input_data = read_json_from_s3(bucket_name, input_json_key)
        if not input_data:
            log_error(f"Failed to read input JSON from S3: {input_json_key}")
            return False
            
        if not input_data:
            logger.warning("Input JSON is empty")
            return True
        
        logger.info(f"Generating responses for {len(input_data)} questions with {max_workers} workers")
            
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            
            for i, item in enumerate(input_data):
                if 'Question' not in item:
                    logger.warning(f"Item {i} does not contain a 'Question' field, skipping")
                    continue
                    
                question = item['Question']
                future = executor.submit(invoke_retrieval_lambda, question, "", lambda_function_name)
                futures[future] = i
                
                time.sleep(10)
            

            for future in as_completed(futures):
                i = futures[future]
                try:
                    raw_answer, extracted_answer = future.result()
                    input_data[i]['Generated Answer'] = {
                        'raw_response': raw_answer,
                        'text_response': extracted_answer
                    }
                    logger.info(f"Generated answer for question {i+1}/{len(input_data)}")
                    

                except Exception as e:
                    log_error(f"Error processing item {i}", e)
                    
                    input_data[i]['Generated Answer'] = {
                        'raw_response': f"Error: {str(e)}",
                        'text_response': ""
                    }
        
        write_success = write_json_to_s3(bucket_name, input_json_key, input_data)
        if not write_success:
            log_error(f"Failed to write updated JSON to S3: {input_json_key}")
            return False
            
        logger.info(f"Successfully generated {len(futures)} responses")
        return True
    
        
    except Exception as e:
        log_error("Error in process_input_json", e)
        return False 