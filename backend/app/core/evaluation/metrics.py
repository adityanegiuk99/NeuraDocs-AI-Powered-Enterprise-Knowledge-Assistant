"""
RAG evaluation metrics.
Implements retrieval quality metrics (Precision@k, Recall@k, MRR)
and generation quality metrics (Faithfulness, Relevancy via LLM-as-judge).
"""

from typing import Optional

from app.core.generation.llm import BaseLLM
from app.utils.logging import get_logger

logger = get_logger(__name__)


def precision_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int = 5) -> float:
    """
    Precision@k: Of the top-k retrieved chunks, how many are relevant?
    
    Args:
        retrieved_ids: Ordered list of retrieved chunk IDs
        relevant_ids: Set of ground-truth relevant chunk IDs
        k: Number of top results to evaluate
    
    Returns:
        Float between 0 and 1
    """
    if not retrieved_ids or not relevant_ids:
        return 0.0

    top_k = retrieved_ids[:k]
    relevant_set = set(relevant_ids)
    hits = sum(1 for rid in top_k if rid in relevant_set)
    return hits / k


def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int = 5) -> float:
    """
    Recall@k: Of all relevant chunks, how many were in the top-k?
    
    Args:
        retrieved_ids: Ordered list of retrieved chunk IDs
        relevant_ids: Set of ground-truth relevant chunk IDs
        k: Number of top results to evaluate
    
    Returns:
        Float between 0 and 1
    """
    if not relevant_ids:
        return 0.0

    top_k = set(retrieved_ids[:k])
    relevant_set = set(relevant_ids)
    hits = len(top_k.intersection(relevant_set))
    return hits / len(relevant_set)


def mean_reciprocal_rank(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """
    MRR: 1 / rank of the first relevant result.
    
    Returns 0 if no relevant results found.
    """
    relevant_set = set(relevant_ids)
    for rank, rid in enumerate(retrieved_ids, 1):
        if rid in relevant_set:
            return 1.0 / rank
    return 0.0


def faithfulness_score(
    answer: str,
    context: str,
    llm: BaseLLM,
) -> float:
    """
    Faithfulness: Are all claims in the answer supported by the context?
    Uses LLM-as-judge to evaluate.
    
    Returns a score between 0 and 1.
    """
    prompt = f"""You are an evaluation judge. Evaluate whether the given answer is faithful to the provided context.

## Context (Ground Truth):
{context}

## Answer to Evaluate:
{answer}

## Task:
1. Extract all factual claims from the answer
2. For each claim, check if it is supported by the context
3. Calculate: (number of supported claims) / (total claims)

Return ONLY a number between 0.0 and 1.0 representing the faithfulness score.
Do not include any explanation, just the number."""

    try:
        result = llm.generate(
            system_prompt="You are a precise evaluation judge. Output only numbers.",
            user_prompt=prompt,
            max_tokens=10,
            temperature=0.0,
        )
        score = float(result.strip())
        return max(0.0, min(1.0, score))
    except (ValueError, Exception) as e:
        logger.warning("faithfulness_eval_failed", error=str(e))
        return 0.0


def answer_relevancy_score(
    query: str,
    answer: str,
    llm: BaseLLM,
) -> float:
    """
    Answer Relevancy: Does the answer address the question?
    Uses LLM-as-judge to evaluate.
    
    Returns a score between 0 and 1.
    """
    prompt = f"""You are an evaluation judge. Rate how relevant and complete the answer is for the given question.

## Question:
{query}

## Answer:
{answer}

## Scoring Criteria:
- 1.0: Fully answers the question with all necessary details
- 0.8: Answers the question well but may miss minor details
- 0.6: Partially answers the question
- 0.4: Tangentially related but doesn't directly answer
- 0.2: Barely related to the question
- 0.0: Completely irrelevant or "I don't know" response

Return ONLY a number between 0.0 and 1.0. No explanation."""

    try:
        result = llm.generate(
            system_prompt="You are a precise evaluation judge. Output only numbers.",
            user_prompt=prompt,
            max_tokens=10,
            temperature=0.0,
        )
        score = float(result.strip())
        return max(0.0, min(1.0, score))
    except (ValueError, Exception) as e:
        logger.warning("relevancy_eval_failed", error=str(e))
        return 0.0
