# LLM Response Evaluation Workflow

A workflow for evaluating and analyzing responses from Large Language Models (LLMs). The system processes questions, generates LLM responses, and evaluates them against expected answers to produce quality assessment metrics and statistics.

## Features
- Converts Excel files with questions/expected answers to JSON format
- Generate LLM responses using AWS Bedrock model
- Evaluate response quality with automatic scoring for:
  - Accuracy (0-10)
  - Completeness (0-10)
  - Relevance (0-10)
- Calculate and report summary statistics
- Support for AWS S3 storage integration

## Code Structure

```
src/
├── __init__.py
├── __main__.py
├── evaluation/ 
│   ├── __init__.py
│   ├── evaluator.py 
│   ├── json_validator.py 
│   ├── metrics.py  # Evaluation metrics and scoring
│   └── workflow.py  # End-to-end workflow orchestration
├── data/
│   ├── __init__.py
│   ├── excel_processor.py  # excel to JSON
│   └── storage.py
├── generation/
│   ├── __init__.py
│   └── response_generator.py  # Response generation with Lambda
└── utils/
    ├── __init__.py
    ├── config.py  
    └── logging.py 
```


###  Usage

```bash
# Run the full workflow using the CLI entry point
llm-evaluate your_input_file.xlsx --bucket your-s3-bucket --workers 5

# Or
python -m src your_input_file.xlsx --bucket your-s3-bucket --workers 5
```

### ETL Steps

1. **Excel Conversion**: Convert Excel files to JSON format
2. **Response Generation**: Generate LLM responses for each question
3. **Evaluation**: Score each generated response against expected answers
4. **Statistics**: Calculate and report summary statistics

## Configuration

### Environment Variables

Configure sensitive information using environment variables:

```bash
export S3_BUCKET_NAME="your-s3-bucket-name"
export LAMBDA_FUNCTION_NAME="your-lambda-function-name"
export PRIMARY_MODEL_ID="anthropic.claude-3-sonnet-20240229-v1:0"
export FALLBACK_MODEL_ID="anthropic.claude-instant-v1"
```

### AWS Resources

The system uses the following AWS resources:
- S3 bucket for storage 
- Lambda function for generation
- AWS Bedrock for model access

## Requirements

- Python 3.10+
- AWS Account
- Required Python packages:
  - boto3
  - pandas
  - numpy
  - requests