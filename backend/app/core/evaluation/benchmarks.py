"""
Benchmark evaluation runner.
Loads golden Q&A dataset, runs each query through the RAG pipeline,
and computes aggregate metrics.
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.config import settings
from app.core.evaluation.metrics import (
    answer_relevancy_score,
    faithfulness_score,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)
from app.core.generation.llm import BaseLLM
from app.core.generation.rag_chain import RAGChain
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BenchmarkQuery:
    """A single benchmark test case."""
    id: str
    query: str
    ground_truth_answer: str
    relevant_chunk_ids: list[str] = field(default_factory=list)
    category: str = "general"
    difficulty: str = "medium"


@dataclass
class EvalRunResult:
    """Complete results from a benchmark evaluation run."""
    run_id: str
    benchmark_id: str
    total_queries: int
    # Retrieval metrics
    avg_precision_at_k: float = 0.0
    avg_recall_at_k: float = 0.0
    avg_mrr: float = 0.0
    # Generation metrics
    avg_faithfulness: float = 0.0
    avg_relevancy: float = 0.0
    # Latency
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    # Per-query details
    query_results: list[dict] = field(default_factory=list)


class BenchmarkRunner:
    """
    Runs evaluation benchmarks against the RAG pipeline.
    
    Usage:
        runner = BenchmarkRunner(rag_chain, eval_llm)
        results = runner.run("default")
    """

    def __init__(self, rag_chain: RAGChain, eval_llm: Optional[BaseLLM] = None):
        self.rag_chain = rag_chain
        self.eval_llm = eval_llm  # LLM used for judging (can differ from generation LLM)

    def load_benchmark(self, benchmark_id: str = "default") -> list[BenchmarkQuery]:
        """Load benchmark dataset from JSON file."""
        benchmark_path = Path(settings.benchmark_dir) / f"{benchmark_id}.json"

        if not benchmark_path.exists():
            logger.warning("benchmark_not_found", path=str(benchmark_path))
            return []

        with open(benchmark_path, "r") as f:
            data = json.load(f)

        queries = []
        for item in data.get("queries", []):
            queries.append(BenchmarkQuery(
                id=item["id"],
                query=item["query"],
                ground_truth_answer=item["ground_truth_answer"],
                relevant_chunk_ids=item.get("relevant_chunk_ids", []),
                category=item.get("category", "general"),
                difficulty=item.get("difficulty", "medium"),
            ))

        logger.info("benchmark_loaded", id=benchmark_id, queries=len(queries))
        return queries

    def run(self, benchmark_id: str = "default", top_k: int = 5) -> EvalRunResult:
        """Run full evaluation on a benchmark dataset."""
        queries = self.load_benchmark(benchmark_id)
        if not queries:
            return EvalRunResult(
                run_id=str(uuid.uuid4()),
                benchmark_id=benchmark_id,
                total_queries=0,
            )

        run_id = str(uuid.uuid4())
        query_results = []
        latencies = []

        precisions = []
        recalls = []
        mrrs = []
        faithfulness_scores = []
        relevancy_scores = []

        for bq in queries:
            logger.info("eval_query", query_id=bq.id, query=bq.query[:80])

            # Run RAG pipeline
            t0 = time.time()
            rag_response = self.rag_chain.run(query=bq.query, top_k=top_k)
            query_latency = (time.time() - t0) * 1000
            latencies.append(query_latency)

            # Extract retrieved chunk IDs
            retrieved_ids = [
                chunk.get("chunk_id", "")
                for chunk in rag_response.sources
            ]

            # Compute retrieval metrics
            p_at_k = precision_at_k(retrieved_ids, bq.relevant_chunk_ids, k=top_k)
            r_at_k = recall_at_k(retrieved_ids, bq.relevant_chunk_ids, k=top_k)
            mrr = mean_reciprocal_rank(retrieved_ids, bq.relevant_chunk_ids)

            precisions.append(p_at_k)
            recalls.append(r_at_k)
            mrrs.append(mrr)

            # Compute generation metrics (if eval LLM available)
            faith = 0.0
            relevancy = 0.0
            if self.eval_llm and rag_response.sources:
                context = "\n".join(c.get("text", "") for c in rag_response.sources)
                faith = faithfulness_score(rag_response.answer, context, self.eval_llm)
                relevancy = answer_relevancy_score(bq.query, rag_response.answer, self.eval_llm)
                faithfulness_scores.append(faith)
                relevancy_scores.append(relevancy)

            query_results.append({
                "query_id": bq.id,
                "query": bq.query,
                "answer": rag_response.answer,
                "ground_truth": bq.ground_truth_answer,
                "precision_at_k": round(p_at_k, 4),
                "recall_at_k": round(r_at_k, 4),
                "mrr": round(mrr, 4),
                "faithfulness": round(faith, 4),
                "relevancy": round(relevancy, 4),
                "latency_ms": round(query_latency, 1),
                "sources_count": len(rag_response.sources),
                "confidence": round(rag_response.confidence, 4),
            })

        # Compute aggregates
        sorted_latencies = sorted(latencies)
        p95_idx = int(len(sorted_latencies) * 0.95)

        result = EvalRunResult(
            run_id=run_id,
            benchmark_id=benchmark_id,
            total_queries=len(queries),
            avg_precision_at_k=round(sum(precisions) / len(precisions), 4) if precisions else 0,
            avg_recall_at_k=round(sum(recalls) / len(recalls), 4) if recalls else 0,
            avg_mrr=round(sum(mrrs) / len(mrrs), 4) if mrrs else 0,
            avg_faithfulness=round(sum(faithfulness_scores) / len(faithfulness_scores), 4) if faithfulness_scores else 0,
            avg_relevancy=round(sum(relevancy_scores) / len(relevancy_scores), 4) if relevancy_scores else 0,
            avg_latency_ms=round(sum(latencies) / len(latencies), 1) if latencies else 0,
            p95_latency_ms=round(sorted_latencies[p95_idx], 1) if sorted_latencies else 0,
            query_results=query_results,
        )

        logger.info(
            "eval_run_complete",
            run_id=run_id,
            queries=len(queries),
            avg_precision=result.avg_precision_at_k,
            avg_recall=result.avg_recall_at_k,
            avg_faithfulness=result.avg_faithfulness,
        )

        return result
