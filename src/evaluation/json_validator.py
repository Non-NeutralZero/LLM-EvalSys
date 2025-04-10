#!/usr/bin/env python3
import os
from typing import Dict, List, Any, Optional

from ..utils.logging import get_logger, log_error, log_section
from ..utils.config import DEFAULT_S3_BUCKET, TMP_DIR
from ..data.storage import read_json_from_s3, write_json_to_s3, get_output_json_path
from ..evaluation.evaluator import call_bedrock_model, build_judging_prompt

logger = get_logger()

def process_json_data(input_json_key: str, output_json_path: str, bucket_name: str = DEFAULT_S3_BUCKET) -> bool:
    """
    Process the JSON file containing questions, expected answers, and generated answers.
    Evaluates each generated answer against its expected answer.
    """
    try:
        data = read_json_from_s3(bucket_name, input_json_key)
        if not data:
            log_error(f"Failed to read input JSON from S3: {input_json_key}")
            return False
            
        logger.info(f"Processing {len(data)} entries from input JSON")

        results = []
        for i, entry in enumerate(data):
            logger.info(f"Processing entry {i+1}/{len(data)}")
            
            question = str(entry.get("Question", "") or "").strip()
            expected_answer = str(entry.get("Expected Answer", "") or "").strip()
            
            if not question or not expected_answer:
                logger.warning(f"Skipping entry {i+1} due to missing question or expected answer")
                continue
            
            # case where Generated Answer might be empty or a string or if it's an error message 
            generated_answer = entry.get("Generated Answer", {})
            if isinstance(generated_answer, dict):
                text_response = str(generated_answer.get("text_response", "") or "").strip()
            else:
                text_response = str(generated_answer or "").strip()
            
            if "The model took too long to respond" in text_response:
                logger.warning(f"Skipping entry {i+1} due to timeout")
                result_entry = {
                    "question": question,
                    "expected_answer": expected_answer,
                    "generated_answer": text_response,
                    "text_response_evaluation": {
                        "accuracy": 0,
                        "completeness": 0,
                        "relevance": 0,
                        "justification": "Skipped due to timeout error in the response"
                    }
                }
            else:
                prompt_inputs = build_judging_prompt(
                    question=question,
                    generated=text_response,
                    reference=expected_answer
                )
                
                evaluation_result = call_bedrock_model(prompt_inputs)
                logger.info(f"Evaluated with scores - Accuracy: {evaluation_result.get('accuracy', 0)}, "
                           f"Completeness: {evaluation_result.get('completeness', 0)}, "
                           f"Relevance: {evaluation_result.get('relevance', 0)}")
                
                
                result_entry = {
                    "question": question,
                    "expected_answer": expected_answer,
                    "generated_answer": text_response,
                    "text_response_evaluation": {
                        "accuracy": evaluation_result.get("accuracy", 0),
                        "completeness": evaluation_result.get("completeness", 0),
                        "relevance": evaluation_result.get("relevance", 0),
                        "justification": evaluation_result.get("justification", "")
                    }
                }
            
            results.append(result_entry)
        
        # save results locally and to S3
        os.makedirs(TMP_DIR, exist_ok=True)
        output_s3_key = get_output_json_path(input_json_key)
    
        write_success = write_json_to_s3(bucket_name, output_s3_key, results)
        if not write_success:
            log_error(f"Failed to write results to S3: {output_s3_key}")
            return False
            
            # NOTE: to dash
        calculate_summary_statistics(results)
        
        return True
    
    except Exception as e:
        log_error("Error processing JSON data", e)
        return False

def calculate_summary_statistics(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate summary statistics from the evaluation results
    """
    if not results:
        logger.warning("No results to calculate statistics")
        return {
            "total_entries": 0,
            "timeout_entries": 0,
            "evaluated_entries": 0,
            "avg_accuracy": 0,
            "avg_completeness": 0,
            "avg_relevance": 0,
            "avg_overall": 0
        }
    
    # Counts
    total_entries = len(results)
    timeout_entries = sum(1 for entry in results if "Skipped due to timeout" in entry.get("text_response_evaluation", {}).get("justification", ""))
    evaluated_entries = total_entries - timeout_entries
    
    # Averages
    total_accuracy = 0
    total_completeness = 0
    total_relevance = 0
    
    for entry in results:
        evaluation = entry.get("text_response_evaluation", {})
        if "Skipped due to timeout" not in evaluation.get("justification", ""):
            total_accuracy += evaluation.get("accuracy", 0)
            total_completeness += evaluation.get("completeness", 0)
            total_relevance += evaluation.get("relevance", 0)
    
    avg_accuracy = total_accuracy / evaluated_entries if evaluated_entries > 0 else 0
    avg_completeness = total_completeness / evaluated_entries if evaluated_entries > 0 else 0
    avg_relevance = total_relevance / evaluated_entries if evaluated_entries > 0 else 0
    avg_overall = (avg_accuracy + avg_completeness + avg_relevance) / 3
    

    log_section("EVALUATION REPORT")
    logger.info(f"Total entries: {total_entries}")
    logger.info(f"Timeout entries: {timeout_entries}")
    logger.info(f"Evaluated entries: {evaluated_entries}")
    logger.info(f"Average accuracy: {avg_accuracy:.2f}/10")
    logger.info(f"Average completeness: {avg_completeness:.2f}/10")
    logger.info(f"Average relevance: {avg_relevance:.2f}/10")
    logger.info(f"Average overall score: {avg_overall:.2f}/10")
    log_section("END OF REPORT")
    
    
    return {
        "total_entries": total_entries,
        "timeout_entries": timeout_entries,
        "evaluated_entries": evaluated_entries,
        "avg_accuracy": avg_accuracy,
        "avg_completeness": avg_completeness,
        "avg_relevance": avg_relevance,
        "avg_overall": avg_overall
    } 