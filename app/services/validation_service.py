from statistics import mean
from typing import Any


def compute_confidence(sources: list[dict[str, Any]], approved: bool) -> float:
    numeric_scores = [float(source.get("score")) for source in sources if source.get("score") is not None]
    retrieval_factor = max(0.0, min(1.0, mean(numeric_scores))) if numeric_scores else 0.2
    source_factor = min(len(sources) / 4.0, 1.0)
    validation_factor = 1.0 if approved else 0.2
    confidence = (0.6 * retrieval_factor) + (0.25 * source_factor) + (0.15 * validation_factor)
    return round(max(0.0, min(1.0, confidence)), 2)
