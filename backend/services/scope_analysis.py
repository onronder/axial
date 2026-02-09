"""
Scope Analysis Service

Analyzes retrieval results for scope distribution and implements the Dominance Guard.
Determines whether to proceed with generation, annotate with scope context, or request clarification.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ScopeClassification(str, Enum):
    """Classification of scope distribution in retrieval results."""
    DOMINANT = "dominant"      # Single scope dominates (≥85%)
    CONTESTED = "contested"    # Primary scope has majority but not dominant (60-84%)
    FRAGMENTED = "fragmented"  # No clear winner (<60%)
    EMPTY = "empty"            # No results with scope information


@dataclass
class ScopeStats:
    """Statistics for a single scope in retrieval results."""
    scope_id: str
    count: int = 0
    score_sum: float = 0.0
    avg_score: float = 0.0
    docs: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if self.count > 0 and self.score_sum > 0:
            self.avg_score = self.score_sum / self.count


@dataclass
class ScopeAnalysisResult:
    """
    Result of scope distribution analysis.

    Used by the Dominance Guard to decide how to handle retrieval results.
    """
    classification: ScopeClassification
    primary_scope_id: str | None = None
    dominance_ratio: float = 0.0
    primary_scope_stats: ScopeStats | None = None
    secondary_scopes: list[ScopeStats] = field(default_factory=list)
    total_docs: int = 0
    scoped_docs: int = 0
    distribution: dict[str, ScopeStats] = field(default_factory=dict)

    @property
    def has_single_dominant_scope(self) -> bool:
        """True if one scope clearly dominates the results."""
        return self.classification == ScopeClassification.DOMINANT

    @property
    def requires_clarification(self) -> bool:
        """True if the system should ask user for scope clarification."""
        return self.classification == ScopeClassification.FRAGMENTED

    @property
    def should_annotate(self) -> bool:
        """True if the response should include scope context annotation."""
        return self.classification in (ScopeClassification.DOMINANT, ScopeClassification.CONTESTED)


# Configurable thresholds
DOMINANCE_THRESHOLD = 0.85  # ≥85% = DOMINANT
CONTESTED_THRESHOLD = 0.60  # 60-84% = CONTESTED, <60% = FRAGMENTED
MIN_SCORE_FOR_ANALYSIS = 0.3  # Ignore docs below this relevance score


def analyze_scope_distribution(
    docs: list[dict[str, Any]],
    dominance_threshold: float = DOMINANCE_THRESHOLD,
    contested_threshold: float = CONTESTED_THRESHOLD,
    min_score: float = MIN_SCORE_FOR_ANALYSIS,
) -> ScopeAnalysisResult:
    """
    Analyze the scope distribution of retrieved documents.

    Implements the Dominance Guard logic:
    - DOMINANT (≥85%): One scope clearly wins → proceed with generation + footnote
    - CONTESTED (60-84%): Primary has majority → proceed with annotation
    - FRAGMENTED (<60%): No clear winner → request clarification

    Args:
        docs: List of retrieved documents from hybrid_search
        dominance_threshold: Ratio threshold for DOMINANT classification (default 0.85)
        contested_threshold: Ratio threshold for CONTESTED classification (default 0.60)
        min_score: Minimum relevance score to include in analysis (default 0.3)

    Returns:
        ScopeAnalysisResult with classification and scope statistics
    """
    if not docs:
        return ScopeAnalysisResult(
            classification=ScopeClassification.EMPTY,
            total_docs=0,
            scoped_docs=0,
        )

    # Filter to high-relevance docs and group by scope
    scope_groups: dict[str, ScopeStats] = defaultdict(lambda: ScopeStats(scope_id=""))
    scoped_docs = 0

    for doc in docs:
        # Get relevance score (hybrid_search uses vector_score, match_documents uses similarity)
        score = doc.get("vector_score") or doc.get("similarity") or doc.get("combined_score", 0)

        # Skip low-relevance docs for scope analysis
        if score < min_score:
            continue

        # Extract scope_id (from new column or metadata fallback)
        scope_id = doc.get("scope_id")
        if not scope_id:
            metadata = doc.get("metadata") or {}
            scope_id = metadata.get("scope_id")

        # Skip docs without scope information
        if not scope_id:
            continue

        scoped_docs += 1

        # Initialize ScopeStats if first doc for this scope
        if not scope_groups[scope_id].scope_id:
            scope_groups[scope_id] = ScopeStats(scope_id=scope_id)

        stats = scope_groups[scope_id]
        stats.count += 1
        stats.score_sum += float(score)
        stats.docs.append(doc)
        stats.avg_score = stats.score_sum / stats.count

    # Handle case where no docs have scope information
    if scoped_docs == 0:
        return ScopeAnalysisResult(
            classification=ScopeClassification.EMPTY,
            total_docs=len(docs),
            scoped_docs=0,
        )

    # Convert to list and sort by count (primary metric) then by avg_score (tiebreaker)
    scope_list = sorted(
        scope_groups.values(),
        key=lambda s: (s.count, s.avg_score),
        reverse=True,
    )

    primary = scope_list[0]
    secondary = scope_list[1:] if len(scope_list) > 1 else []

    # Calculate dominance ratio
    dominance_ratio = primary.count / scoped_docs if scoped_docs > 0 else 0.0

    # Classify based on dominance ratio
    if dominance_ratio >= dominance_threshold:
        classification = ScopeClassification.DOMINANT
    elif dominance_ratio >= contested_threshold:
        classification = ScopeClassification.CONTESTED
    else:
        classification = ScopeClassification.FRAGMENTED

    logger.info(
        f"🔍 [ScopeAnalysis] Classification={classification.value}, "
        f"primary={primary.scope_id[:50]}..., ratio={dominance_ratio:.2%}, "
        f"scoped={scoped_docs}/{len(docs)} docs"
    )

    return ScopeAnalysisResult(
        classification=classification,
        primary_scope_id=primary.scope_id,
        dominance_ratio=dominance_ratio,
        primary_scope_stats=primary,
        secondary_scopes=secondary[:5],  # Top 5 secondary scopes
        total_docs=len(docs),
        scoped_docs=scoped_docs,
        distribution=dict(scope_groups),
    )


def get_scope_candidates_for_clarification(
    analysis: ScopeAnalysisResult,
    max_candidates: int = 5,
) -> list[dict[str, Any]]:
    """
    Extract scope candidates for clarification response.

    Returns simplified scope info suitable for the 300 Multiple Choices response.

    Args:
        analysis: ScopeAnalysisResult from analyze_scope_distribution
        max_candidates: Maximum number of candidates to return

    Returns:
        List of candidate dicts with id, count, and score_sum
    """
    candidates = []

    # Include primary scope
    if analysis.primary_scope_stats:
        candidates.append({
            "scope_id": analysis.primary_scope_stats.scope_id,
            "count": analysis.primary_scope_stats.count,
            "score_sum": round(analysis.primary_scope_stats.score_sum, 3),
            "avg_score": round(analysis.primary_scope_stats.avg_score, 3),
        })

    # Include secondary scopes
    for scope_stats in analysis.secondary_scopes[:max_candidates - 1]:
        candidates.append({
            "scope_id": scope_stats.scope_id,
            "count": scope_stats.count,
            "score_sum": round(scope_stats.score_sum, 3),
            "avg_score": round(scope_stats.avg_score, 3),
        })

    return candidates


def filter_docs_by_scope(
    docs: list[dict[str, Any]],
    scope_id: str,
) -> list[dict[str, Any]]:
    """
    Filter documents to only those from a specific scope.

    Used when user selects a scope from clarification options.

    Args:
        docs: List of retrieved documents
        scope_id: Canonical scope URI to filter by

    Returns:
        Filtered list of documents from the specified scope
    """
    filtered = []
    for doc in docs:
        doc_scope = doc.get("scope_id")
        if not doc_scope:
            metadata = doc.get("metadata") or {}
            doc_scope = metadata.get("scope_id")

        if doc_scope == scope_id:
            filtered.append(doc)

    return filtered
