#!/usr/bin/env python3
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

def calculate_metrics(evaluation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate detailed metrics from evaluation results
    Return: Dict[str, Any]: Detailed metrics
    """
    if not evaluation_results:
        return {
            "count": 0,
            "metrics": {},
            "distribution": {}
        }
    
    metrics = {}
    accuracy_scores = []
    completeness_scores = []
    relevance_scores = []
    for result in evaluation_results:
        eval_data = result.get("text_response_evaluation", {})
        if "Skipped due to timeout" not in eval_data.get("justification", ""):
            accuracy_scores.append(eval_data.get("accuracy", 0))
            completeness_scores.append(eval_data.get("completeness", 0))
            relevance_scores.append(eval_data.get("relevance", 0))
    
    if not accuracy_scores:

        return {
            "count": 0,
            "metrics": {},
            "distribution": {}
        }
    
    metrics["accuracy"] = {
        "mean": np.mean(accuracy_scores),
        "median": np.median(accuracy_scores),
        "min": np.min(accuracy_scores),
        "max": np.max(accuracy_scores),
        "std": np.std(accuracy_scores)
    }
    
    metrics["completeness"] = {
        "mean": np.mean(completeness_scores),
        "median": np.median(completeness_scores),
        "min": np.min(completeness_scores),
        "max": np.max(completeness_scores),
        "std": np.std(completeness_scores)
    }
    
    metrics["relevance"] = {
        "mean": np.mean(relevance_scores),
        "median": np.median(relevance_scores),
        "min": np.min(relevance_scores),
        "max": np.max(relevance_scores),
        "std": np.std(relevance_scores)
    }
    
    # Calculate combined score
    combined_scores = [(a + c + r) / 3 for a, c, r in zip(accuracy_scores, completeness_scores, relevance_scores)]
    
    metrics["combined"] = {
        "mean": np.mean(combined_scores),
        "median": np.median(combined_scores),
        "min": np.min(combined_scores),
        "max": np.max(combined_scores),
        "std": np.std(combined_scores)
    }
    
    # Score distribution
    distribution = {}
    
    for score_type, scores in [
        ("accuracy", accuracy_scores),
        ("completeness", completeness_scores),
        ("relevance", relevance_scores),
        ("combined", combined_scores)
    ]:
        bins = {}
        for i in range(11):  # 0-10 scores
            bins[i] = sum(1 for s in scores if round(s) == i)
        
        distribution[score_type] = bins
    
    return {
        "count": len(accuracy_scores),
        "metrics": metrics,
        "distribution": distribution
    }

def get_score_level(score: float) -> str:
    """
    descriptive level for a final score
    """
    if score >= 9:
        return "Excellent"
    elif score >= 7:
        return "Good"
    elif score >= 5:
        return "Average"
    elif score >= 3:
        return "Below Average"
    else:
        return "Poor"

def format_score(score: float) -> str:
    """
    Format a score with its descriptive band
    """
    return f"{score:.1f}/10 ({get_score_level(score)})" 