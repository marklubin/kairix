"""
InferenceEval: A lightweight evaluation framework for testing AI model outputs
against expected behaviors using multiple scoring methods.
"""

import json
import os
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, field
import numpy as np
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from pydantic import BaseModel
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class InferenceTestCase:
    """Represents a single test case for evaluation."""
    inputs: Dict[str, str]  # Can include prompt, context, query, etc.
    expected_behavior: str
    test_type: Optional[str] = None  # e.g., "rag", "prompt_adherence", "function_calling"
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.inputs or not self.expected_behavior:
            raise ValueError("inputs and expected_behavior cannot be empty")


@dataclass
class TestResult:
    """Result of a single test evaluation."""
    test_case: InferenceTestCase
    prediction: str
    score: float
    eval_type: str  # "semantic" or "llm_judge"
    reasoning: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


class EvaluationScore(BaseModel):
    """Structured response from LLM judge."""
    score: float
    reasoning: str
    criteria_scores: Dict[str, float]


class InferenceEval:
    """
    General evaluation framework for comparing model predictions against expected behaviors.
    
    Supports two evaluation types:
    - Semantic similarity using sentence embeddings
    - LLM-based evaluation using OpenAI structured outputs
    
    Can be used for evaluating:
    - RAG system responses
    - Prompt adherence
    - Function calling accuracy
    - General model outputs
    """
    
    def __init__(
        self,
        name: str,
        generate_report: bool = True,
        semantic_model: str = "all-MiniLM-L6-v2",
        llm_judge_model: str = "gpt-4o-mini",
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize the evaluation framework.
        
        Args:
            name: Name of this evaluation suite
            generate_report: Whether to generate detailed reports
            semantic_model: Name of the sentence transformer model
            llm_judge_model: OpenAI model to use for LLM judging
            openai_api_key: OpenAI API key (uses env var if not provided)
        """
        self.name = name
        self.generate_report = generate_report
        self.encoder = None  # Lazy load
        self.semantic_model = semantic_model
        self.llm_judge_model = llm_judge_model
        self.tests: List[InferenceTestCase] = []
        self.results: List[TestResult] = []
        
        # Set up OpenAI
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
            logger.warning("No OpenAI API key found. LLM judging will not be available.")
    
    def add_test(
        self,
        inputs: Dict[str, str],
        expected_behavior: str,
        test_type: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Add a test case to the evaluation suite.
        
        Args:
            inputs: Dictionary of inputs (e.g., {"prompt": "...", "context": "..."})
            expected_behavior: Description of expected output behavior
            test_type: Type of test (e.g., "rag", "prompt_adherence")
            metadata: Additional metadata for the test
        """
        test_case = InferenceTestCase(
            inputs=inputs,
            expected_behavior=expected_behavior,
            test_type=test_type,
            metadata=metadata or {}
        )
        self.tests.append(test_case)
    
    def _init_encoder(self):
        """Lazy initialization of sentence encoder."""
        if self.encoder is None:
            self.encoder = SentenceTransformer(self.semantic_model)
    
    def evaluate_semantic(self, predictions: Union[List[str], Dict[int, str]]) -> Dict:
        """
        Evaluate predictions using semantic similarity.
        
        Args:
            predictions: List of predictions or dict mapping indices to predictions
            
        Returns:
            Evaluation results dictionary
        """
        self._init_encoder()
        predictions_list = self._validate_predictions(predictions)
        
        results = []
        for test, prediction in zip(self.tests, predictions_list):
            score = self._semantic_score(prediction, test.expected_behavior)
            result = TestResult(
                test_case=test,
                prediction=prediction,
                score=score,
                eval_type="semantic"
            )
            results.append(result)
            self.results.append(result)
        
        return self._compile_results(results)
    
    def evaluate_llm_judge(self, predictions: Union[List[str], Dict[int, str]]) -> Dict:
        """
        Evaluate predictions using LLM judge with structured outputs.
        
        Args:
            predictions: List of predictions or dict mapping indices to predictions
            
        Returns:
            Evaluation results dictionary
        """
        if not self.client:
            raise RuntimeError("OpenAI client not initialized. Provide API key.")
            
        predictions_list = self._validate_predictions(predictions)
        
        results = []
        for test, prediction in zip(self.tests, predictions_list):
            score, reasoning = self._llm_judge_score(prediction, test)
            result = TestResult(
                test_case=test,
                prediction=prediction,
                score=score,
                eval_type="llm_judge",
                reasoning=reasoning
            )
            results.append(result)
            self.results.append(result)
        
        return self._compile_results(results)
    
    def _validate_predictions(self, predictions: Union[List[str], Dict[int, str]]) -> List[str]:
        """Validate and convert predictions to list format."""
        if not self.tests:
            raise ValueError("No tests added. Use add_test() first.")
            
        if isinstance(predictions, dict):
            predictions_list = []
            for i in range(len(self.tests)):
                if i not in predictions:
                    raise ValueError(f"No prediction provided for test index: {i}")
                predictions_list.append(predictions[i])
        else:
            predictions_list = predictions
            
        if len(predictions_list) != len(self.tests):
            raise ValueError(
                f"Number of predictions ({len(predictions_list)}) "
                f"doesn't match number of tests ({len(self.tests)})"
            )
            
        return predictions_list
    
    def _semantic_score(self, prediction: str, expected: str) -> float:
        """Calculate semantic similarity between prediction and expected behavior."""
        try:
            emb1 = self.encoder.encode(prediction)
            emb2 = self.encoder.encode(expected)
            
            # Cosine similarity
            similarity = float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
            
            # Ensure score is between 0 and 1
            return max(0.0, min(1.0, similarity))
        except Exception as e:
            logger.error(f"Error in semantic scoring: {e}")
            return 0.0
    
    def _llm_judge_score(self, prediction: str, test_case: InferenceTestCase) -> tuple[float, str]:
        """Use LLM to judge prediction with structured output."""
        # Build context from inputs
        input_context = "\n".join([f"{k}: {v}" for k, v in test_case.inputs.items()])
        
        prompt = f"""Evaluate how well the prediction matches the expected behavior.

Test Type: {test_case.test_type or "general"}

Inputs provided:
{input_context}

Expected behavior: {test_case.expected_behavior}

Actual prediction: {prediction}

Evaluate based on these criteria and provide a score for each:
1. relevance: Does the prediction address what was expected? (0-1)
2. completeness: Are all expected elements present? (0-1)
3. accuracy: Is the information correct and aligned with expectations? (0-1)
4. format: Does it follow any specified format requirements? (0-1)

Provide an overall score (0-1) and reasoning for your evaluation."""
        
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.llm_judge_model,
                messages=[{"role": "user", "content": prompt}],
                response_format=EvaluationScore,
                temperature=0
            )
            
            eval_result = response.choices[0].message.parsed
            return eval_result.score, eval_result.reasoning
            
        except Exception as e:
            logger.error(f"Error in LLM judge scoring: {e}")
            return 0.0, f"Error: {str(e)}"
    
    def _compile_results(self, results: List[TestResult]) -> Dict:
        """Compile results into summary statistics."""
        all_scores = [r.score for r in results]
        
        # Group by test type
        scores_by_type = {}
        for result in results:
            test_type = result.test_case.test_type or "general"
            if test_type not in scores_by_type:
                scores_by_type[test_type] = []
            scores_by_type[test_type].append(result.score)
        
        # Calculate metrics by test type
        metrics_by_type = {}
        for test_type, scores in scores_by_type.items():
            if scores:
                metrics_by_type[test_type] = {
                    "mean": float(np.mean(scores)),
                    "std": float(np.std(scores)),
                    "min": float(np.min(scores)),
                    "max": float(np.max(scores)),
                    "count": len(scores)
                }
        
        summary = {
            "eval_name": self.name,
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "overall_score": float(np.mean(all_scores)),
            "metrics_by_type": metrics_by_type,
            "num_tests": len(results),
            "summary_stats": {
                "mean": float(np.mean(all_scores)),
                "std": float(np.std(all_scores)),
                "min": float(np.min(all_scores)),
                "max": float(np.max(all_scores))
            }
        }
        
        if self.generate_report:
            self._generate_report(summary)
            
        return summary
    
    def _generate_report(self, summary: Dict) -> None:
        """Generate a detailed report of evaluation results."""
        report_dir = "evaluation_reports"
        os.makedirs(report_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(report_dir, f"{self.name}_{timestamp}_report.json")
        
        # Convert dataclasses to dicts for JSON serialization
        export_data = {
            **summary,
            "results": [
                {
                    "inputs": r.test_case.inputs,
                    "expected": r.test_case.expected_behavior,
                    "prediction": r.prediction,
                    "score": r.score,
                    "eval_type": r.eval_type,
                    "reasoning": r.reasoning,
                    "test_type": r.test_case.test_type,
                    "metadata": r.metadata
                }
                for r in summary["results"]
            ]
        }
        
        with open(report_path, "w") as f:
            json.dump(export_data, f, indent=2)
        
        # Also generate a human-readable summary
        summary_path = os.path.join(report_dir, f"{self.name}_{timestamp}_summary.txt")
        with open(summary_path, "w") as f:
            f.write(f"Evaluation Report: {self.name}\n")
            f.write(f"Generated: {summary['timestamp']}\n")
            f.write(f"{'=' * 50}\n\n")
            
            f.write(f"Overall Score: {summary['overall_score']:.3f}\n")
            f.write(f"Total Tests: {summary['num_tests']}\n\n")
            
            f.write("Summary Statistics:\n")
            stats = summary['summary_stats']
            f.write(f"  Mean: {stats['mean']:.3f}\n")
            f.write(f"  Std:  {stats['std']:.3f}\n")
            f.write(f"  Min:  {stats['min']:.3f}\n")
            f.write(f"  Max:  {stats['max']:.3f}\n\n")
            
            if summary['metrics_by_type']:
                f.write("Scores by Test Type:\n")
                for test_type, metrics in summary['metrics_by_type'].items():
                    f.write(f"\n  {test_type}:\n")
                    f.write(f"    Mean: {metrics['mean']:.3f}\n")
                    f.write(f"    Count: {metrics['count']}\n")
            
            # List failing tests
            failing = [r for r in summary['results'] if r.score < 0.5]
            if failing:
                f.write(f"\n\nFailing Tests (score < 0.5): {len(failing)}\n")
                for r in failing[:5]:  # Show first 5
                    f.write(f"\n  Score: {r.score:.3f}\n")
                    f.write(f"  Inputs: {list(r.test_case.inputs.keys())}\n")
                    if r.reasoning:
                        f.write(f"  Reasoning: {r.reasoning[:100]}...\n")
        
        logger.info(f"Report saved to {report_path} and {summary_path}")
    
    def clear_tests(self) -> None:
        """Clear all test cases and results."""
        self.tests = []
        self.results = []
    
    def get_failing_tests(self, threshold: float = 0.5) -> List[TestResult]:
        """Get tests that scored below threshold."""
        return [r for r in self.results if r.score < threshold]
