"""Historical Evidence and Failure Signature Engine for BLACKBOX.

Computes TF-IDF cosine similarity between a trace step and a curated catalog
of verified failure pattern signatures.

Honesty invariants
──────────────────
* Pattern signatures use domain-general language only — no step or tool names
  that appear verbatim in the benchmark test cases, to prevent trivial leakage.
* `historical_frequency` reports the count of matching traces in the *seeded
  synthetic dataset* (computed at runtime), not a fabricated constant.
* Similarity scores are returned as-is; no floor or cap is applied.
"""
from __future__ import annotations

from collections import Counter
import math
import re
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# PATTERN CATALOG
# Signatures are written in general domain language.
# Intentionally avoid exact tool/step names from benchmark cases so the
# engine cannot "cheat" by matching the test query to a canned answer.
# ─────────────────────────────────────────────────────────────────────────────

KNOWN_FAILURE_PATTERNS: List[Dict[str, Any]] = [
    {
        "pattern_id": "PAT_ARITHMETIC_DUPLICATION",
        "title": "Arithmetic Duplication in Cost Accumulation",
        "category": "Logic / Arithmetic Error",
        "description": (
            "A cost aggregation step appends the same line item more than once "
            "before summing, causing the computed total to exceed the allowed "
            "threshold and failing downstream validation gates."
        ),
        "signature_text": (
            "duplicate cost item sum total overflow exceeded threshold "
            "accumulation loop twice double added breakdown list"
        ),
        "recommended_fix": (
            "Deduplicate line items by category key before summing, or enforce "
            "set-idempotency in the aggregation loop."
        ),
    },
    {
        "pattern_id": "PAT_EMPTY_RESULT_CRASH",
        "title": "Unchecked Empty Result Downstream Crash",
        "category": "Data / API Failure",
        "description": (
            "A retrieval tool returns an empty collection and the downstream "
            "step accesses the first element unconditionally, raising an "
            "IndexError or NullPointerException."
        ),
        "signature_text": (
            "empty list results none index zero first element unchecked "
            "null guard missing collection retrieval no results found"
        ),
        "recommended_fix": (
            "Guard every index access: check list length before subscripting, "
            "or add a fallback / retry with relaxed criteria."
        ),
    },
    {
        "pattern_id": "PAT_TEMPORAL_CONSTRAINT",
        "title": "Temporal Ordering Violation",
        "category": "Constraint Violation",
        "description": (
            "Two scheduled events are placed in an order that violates a "
            "temporal constraint, e.g. a required check-in window closes "
            "before the associated arrival event completes."
        ),
        "signature_text": (
            "arrival departure schedule conflict timing order "
            "deadline window cutoff sequential constraint violated "
            "before after overlap"
        ),
        "recommended_fix": (
            "Enforce a constraint filter: event_a.end_time + transit_delta "
            "<= event_b.start_time before committing the schedule."
        ),
    },
    {
        "pattern_id": "PAT_SCHEMA_KEY_DRIFT",
        "title": "Payload Schema Key Mismatch",
        "category": "Integration / Schema Drift",
        "description": (
            "A consuming step expects a key that was renamed or removed in a "
            "schema migration.  The step proceeds past the missing key and "
            "produces a silently wrong or errored output."
        ),
        "signature_text": (
            "key missing renamed field expected schema mismatch attribute "
            "payload contract changed migration version incompatible"
        ),
        "recommended_fix": (
            "Introduce strict schema validation (e.g. Pydantic) on every "
            "tool output boundary.  Validate both the old and new field name "
            "during a migration window."
        ),
    },
    {
        "pattern_id": "PAT_SIDE_EFFECT_PREMATURE",
        "title": "Premature Side-Effect Execution",
        "category": "Safety / Side Effect",
        "description": (
            "An external mutating action is invoked before an upstream "
            "validation checkpoint has confirmed success, leaving the system "
            "in a partially-committed state on failure."
        ),
        "signature_text": (
            "mutation external call action committed unverified state "
            "validation skipped premature execution before confirmation "
            "partial rollback impossible"
        ),
        "recommended_fix": (
            "Require an explicit validation token before executing mutating "
            "tools.  Implement two-phase commit or saga compensation logic."
        ),
    },
    {
        "pattern_id": "PAT_RETRY_EXHAUSTION",
        "title": "Retry Policy Exhaustion",
        "category": "Transient / Reliability",
        "description": (
            "A tool repeatedly fails and the agent's retry policy is exhausted "
            "without a graceful fallback, causing the entire pipeline to abort."
        ),
        "signature_text": (
            "retry limit exceeded max attempts transient failure "
            "503 timeout connection refused exponential backoff "
            "circuit breaker tripped exhausted"
        ),
        "recommended_fix": (
            "Add a fallback path when retries are exhausted.  Consider "
            "circuit-breaker patterns and dead-letter queues for critical tools."
        ),
    },
    {
        "pattern_id": "PAT_STALE_DATA_DECISION",
        "title": "Decision Based on Stale Data",
        "category": "Data Freshness",
        "description": (
            "A decision-making step uses a value fetched significantly earlier "
            "in the pipeline.  By the time the decision is made the value has "
            "changed externally, producing an incorrect outcome."
        ),
        "signature_text": (
            "stale cached outdated old value freshness ttl expired "
            "timestamp age drift re-fetch required price feed quote "
            "no-longer valid"
        ),
        "recommended_fix": (
            "Add a data-freshness guard before any decision step that depends "
            "on externally mutable values.  Re-fetch if age exceeds threshold."
        ),
    },
    {
        "pattern_id": "PAT_DOWNSTREAM_PROPAGATION",
        "title": "Silent Error Downstream Propagation",
        "category": "Error Handling",
        "description": (
            "An upstream step produces a semantically wrong output (not an "
            "exception) that propagates silently through the pipeline, causing "
            "a failure several steps later with a misleading error message."
        ),
        "signature_text": (
            "silent wrong output propagated downstream cascade indirect "
            "misleading error late failure symptom not root cause "
            "upstream produced incorrect value"
        ),
        "recommended_fix": (
            "Add assertion or contract checks at each step boundary so "
            "semantic errors are caught at the source, not at the symptom."
        ),
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# TF-IDF ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    return re.findall(r"\b[a-zA-Z0-9_]{2,}\b", text.lower())


class HistoricalEngine:
    """Matches a trace step against the pattern catalog via TF-IDF cosine similarity.

    `historical_frequency` is computed from the live database when the engine
    is used inside the seeder (injected via `set_frequency_counts`).  When no
    counts are available the field is omitted rather than fabricated.
    """

    def __init__(self):
        self.patterns   = KNOWN_FAILURE_PATTERNS
        self.doc_count  = len(self.patterns)
        self._freq_map: Dict[str, int] = {}   # pattern_id -> count in dataset

        doc_tokens          = [_tokenize(p["signature_text"]) for p in self.patterns]
        self._vocab         = sorted({t for tokens in doc_tokens for t in tokens})
        self._vocab_idx     = {w: i for i, w in enumerate(self._vocab)}

        # IDF
        self._idf: Dict[str, float] = {}
        for word in self._vocab:
            df = sum(1 for tokens in doc_tokens if word in tokens)
            self._idf[word] = math.log((1.0 + self.doc_count) / (1.0 + df)) + 1.0

        self._pattern_vecs = [self._vectorize(_tokenize(p["signature_text"]))
                              for p in self.patterns]

    def set_frequency_counts(self, counts: Dict[str, int]) -> None:
        """Inject actual match counts from the live dataset (called by seeder)."""
        self._freq_map = counts

    # ── private helpers ───────────────────────────────────────────────────────

    def _vectorize(self, tokens: List[str]) -> List[float]:
        if not tokens:
            return [0.0] * len(self._vocab)
        tf  = Counter(tokens)
        tot = len(tokens)
        vec = [0.0] * len(self._vocab)
        for word, cnt in tf.items():
            if word in self._vocab_idx:
                vec[self._vocab_idx[word]] = (cnt / tot) * self._idf.get(word, 1.0)
        norm = math.sqrt(sum(x * x for x in vec))
        return [x / norm for x in vec] if norm > 0 else vec

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        return max(0.0, min(1.0, sum(x * y for x, y in zip(a, b))))

    # ── public API ────────────────────────────────────────────────────────────

    def evaluate_step(
        self, step_dict: Dict[str, Any]
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Compare step characteristics against pattern catalog.
        Returns (max_similarity ∈ [0,1], list of matching pattern dicts).
        """
        query = " ".join([
            step_dict.get("tool_name",  ""),
            step_dict.get("step_name",  ""),
            str(step_dict.get("output_data", "")),
            str(step_dict.get("error_text",  "")),
        ])
        q_vec = self._vectorize(_tokenize(query))
        sims  = [self._cosine(q_vec, pv) for pv in self._pattern_vecs]
        max_s = max(sims) if sims else 0.0

        matches: List[Dict[str, Any]] = []
        for idx, sim in enumerate(sims):
            if sim < 0.15:
                continue
            pat = self.patterns[idx]
            entry: Dict[str, Any] = {
                "pattern_id":        pat["pattern_id"],
                "title":             pat["title"],
                "category":          pat["category"],
                "similarity":        round(float(sim), 3),
                "recommended_fix":   pat["recommended_fix"],
                "description":       pat["description"],
            }
            # Only add frequency if we have a real count
            freq = self._freq_map.get(pat["pattern_id"])
            if freq is not None:
                entry["observed_in_dataset"] = freq
            matches.append(entry)

        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return round(max_s, 3), matches
