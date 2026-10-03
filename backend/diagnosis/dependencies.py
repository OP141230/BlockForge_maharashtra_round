"""Dependency Graph and Downstream Impact Engine for BLACKBOX.

Analyzes causal relationships, downstream reachability, and failure cascade propagation.
"""
from typing import Any, Dict, List, Set, Tuple


class DependencyEngine:
    """Builds DAG of execution steps and computes cascade propagation metrics."""

    @staticmethod
    def build_graph(steps: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
        """
        Build adjacency list {step_id: set_of_downstream_step_ids}.
        Infer causal links from explicit dependencies or sequential input/output flow.
        """
        adjacency: Dict[str, Set[str]] = {s["id"]: set() for s in steps}
        step_by_id = {s["id"]: s for s in steps}

        # First connect explicit dependencies
        for step in steps:
            deps = step.get("dependencies", []) or []
            for dep_id in deps:
                if dep_id in adjacency:
                    adjacency[dep_id].add(step["id"])

        # Also sequential causal chain inference for adjacent pipeline steps
        sorted_steps = sorted(steps, key=lambda s: s.get("step_index", 0))
        for i in range(len(sorted_steps) - 1):
            curr_id = sorted_steps[i]["id"]
            next_id = sorted_steps[i + 1]["id"]
            adjacency[curr_id].add(next_id)

        return adjacency

    @classmethod
    def get_descendants(cls, start_id: str, adjacency: Dict[str, Set[str]]) -> Set[str]:
        """Traverse graph to find all downstream descendants of a step."""
        visited: Set[str] = set()
        queue = [start_id]
        while queue:
            node = queue.pop(0)
            for child in adjacency.get(node, set()):
                if child not in visited:
                    visited.add(child)
                    queue.append(child)
        return visited

    @classmethod
    def evaluate_step(
        cls,
        step_dict: Dict[str, Any],
        all_steps: List[Dict[str, Any]],
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Evaluate downstream impact of a step.
        Returns: (impact_score: 0.0 - 1.0, impact_evidence: Dict)
        """
        adjacency = cls.build_graph(all_steps)
        descendants = cls.get_descendants(step_dict["id"], adjacency)

        steps_by_id = {s["id"]: s for s in all_steps}
        failed_steps = [s for s in all_steps if s.get("status") == "FAILED" or s.get("error_text")]
        total_failures = len(failed_steps)

        # Count how many failed steps lie downstream
        downstream_failed_ids = [fid for fid in descendants if fid in steps_by_id and steps_by_id[fid].get("status") == "FAILED"]
        downstream_fail_count = len(downstream_failed_ids)

        if total_failures == 0:
            impact_score = 0.0
        else:
            # Score proportional to how many failures this step is upstream from
            fraction_of_failures = downstream_fail_count / total_failures
            fanout_factor = min(1.0, len(descendants) / max(len(all_steps) - 1, 1))
            impact_score = min(1.0, fraction_of_failures * 0.7 + fanout_factor * 0.3)

            # If the step itself has errors and is upstream, high impact
            if step_dict.get("is_root_suspect"):
                impact_score = max(impact_score, 0.85)

        cascade_names = [steps_by_id[d].get("step_name") for d in descendants if d in steps_by_id]
        evidence = {
            "downstream_step_count": len(descendants),
            "downstream_failures": downstream_fail_count,
            "cascade_path": cascade_names,
            "impact_level": "HIGH" if impact_score >= 0.7 else "MEDIUM" if impact_score >= 0.4 else "LOW",
            "details": f"Step is upstream of {len(descendants)} execution nodes and {downstream_fail_count} downstream failure events.",
        }

        return round(impact_score, 3), evidence
