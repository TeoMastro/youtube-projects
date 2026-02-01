"""
RAG Evaluator for Greek Legal Document System.

Uses RAGAS metrics for RAG performance evaluation.
"""

import json
import logging
import math
import traceback
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from datasets import Dataset
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

from ..agents.graph import run_multi_agent_query_sync
from ..config import settings

logger = logging.getLogger(__name__)


class RAGEvaluator:
    """
    Evaluator for the multi-agent RAG system.

    Uses RAGAS metrics: faithfulness, relevance, precision, recall.
    """

    def __init__(self, dataset_path: str = "evaluation_dataset.json"):
        """
        Initialize evaluator.

        Args:
            dataset_path: Path to evaluation dataset JSON file
        """
        self.dataset_path = Path(dataset_path)

    def load_dataset(self) -> List[Dict[str, Any]]:
        """Load evaluation dataset from JSON file."""
        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Evaluation dataset not found at {self.dataset_path}. "
                "Please create an evaluation dataset first."
            )

        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data.get('test_cases', [])

    def run_evaluation(
        self,
        save_results: bool = True,
        output_dir: str = "evaluation_results"
    ) -> Dict[str, Any]:
        """
        Run full evaluation on all test cases.

        Args:
            save_results: Whether to save results to disk
            output_dir: Directory to save results

        Returns:
            Dict with evaluation results and metrics
        """
        logger.info("Starting RAG evaluation...")
        test_cases = self.load_dataset()

        if not test_cases:
            logger.error("No test cases found in dataset")
            return {}

        logger.info(f"Loaded {len(test_cases)} test cases")

        # Run each test case
        results = []
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"Running test case {i}/{len(test_cases)}: {test_case['id']}")
            result = self._evaluate_single(test_case)
            results.append(result)

        # Calculate RAGAS metrics
        logger.info("Calculating RAGAS metrics...")
        ragas_results = self._calculate_ragas_metrics(results)

        # Combine results
        evaluation_results = {
            "timestamp": datetime.now().isoformat(),
            "dataset": str(self.dataset_path),
            "num_test_cases": len(test_cases),
            "ragas_metrics": ragas_results,
            "individual_results": results,
            "config": {
                "model": settings.OPENAI_MODEL,
                "embedding_model": settings.OPENAI_EMBEDDING_MODEL,
                "retrieval_top_k": settings.RETRIEVAL_TOP_K,
            }
        }

        # Save results
        if save_results:
            self._save_results(evaluation_results, output_dir)

        logger.info("Evaluation complete!")
        return evaluation_results

    def _evaluate_single(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a single test case.

        Args:
            test_case: Test case dictionary

        Returns:
            Dict with results for this test case
        """
        question = test_case['question']

        try:
            # Run multi-agent query
            response = run_multi_agent_query_sync(question)

            # Extract results
            result = {
                "test_id": test_case['id'],
                "question": question,
                "answer": response['answer'],
                "expected_answer": test_case.get('expected_answer', ''),
                "retrieved_contexts": response.get('retrieved_contexts', []),
                "sources": response['sources'],
                "success": True,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error evaluating test case {test_case['id']}: {e}")
            result = {
                "test_id": test_case['id'],
                "question": question,
                "success": False,
                "error": str(e)
            }

        return result

    def _calculate_ragas_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate RAGAS metrics for all results.

        Args:
            results: List of evaluation results

        Returns:
            Dict with RAGAS metric scores
        """
        # Filter successful results
        successful_results = [r for r in results if r.get('success', False)]

        if not successful_results:
            logger.warning("No successful results to calculate RAGAS metrics")
            return {}

        # Prepare data for RAGAS
        data = {
            'question': [],
            'answer': [],
            'contexts': [],
            'ground_truth': []
        }

        for result in successful_results:
            data['question'].append(result['question'])
            data['answer'].append(result['answer'])

            # Use actual retrieved document content for RAGAS evaluation
            # This is the actual text from the documents, not just metadata
            retrieved_contexts = result.get('retrieved_contexts', [])

            if retrieved_contexts:
                # Use actual document content
                contexts = retrieved_contexts
            else:
                # Fallback: try to extract text from sources if available
                contexts = [
                    source.get('text', str(source))
                    for source in result.get('sources', [])
                    if source
                ]

            data['contexts'].append(contexts if contexts else ['No context available'])

            # Use expected answer as ground truth
            data['ground_truth'].append(result.get('expected_answer', ''))

        # Create dataset
        dataset = Dataset.from_dict(data)

        try:
            # Configure RAGAS with explicit LLM (required in newer versions)
            evaluate_kwargs = {
                "dataset": dataset,
                "metrics": [
                    faithfulness,
                    answer_relevancy,
                    context_precision,
                    context_recall,
                ],
            }

            # Configure RAGAS with explicit LLM
            llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0)
            embeddings = OpenAIEmbeddings(model=settings.OPENAI_EMBEDDING_MODEL)
            evaluate_kwargs["llm"] = LangchainLLMWrapper(llm)
            evaluate_kwargs["embeddings"] = LangchainEmbeddingsWrapper(embeddings)

            # Run RAGAS evaluation
            logger.info("Running RAGAS evaluation...")
            ragas_result = evaluate(**evaluate_kwargs)

            # Helper to extract score (handles both list and scalar returns)
            def extract_score(result, key):
                value = result[key]
                if isinstance(value, list):
                    # Newer RAGAS versions return per-sample scores as list
                    # Filter out None and NaN values, then calculate mean
                    valid_scores = [
                        v for v in value
                        if v is not None and not (isinstance(v, float) and math.isnan(v))
                    ]
                    return sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
                # Handle scalar NaN
                float_val = float(value)
                return 0.0 if math.isnan(float_val) else float_val

            # Convert to dict
            return {
                "faithfulness": extract_score(ragas_result, 'faithfulness'),
                "answer_relevancy": extract_score(ragas_result, 'answer_relevancy'),
                "context_precision": extract_score(ragas_result, 'context_precision'),
                "context_recall": extract_score(ragas_result, 'context_recall'),
            }

        except Exception as e:
            # Print error prominently so user can see it
            error_msg = f"Error calculating RAGAS metrics: {e}"
            logger.error(error_msg)
            print(f"\n[RAGAS ERROR] {error_msg}")
            print(f"[RAGAS ERROR] Traceback: {traceback.format_exc()}")
            return {}

    def _save_results(self, results: Dict[str, Any], output_dir: str):
        """
        Save evaluation results to disk.

        Args:
            results: Evaluation results dictionary
            output_dir: Directory to save results
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = output_path / f"evaluation_results_{timestamp}.json"

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"Results saved to {results_file}")
