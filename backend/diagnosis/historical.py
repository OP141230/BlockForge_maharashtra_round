"""Historical Evidence and Failure Signature Engine for BLACKBOX.

Computes similarity against known verified failure patterns and recurrence clusters
using robust mathematical TF-IDF vectorization and cosine similarity.
"""
from collections import Counter
import math
import re
from typing import Any, Dict, List, Tuple


KNOWN_FAILURE_PATTERNS = [
    {
        "pattern_id": "PAT_ARITHMETIC_DUPLICATION",
        "title": "Arithmetic Duplication in Budget Accumulation",
        "category": "Logic / Arithmetic Error",
        "description": "Agent accumulates budget items by appending duplicate accommodation or flight entries into the sum loop, resulting in premature budget exhaustion.",
        "signature_text": "budget calculation duplicate double hotel accommodation cost total exceeds limit overflow price sum breakdown",
        "historical_frequency": "42 occurrences in historical traces",
        "recommended_fix": "Deduplicate line items before summing or enforce category set idempotency in budget_calculation.",
    },
    {
        "pattern_id": "PAT_EMPTY_LOOKUP_CASCADE",
        "title": "Unchecked Empty Lookup Downstream Crash",
        "category": "Data / API Failure",
        "description": "Search tool returns an empty list for criteria, and downstream node accesses index [0] without fallback or null check.",
        "signature_text": "search flight hotel empty results list index out of range null none lookup empty array",
        "historical_frequency": "28 occurrences in historical traces",
        "recommended_fix": "Add fallback date relaxation or conditional existence guard before indexing query results.",
    },
    {
        "pattern_id": "PAT_CHRONO_INVERSION",
        "title": "Temporal Order Conflict",
        "category": "Constraint Violation",
        "description": "Flight arrival timestamp occurs later than scheduled check-in window or appointment start time.",
        "signature_text": "arrival time checkin time after deadline arrival schedule conflict temporal mismatch hotel check-in cutoff",
        "historical_frequency": "19 occurrences in historical traces",
        "recommended_fix": "Enforce constraint filter: flight.arrival_time + transit_delta <= hotel.checkin_time.",
    },
    {
        "pattern_id": "PAT_SCHEMA_KEY_DRIFT",
        "title": "Database / Payload Schema Mismatch",
        "category": "Integration / Schema",
        "description": "Agent assumes legacy key structure (e.g. 'flight_id') when tool returns migrated schema ('id' or 'flight_code').",
        "signature_text": "KeyError schema missing field flight_id expected dict key mismatch attribute error database query",
        "historical_frequency": "34 occurrences in historical traces",
        "recommended_fix": "Introduce strict Pydantic model validation on tool output boundaries.",
    },
    {
        "pattern_id": "PAT_SIDE_EFFECT_LEAK",
        "title": "Unvalidated Side Effect Triggering",
        "category": "Safety / Side Effect",
        "description": "Agent triggers external mutating action (e.g. send_email, make_payment) before validating intermediate validation constraints.",
        "signature_text": "send_email make_payment book_flight side effect mutation external api unverified state",
        "historical_frequency": "15 occurrences in historical traces",
        "recommended_fix": "Enforce two-phase commit or require explicit validation token before executing side-effect tools.",
    },
]


def _tokenize(text: str) -> List[str]:
    """Tokenize alphanumeric words."""
    return re.findall(r"\b[a-zA-Z0-9_]{2,}\b", text.lower())


class HistoricalEngine:
    """Matches trace steps with historical failure pattern corpus via TF-IDF vector similarity."""

    def __init__(self):
        self.patterns = KNOWN_FAILURE_PATTERNS
        self.doc_count = len(self.patterns)
        
        # Build vocabulary and doc frequencies
        self.doc_tokens = [_tokenize(p["signature_text"]) for p in self.patterns]
        self.vocab = sorted(list({token for tokens in self.doc_tokens for token in tokens}))
        self.vocab_idx = {word: i for i, word in enumerate(self.vocab)}
        
        # Calculate IDF
        self.idf = {}
        for word in self.vocab:
            df = sum(1 for tokens in self.doc_tokens if word in tokens)
            self.idf[word] = math.log((1.0 + self.doc_count) / (1.0 + df)) + 1.0

        # Calculate TF-IDF vectors for known patterns
        self.pattern_vectors = [self._vectorize(tokens) for tokens in self.doc_tokens]

    def _vectorize(self, tokens: List[str]) -> List[float]:
        """Convert token list into normalized TF-IDF vector."""
        if not tokens:
            return [0.0] * len(self.vocab)
        tf = Counter(tokens)
        total = len(tokens)
        vec = [0.0] * len(self.vocab)
        for word, count in tf.items():
            if word in self.vocab_idx:
                idx = self.vocab_idx[word]
                vec[idx] = (count / total) * self.idf.get(word, 1.0)
        
        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two unit vectors."""
        return max(0.0, min(1.0, sum(a * b for a, b in zip(vec1, vec2))))

    def evaluate_step(self, step_dict: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Evaluate historical similarity of a step's characteristics.
        Returns: (similarity_score: 0.0 - 1.0, matching_patterns: List[Dict])
        """
        tool_name = step_dict.get("tool_name", "")
        step_name = step_dict.get("step_name", "")
        output_str = str(step_dict.get("output_data", ""))
        error_str = str(step_dict.get("error_text", ""))

        query_tokens = _tokenize(f"{tool_name} {step_name} {output_str} {error_str}")
        query_vec = self._vectorize(query_tokens)

        similarities = [self._cosine_similarity(query_vec, pvec) for pvec in self.pattern_vectors]
        max_sim = max(similarities) if similarities else 0.0

        matches: List[Dict[str, Any]] = []
        for idx, sim in enumerate(similarities):
            if sim >= 0.15:
                pat = self.patterns[idx]
                matches.append({
                    "pattern_id": pat["pattern_id"],
                    "title": pat["title"],
                    "category": pat["category"],
                    "similarity": round(float(sim), 3),
                    "historical_frequency": pat["historical_frequency"],
                    "recommended_fix": pat["recommended_fix"],
                    "description": pat["description"],
                })

        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return round(max_sim, 3), matches
