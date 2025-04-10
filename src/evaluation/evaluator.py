#!/usr/bin/env python3
import boto3
import json
import time
from typing import Dict, Any, Optional

from ..utils.config import BEDROCK_DEFAULT_MODEL, BEDROCK_FALLBACK_MODEL
from ..utils.logging import get_logger, log_error

logger = get_logger()

def build_judging_prompt(question: str, generated: str, reference: str) -> Dict[str, str]:
    """
    Build the prompt inputs for the judging model
    
    Args:
        question (str): The question to be evaluated
        generated (str): The generated answer
        reference (str): The reference or expected answer
        
    Returns:
        Dict[str, str]: Dictionary of prompt inputs
    """
    return {
        "question": question,
        "generated": generated,
        "reference": reference
    }

def call_bedrock_model(prompt_inputs: Dict[str, str], max_retries: int = 3) -> Dict[str, Any]:
    """
    Calls the AWS Bedrock model to evaluate an answer
    """
    try:
        bedrock = boto3.client("bedrock-runtime")
        
        model_id = BEDROCK_DEFAULT_MODEL
        fallback_model_id = BEDROCK_FALLBACK_MODEL

        question = prompt_inputs.get("question", "").strip() or "Question not provided"
        generated = prompt_inputs.get("generated", "").strip() or "Generated answer not provided"
        reference = prompt_inputs.get("reference", "").strip() or "Expected answer not provided"
        
        prompt = f"""Evaluate the generated answer compared to the expected answer.

Question: {question}

Generated answer: {generated}

Expected answer: {reference}

Provide evaluation scores with:
- Accuracy (from 0 to 10): How factually correct the generated answer is compared to the expected answer
- Completeness (from 0 to 10): How thoroughly the generated answer covers all aspects of the expected answer
- Relevance (from 0 to 10): How is the generated answer relative to the specific question asked. Do they have the same topic? Does the answer address the same aspects of the question's topic?

Response format:
Accuracy score: [0-10]
Completeness score: [0-10]
Relevance score: [0-10]
Justification: [Detailed explanation]"""
        
        retries = 0
        result = None
        
        while retries < max_retries:
            try:
                logger.info(f"Calling Bedrock model {model_id} (attempt {retries + 1}/{max_retries})")
                
                response = bedrock.invoke_model(
                    modelId=model_id,
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 4096,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    }),
                    contentType="application/json",
                    accept="application/json"
                )
                
                response_body = json.loads(response["body"].read().decode("utf-8"))
                result = response_body.get("content", [{}])[0].get("text", "")
                break
                
            except Exception as invoke_error:
                retries += 1
                error_message = str(invoke_error)

                if "ValidationException" in error_message and "inference profile" in error_message:
                    logger.warning(f"Inference profile error detected, trying fallback model")
                    model_id = fallback_model_id
                elif retries < max_retries:
                    logger.warning(f"Error calling Bedrock model, retrying in 2 seconds")
                    time.sleep(2)
                else:
                    # max retries reached
                    raise
        
        if not result:
            log_error("Failed to get response from Bedrock model after retries")
            return {
                "accuracy": 0,
                "completeness": 0,
                "relevance": 0,
                "justification": "Failed to get response from model"
            }
            
        try:
            lines = result.split("\n")
            
            def extract_score(prefix):
                try:
                    score_line = next((line for line in lines if line.startswith(prefix)), "")
                    return int(score_line.split(":")[1].strip()) if score_line else 0
                except (IndexError, ValueError):
                    return 0
            
            accuracy = extract_score("Accuracy score")
            completeness = extract_score("Completeness score")
            relevance = extract_score("Relevance score")
            
            justification_lines = [line for line in lines if line.startswith("Justification")]
            justification = " ".join(justification_lines).replace("Justification:", "").strip() if justification_lines else ""
            
            logger.info(f"Evaluation scores - Accuracy: {accuracy}, Completeness: {completeness}, Relevance: {relevance}")
            
            return {
                "accuracy": accuracy,
                "completeness": completeness,
                "relevance": relevance,
                "justification": justification
            }
        
        except Exception as parsing_error:
            log_error("Error parsing evaluation result", parsing_error)
            return {
                "accuracy": 0,
                "completeness": 0,
                "relevance": 0,
                "justification": f"Parsing error: {parsing_error}",
                "raw_result": result
            }
    
    except Exception as e:
        log_error("Error in call_bedrock_model", e)
        return {
            "accuracy": 0,
            "completeness": 0,
            "relevance": 0,
            "justification": f"Failed to evaluate: {e}"
        } 