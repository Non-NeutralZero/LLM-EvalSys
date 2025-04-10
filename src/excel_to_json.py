#!/usr/bin/env python3
import json
import os
import sys
import io
import boto3
import pandas as pd
import numpy as np
import traceback


def excel_to_json(bucket_name, file_key, sheet_name=0):
    try:
        s3 = boto3.client('s3')
        
        print(f"Reading Excel file from s3://{bucket_name}/{file_key}")
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        
        excel_content = response['Body'].read()
        df = pd.read_excel(io.BytesIO(excel_content), sheet_name=sheet_name)
        
        if df.empty:
            print("Warning: Excel file has no data")
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
            print("JSON validation successful")
        except json.JSONDecodeError as e:
            print(f"Error: Generated invalid JSON: {str(e)}")
            error_pos = e.pos
            context_start = max(0, error_pos - 50)
            context_end = min(len(json_data), error_pos + 50)
            print(f"Error context: {json_data[context_start:context_end]}")
            return False
   
        # Upload to S3
        s3.put_object(
            Bucket=bucket_name,
            Key=output_key,
            Body=json_data.encode('utf-8'),  
            ContentType='application/json; charset=utf-8'
        )
        
        print(f"Successfully converted Excel to JSON with {len(data)} records")
        print(f"JSON data written to s3://{bucket_name}/{output_key}")
        
        # Save a local copy in .tmp directory
        os.makedirs("./.tmp", exist_ok=True)
        local_path = f"./.tmp/{os.path.basename(output_key)}"
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(json_data)
        print(f"Local copy saved to {local_path}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Stack trace:", traceback.format_exc())
        return False

def create_output_jsons(bucket_name):
    try:
        s3 = boto3.client('s3')
        
        print(f"Listing all JSON files in s3://{bucket_name}")
        
        paginator = s3.get_paginator('list_objects_v2')
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
                    
                    s3.put_object(
                        Bucket=bucket_name,
                        Key=output_key,
                        Body=empty_json.encode('utf-8'),
                        ContentType='application/json; charset=utf-8'
                    )
                    
                    print(f"Created empty output JSON: s3://{bucket_name}/{output_key}")
                    count += 1
        
        print(f"Created {count} empty output JSON files")
        return True
    
    except Exception as e:
        print(f"Error creating output JSONs: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python excel_to_json.py <command> [arguments...]")
        print("  Commands:")
        print("    excel <file_key> [sheet_name] [bucket_name]")
        print("    create-outputs [bucket_name]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'excel':
        if len(sys.argv) < 3:
            print("Error: Excel key is required")
            sys.exit(1)
            
        file_key = sys.argv[2]
        sheet_name = sys.argv[3] if len(sys.argv) > 3 else 0
        bucket_name = sys.argv[4] if len(sys.argv) > 4 else "your-s3-bucket-name"
        
        success = excel_to_json(bucket_name, file_key, sheet_name)
        sys.exit(0 if success else 1)
        
    elif command == 'create-outputs':
        bucket_name = sys.argv[2] if len(sys.argv) > 2 else "your-s3-bucket-name"
        success = create_output_jsons(bucket_name)
        sys.exit(0 if success else 1)
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1) 
