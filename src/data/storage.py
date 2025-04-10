#!/usr/bin/env python3
import json
import os
import boto3
from typing import Dict, List, Any, Union, Optional

from ..utils.config import TMP_DIR
from ..utils.logging import get_logger, log_error

logger = get_logger()

def get_s3_client():
    return boto3.client('s3')

def read_json_from_s3(bucket_name: str, key: str, s3_client=None) -> Optional[List[Dict[str, Any]]]:
    try:
        if s3_client is None:
            s3_client = get_s3_client()
            
        logger.info(f"Reading JSON from s3://{bucket_name}/{key}")
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        data = json.loads(response['Body'].read().decode('utf-8'))
        
        logger.info(f"Loaded {len(data) if isinstance(data, list) else 'non-list'} JSON data from S3")
        return data
        
    except Exception as e:
        log_error(f"Error reading JSON from S3: {key}", e)
        return None

def write_json_to_s3(bucket_name: str, key: str, data: Union[List, Dict], 
                     save_local: bool = True, s3_client=None) -> bool:
    try:
        if s3_client is None:
            s3_client = get_s3_client()
            
        json_data = json.dumps(data, indent=4, ensure_ascii=False, default=str)
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=json_data.encode('utf-8'),
            ContentType='application/json; charset=utf-8'
        )
        
        logger.info(f"JSON data written to s3://{bucket_name}/{key}")
        
        # save local copy
        if save_local:
            os.makedirs(TMP_DIR, exist_ok=True)
            local_path = f"{TMP_DIR}/{os.path.basename(key)}"
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(json_data)
            logger.info(f"Local copy saved to {local_path}")
        
        return True
        
    except Exception as e:
        log_error(f"Error writing JSON to S3: {key}", e)
        return False

def get_output_json_path(input_json_key: str) -> str:
    return input_json_key.replace("_input.json", "_output.json") 