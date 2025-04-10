#!/usr/bin/env python3
import json
import os
import io
import traceback
import pandas as pd
import numpy as np

from ..utils.config import DEFAULT_S3_BUCKET, TMP_DIR
from ..utils.logging import get_logger, log_error, log_success

logger = get_logger()

def convert_excel_to_json(bucket_name, file_key, sheet_name=0, s3_client=None):
    """
    Convert Excel file from S3 to JSON format
    
    Args:
        bucket_name (str): S3 bucket name
        file_key (str): S3 key for the Excel file
        sheet_name (int or str): Sheet name or index to read (default: 0)
        s3_client: Boto3 S3 client
    Returns:
        bool: True if successful
    """
    try:
        if s3_client is None:
            import boto3
            s3_client = boto3.client('s3')
        
        logger.info(f"Reading Excel file from s3://{bucket_name}/{file_key}")
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        
        excel_content = response['Body'].read()
        df = pd.read_excel(io.BytesIO(excel_content), sheet_name=sheet_name)
        
        if df.empty:
            logger.warning("Excel file has no data")
            data = []
        else:
            df.columns = [str(col).strip() for col in df.columns]
            df = df.replace({np.nan: None})
            
            def clean_value(val):
                if pd.isna(val):
                    return None
                if isinstance(val, (int, float)):
                    return val
                if isinstance(val, str):
                    return val.strip().replace('\r\n', '\n')
                return val
                
            for col in df.columns:
                df[col] = df[col].apply(clean_value)
            
            data = df.to_dict(orient='records')
        
        base, _ = os.path.splitext(file_key)
        output_key = f"{base}_input.json"
        json_data = json.dumps(data, indent=4, default=str, ensure_ascii=False)
        
        try:
            json.loads(json_data)
            logger.info("JSON validation successful")
        except json.JSONDecodeError as e:
            log_error(f"Generated invalid JSON: {str(e)}")
            error_pos = e.pos
            context_start = max(0, error_pos - 50)
            context_end = min(len(json_data), error_pos + 50)
            logger.error(f"Error context: {json_data[context_start:context_end]}")
            return False
   

        s3_client.put_object(
            Bucket=bucket_name,
            Key=output_key,
            Body=json_data.encode('utf-8'),  
            ContentType='application/json; charset=utf-8'
        )
        
        logger.info(f"Successfully converted Excel to JSON with {len(data)} records")
        logger.info(f"JSON data written to s3://{bucket_name}/{output_key}")

        os.makedirs(TMP_DIR, exist_ok=True)
        local_path = f"{TMP_DIR}/{os.path.basename(output_key)}"
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(json_data)
        logger.info(f"Local copy saved to {local_path}")
        
        return True
        
    except Exception as e:
        log_error("Error converting Excel to JSON", e)
        return False

def create_output_jsons(bucket_name, s3_client=None):
    """
    Create empty output JSON files for all input JSON files in the bucket
    
    Args:
        bucket_name S3 bucket name
        s3_client: Boto3 S3 client (optional)
        
    Returns:
        bool: True if successful
    """
    try:
        if s3_client is None:
            import boto3
            s3_client = boto3.client('s3')
        
        logger.info(f"Listing all JSON files in s3://{bucket_name}")
        
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)
        
        count = 0
        for page in pages:
            if 'Contents' not in page:
                continue
            for obj in page['Contents']:
                key = obj['Key']
                if key.endswith('_input.json'):
                    output_key = key.replace('_input.json', '_output.json')
                    
                    empty_json = json.dumps([], indent=4, ensure_ascii=False)
                    
                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=output_key,
                        Body=empty_json.encode('utf-8'),
                        ContentType='application/json; charset=utf-8'
                    )
                    
                    logger.info(f"Created empty output JSON: s3://{bucket_name}/{output_key}")
                    count += 1
        
        logger.info(f"Created {count} empty output JSON files")
        return True
    
    except Exception as e:
        log_error("Error creating output JSONs", e)
        return False 
