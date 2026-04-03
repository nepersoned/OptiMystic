"""
Domain: Vehicle Routing Problem (VRP)
Maps raw routing payload to a normalized OR-Tools-friendly contract.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _safe_list(values: Any, length: int, default: float = 0.0) -> List[Any]:
    if not isinstance(values, list):
        return [default] * length
    if len(values) >= length:
        return values[:length]
    return values + [default] * (length - len(values))


def _normalize_node(raw_node: Dict[str, Any], index: int) -> Dict[str, Any]:
    name = str(raw_node.get("Name", raw_node.get("name", f"Node_{index}"))).strip() or f"Node_{index}"
    return {
        "name": name,
        "demand": _safe_float(raw_node.get("Demand", raw_node.get("demand", 0.0)), 0.0),
        "x": _safe_float(raw_node.get("X", raw_node.get("x", raw_node.get("lon", 0.0))), 0.0),
        "y": _safe_float(raw_node.get("Y", raw_node.get("y", raw_node.get("lat", 0.0))), 0.0),
        "service_time": _safe_float(raw_node.get("ServiceTime", raw_node.get("service_time", 0.0)), 0.0),
        "ready_time": _safe_float(raw_node.get("ReadyTime", raw_node.get("ready_time", 0.0)), 0.0),
        "due_time": _safe_float(raw_node.get("DueTime", raw_node.get("due_time", 0.0)), 0.0),
    }


def _build_distance_matrix(nodes: List[Dict[str, Any]], raw_params: Dict[str, Any]) -> List[List[int]]:
    matrix = raw_params.get("DistanceMatrix", raw_params.get("distance_matrix"))
    if isinstance(matrix, list) and matrix:
        normalized: List[List[int]] = []
        for row in matrix:
            if not isinstance(row, list):
                continue
            normalized.append([max(0, _safe_int(value, 0)) for value in row])
        if normalized:
            return normalized

    if not nodes:
        return []

    matrix = []
    for left in nodes:
        row = []
        for right in nodes:
            distance = math.hypot(left["x"] - right["x"], left["y"] - right["y"])
            row.append(int(round(distance * 1000)))
        matrix.append(row)
    return matrix


def _build_time_matrix(nodes: List[Dict[str, Any]], raw_params: Dict[str, Any]) -> List[List[int]]:
    matrix = raw_params.get("TimeMatrix", raw_params.get("time_matrix"))
    if isinstance(matrix, list) and matrix:
        normalized: List[List[int]] = []
        for row in matrix:
            if not isinstance(row, list):
                continue
            normalized.append([max(0, _safe_int(value, 0)) for value in row])
        if normalized:
            return normalized

    if not nodes:
        return []

    matrix = []
    for left in nodes:
        row = []
        for right in nodes:
            travel = math.hypot(left["x"] - right["x"], left["y"] - right["y"])
            row.append(max(0, int(round(travel))))
        matrix.append(row)
    return matrix


def _resolve_depot_index(raw_params: Dict[str, Any], nodes: List[Dict[str, Any]]) -> int:
    depot = raw_params.get("Depot", raw_params.get("depot"))
    if isinstance(depot, int):
        return max(0, min(_safe_int(depot, 0), max(0, len(nodes) - 1)))
    if isinstance(depot, dict):
        depot_name = str(depot.get("Name", depot.get("name", ""))).strip()
        if depot_name:
            for index, node in enumerate(nodes):
                if node["name"] == depot_name:
                    return index
    return 0


def map_params(raw_params: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize routing payload to a common VRP contract."""
    raw_params = dict(raw_params or {})

    raw_nodes = raw_params.get("Nodes", raw_params.get("Locations", raw_params.get("Customers", [])))
    if isinstance(raw_nodes, dict):
        raw_nodes = [raw_nodes]
    if not isinstance(raw_nodes, list):
        raw_nodes = []

    nodes = [_normalize_node(node, index) for index, node in enumerate(raw_nodes) if isinstance(node, dict)]
    if not nodes:
        depot = _normalize_node({"Name": "Depot", "Demand": 0.0, "X": 0.0, "Y": 0.0}, 0)
        nodes = [depot]

    depot_index = _resolve_depot_index(raw_params, nodes)
    distance_matrix = _build_distance_matrix(nodes, raw_params)
    if not distance_matrix:
        distance_matrix = [[0 for _ in nodes] for _ in nodes]

    time_matrix = _build_time_matrix(nodes, raw_params)

    vehicles_raw = raw_params.get("Vehicles", raw_params.get("Fleet", []))
    if isinstance(vehicles_raw, dict):
        vehicles_raw = [vehicles_raw]
    if not isinstance(vehicles_raw, list) or not vehicles_raw:
        vehicles_raw = [{"Name": f"Vehicle_{i}", "Capacity": 1.0} for i in range(max(1, len(nodes) - 1))]

    vehicles: List[Dict[str, Any]] = []
    capacities: List[float] = []
    for index, vehicle in enumerate(vehicles_raw):
        if not isinstance(vehicle, dict):
            continue
        name = str(vehicle.get("Name", vehicle.get("name", f"Vehicle_{index}"))).strip() or f"Vehicle_{index}"
        capacity = _safe_float(vehicle.get("Capacity", vehicle.get("capacity", 1.0)), 1.0)
        start_index = _safe_int(vehicle.get("StartIndex", vehicle.get("start_index", depot_index)), depot_index)
        end_index = _safe_int(vehicle.get("EndIndex", vehicle.get("end_index", depot_index)), depot_index)
        vehicles.append({"name": name, "capacity": capacity, "start_index": start_index, "end_index": end_index})
        capacities.append(capacity)

    if not vehicles:
        vehicles = [{"name": "Vehicle_0", "capacity": 1.0, "start_index": depot_index, "end_index": depot_index}]
        capacities = [1.0]

    demands = [node["demand"] for node in nodes]
    demands[depot_index] = 0.0

    time_windows = []
    service_times = []
    for node in nodes:
        ready_time = _safe_float(node.get("ready_time", 0.0), 0.0)
        due_time = _safe_float(node.get("due_time", 0.0), 0.0)
        if due_time <= 0 and ready_time > 0:
            due_time = ready_time + 1000.0
        if due_time <= 0:
            due_time = 100000.0
        time_windows.append([ready_time, due_time])
        service_times.append(_safe_float(node.get("service_time", 0.0), 0.0))

    pickup_deliveries_raw = raw_params.get("PickupDeliveries", raw_params.get("pickup_deliveries", raw_params.get("Pairs", [])))
    pickup_deliveries = []
    if isinstance(pickup_deliveries_raw, list):
        for item in pickup_deliveries_raw:
            if not isinstance(item, dict):
                continue
            pickup = item.get("Pickup", item.get("pickup"))
            delivery = item.get("Delivery", item.get("delivery"))
            if isinstance(pickup, int) and isinstance(delivery, int):
                pickup_deliveries.append([max(0, min(pickup, len(nodes) - 1)), max(0, min(delivery, len(nodes) - 1))])

    drop_penalty = _safe_int(raw_params.get("DropPenalty", raw_params.get("drop_penalty", 100000)), 100000)
    allow_dropping = bool(raw_params.get("AllowDropping", raw_params.get("allow_dropping", True)))
    time_horizon = _safe_int(raw_params.get("TimeHorizon", raw_params.get("time_horizon", 100000)), 100000)

    mapped = {
        "Mode": "vrp",
        "VRP": {
            "nodes": nodes,
            "distance_matrix": distance_matrix,
            "distance_scale": 1.0 if isinstance(raw_params.get("DistanceMatrix", raw_params.get("distance_matrix")), list) else 1000.0,
            "time_matrix": time_matrix,
            "depot_index": depot_index,
            "vehicles": vehicles,
            "vehicle_capacities": capacities,
            "demands": demands,
            "time_windows": time_windows,
            "service_times": service_times,
            "pickup_deliveries": pickup_deliveries,
            "allow_dropping": allow_dropping,
            "drop_penalty": drop_penalty,
            "time_horizon": time_horizon,
            "time_limit_seconds": _safe_float(raw_params.get("TimeLimit", raw_params.get("time_limit", 10)), 10.0),
            "seed": _safe_int(raw_params.get("Seed", raw_params.get("seed", 0)), 0),
        },
        "Sense": str(raw_params.get("Sense", "minimize")).strip().lower() or "minimize",
    }
    mapped["Nodes"] = nodes
    mapped["Vehicles"] = vehicles
    mapped["DistanceMatrix"] = distance_matrix
    mapped["TimeMatrix"] = time_matrix
    mapped["DepotIndex"] = depot_index
    mapped["Demands"] = demands
    mapped["TimeWindows"] = time_windows
    mapped["ServiceTimes"] = service_times
    mapped["PickupDeliveries"] = pickup_deliveries
    return mapped