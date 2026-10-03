import glob
import json
import os
from typing import Any, Dict, List


def load_traces(base_dir: str = "data/traces") -> List[Dict[str, Any]]:
    """
    Loads all trace.json files from the trace directory.

    Expected structure:
        data/traces/<trace_id>/trace.json
    """
    pattern = os.path.join(base_dir, "*", "trace.json")
    paths = sorted(glob.glob(pattern))

    traces: List[Dict[str, Any]] = []

    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            trace = json.load(f)
        traces.append(trace)

    traces.sort(key=lambda trace: trace.get("trace_id", ""))
    return traces