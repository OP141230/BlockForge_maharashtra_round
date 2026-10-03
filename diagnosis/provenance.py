from typing import Any, Dict, List
from collections import deque

# Static analysis map of our Travel Agent's data flow.
# We use top-level state keys to ensure the graph remains fully connected.
STEP_READS = {
    "parse_request": [],
    "extract_constraints": ["parsed_request"],
    "search_flights": ["constraints"],
    "filter_flights_by_budget": ["flights", "constraints"],
    "select_cheapest_flight": ["filtered_flights"],
    "search_hotels": ["constraints"],
    "filter_hotels_by_checkin": ["hotels", "constraints"],
    "select_hotel": ["filtered_hotels"],
    "create_booking": ["selected_flight", "selected_hotel"],
    "validate_final_result": ["booking", "constraints"],
    "send_confirmation": ["final_validation", "booking"],
}

STEP_WRITES = {
    "parse_request": ["parsed_request"],
    "extract_constraints": ["constraints"],
    "search_flights": ["flights"],
    "filter_flights_by_budget": ["filtered_flights"],
    "select_cheapest_flight": ["selected_flight"],
    "search_hotels": ["hotels"],
    "filter_hotels_by_checkin": ["filtered_hotels"],
    "select_hotel": ["selected_hotel"],
    "create_booking": ["booking"],
    "validate_final_result": ["final_validation"],
    "send_confirmation": ["confirmation"],
}

# Maps final violations to the top-level state keys that caused them
VIOLATION_DEPENDENCIES = {
    "booking_missing": ["booking"],
    "flight_origin_mismatch": ["booking", "constraints"],
    "flight_destination_mismatch": ["booking", "constraints"],
    "flight_date_mismatch": ["booking", "constraints"],
    "flight_budget_violation": ["booking", "constraints"],
    "hotel_city_mismatch": ["booking", "constraints"],
    "hotel_date_mismatch": ["booking", "constraints"],
    "hotel_checkin_time_violation": ["booking", "constraints"],
}

def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}

def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []

def build_provenance_graph(trace: Dict[str, Any], report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Builds a directed acyclic graph (DAG) of the agent's execution.
    Nodes: steps, state keys, violations.
    Edges: reads, writes, causes.
    """
    trace = _safe_dict(trace)
    report = _safe_dict(report)
    
    nodes = []
    edges = []
    node_ids = set()
    
    def add_node(node_id: str, node_type: str, data: Any = None):
        if node_id not in node_ids:
            node_ids.add(node_id)
            nodes.append({"id": node_id, "type": node_type, "data": data})
            
    # 1. Add Step Nodes
    for step in _safe_list(trace.get("steps")):
        step = _safe_dict(step)
        name = step.get("name")
        if name:
            add_node(f"step:{name}", "step", step)
            
    # 2. Add State Nodes and Read/Write Edges
    for step in _safe_list(trace.get("steps")):
        step = _safe_dict(step)
        name = step.get("name")
        if not name: 
            continue
        
        for read_key in STEP_READS.get(name, []):
            add_node(f"state:{read_key}", "state")
            edges.append({"source": f"state:{read_key}", "target": f"step:{name}", "type": "reads"})
            
        for write_key in STEP_WRITES.get(name, []):
            add_node(f"state:{write_key}", "state")
            edges.append({"source": f"step:{name}", "target": f"state:{write_key}", "type": "writes"})
            
    # 3. Add Violation Nodes and Causal Edges
    for v in _safe_list(report.get("final_violations")):
        v = _safe_dict(v)
        v_name = v.get("violation")
        if v_name:
            add_node(f"violation:{v_name}", "violation", v)
            for dep in VIOLATION_DEPENDENCIES.get(v_name, []):
                add_node(f"state:{dep}", "state")
                edges.append({"source": f"state:{dep}", "target": f"violation:{v_name}", "type": "causes"})
                
    return {"nodes": nodes, "edges": edges}

def get_backward_slice(graph: Dict[str, Any], target_node_id: str) -> List[str]:
    """
    Traverses the graph backwards from a target (e.g., a violation) 
    to find all steps that contributed to it (the causal slice).
    """
    graph = _safe_dict(graph)
    edges = _safe_list(graph.get("edges"))
    
    # Build reverse adjacency list
    reverse_adj = {}
    for edge in edges:
        target = edge.get("target")
        source = edge.get("source")
        if target and source:
            reverse_adj.setdefault(target, []).append(source)
            
    visited = set()
    queue = deque([target_node_id])
    step_names = []
    
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        
        if current.startswith("step:"):
            step_names.append(current.split(":", 1)[1])
            
        for parent in reverse_adj.get(current, []):
            if parent not in visited:
                queue.append(parent)
                
    return step_names