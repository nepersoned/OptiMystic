"""Vehicle routing solver built on OR-Tools routing primitives."""
from __future__ import annotations

import time
from typing import Any, Dict, List

try:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
except ImportError:  # pragma: no cover - runtime dependency guard
    pywrapcp = None
    routing_enums_pb2 = None


def _parameter_map(parameters: Any) -> Dict[str, Any]:
    if isinstance(parameters, dict):
        return parameters
    if isinstance(parameters, list):
        mapped = {}
        for item in parameters:
            if isinstance(item, dict) and "name" in item:
                mapped[item["name"]] = item.get("data")
        return mapped
    return {}


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


def _extract_routes(solution, routing, manager, nodes, vehicles, distance_matrix, demands, distance_scale, time_dimension=None):
    routes: List[Dict[str, Any]] = []
    route_variables: List[Dict[str, Any]] = []
    total_distance = 0.0
    total_load = 0.0
    visited = set()

    for vehicle_index in range(routing.vehicles()):
        index = routing.Start(vehicle_index)
        route_nodes: List[str] = []
        route_distance = 0.0
        route_load = 0.0
        route_times: List[float] = []

        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            start_node = manager.IndexToNode(routing.Start(vehicle_index))
            if node_index != start_node:
                route_nodes.append(str(nodes[node_index]["name"]))
                visited.add(node_index)
                route_load += _safe_float(demands[node_index], 0.0)
                if time_dimension is not None:
                    try:
                        route_times.append(float(solution.Value(time_dimension.CumulVar(index))))
                    except Exception:
                        route_times.append(0.0)

            next_index = solution.Value(routing.NextVar(index))
            next_node_index = manager.IndexToNode(next_index)
            route_distance += _safe_float(distance_matrix[node_index][next_node_index], 0.0)
            index = next_index

        if vehicle_index < len(vehicles) and isinstance(vehicles[vehicle_index], dict):
            vehicle_name = str(vehicles[vehicle_index].get("name", f"Vehicle_{vehicle_index}"))
        else:
            vehicle_name = f"Vehicle_{vehicle_index}"

        routes.append({
            "vehicle": vehicle_name,
            "route": route_nodes,
            "distance": round(route_distance / distance_scale, 2),
            "load": round(route_load, 2),
            "arrival_times": [round(t, 2) for t in route_times],
        })
        total_distance += route_distance
        total_load += route_load
        for stop_index, stop_name in enumerate(route_nodes):
            route_variables.append({
                "Variable": f"Route_{vehicle_index}_{stop_index}",
                "Value": float(stop_index + 1),
                "vehicle": vehicle_name,
                "stop": stop_name,
            })

    starts = {manager.IndexToNode(routing.Start(idx)) for idx in range(routing.vehicles())}
    unserved = [str(nodes[index]["name"]) for index in range(len(nodes)) if index not in visited and index not in starts]
    return routes, route_variables, total_distance, total_load, unserved


def solve_vrp_model(store_data: Dict[str, Any], objective: Any = None) -> Dict[str, Any]:
    start = time.time()
    if pywrapcp is None:
        return {
            "status": "Error",
            "error_msg": "OR-Tools required for VRP. pip install ortools",
            "solve_time": time.time() - start,
        }

    parameters = _parameter_map(store_data.get("parameters", {}))
    spec = parameters.get("VRP") if isinstance(parameters.get("VRP"), dict) else {}
    if not spec:
        return {"status": "Error", "error_msg": "VRP spec missing", "solve_time": time.time() - start}

    nodes = list(spec.get("nodes", []))
    vehicles = list(spec.get("vehicles", []))
    distance_matrix = list(spec.get("distance_matrix", []))
    time_matrix = list(spec.get("time_matrix", distance_matrix))
    demands = list(spec.get("demands", []))
    capacities = list(spec.get("vehicle_capacities", []))
    distance_scale = _safe_float(spec.get("distance_scale", 1.0), 1.0) or 1.0
    time_windows = list(spec.get("time_windows", []))
    service_times = list(spec.get("service_times", []))
    pickup_deliveries = list(spec.get("pickup_deliveries", []))
    allow_dropping = bool(spec.get("allow_dropping", True))
    drop_penalty = _safe_int(spec.get("drop_penalty", 100000), 100000)
    time_horizon = max(1, _safe_int(spec.get("time_horizon", 100000), 100000))
    time_limit_seconds = max(1, _safe_int(spec.get("time_limit_seconds", 10), 10))
    seed = _safe_int(spec.get("seed", 0), 0)

    if not nodes:
        return {"status": "Error", "error_msg": "No VRP nodes provided", "solve_time": time.time() - start}
    if not vehicles:
        return {"status": "Error", "error_msg": "No VRP vehicles provided", "solve_time": time.time() - start}
    if not distance_matrix:
        return {"status": "Error", "error_msg": "VRP distance matrix missing", "solve_time": time.time() - start}

    starts = [max(0, min(_safe_int(vehicle.get("start_index", 0), 0), len(nodes) - 1)) if isinstance(vehicle, dict) else 0 for vehicle in vehicles]
    ends = [max(0, min(_safe_int(vehicle.get("end_index", 0), 0), len(nodes) - 1)) if isinstance(vehicle, dict) else 0 for vehicle in vehicles]
    manager = pywrapcp.RoutingIndexManager(len(nodes), len(vehicles), starts, ends)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(_safe_float(distance_matrix[from_node][to_node], 0.0))

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    if any(capacity > 0 for capacity in capacities) and demands:
        def demand_callback(from_index):
            node_index = manager.IndexToNode(from_index)
            return int(round(_safe_float(demands[node_index], 0.0)))

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        vehicle_capacities = [max(1, _safe_int(capacity, 1)) for capacity in capacities]
        routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, vehicle_capacities, True, "Capacity")

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        travel = _safe_float(time_matrix[from_node][to_node], 0.0)
        service = _safe_float(service_times[from_node] if from_node < len(service_times) else 0.0, 0.0)
        return int(round(travel + service))

    time_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.AddDimension(time_callback_index, time_horizon, time_horizon, False, "Time")
    time_dimension = routing.GetDimensionOrDie("Time")

    for node_index, window in enumerate(time_windows):
        if not isinstance(window, list) or len(window) < 2:
            continue
        start_window = max(0, _safe_int(window[0], 0))
        end_window = max(start_window, min(time_horizon, _safe_int(window[1], time_horizon)))
        time_dimension.CumulVar(manager.NodeToIndex(node_index)).SetRange(start_window, end_window)

    for vehicle_index, vehicle in enumerate(vehicles):
        if not isinstance(vehicle, dict):
            continue
        start_index = manager.NodeToIndex(starts[vehicle_index])
        end_index = manager.NodeToIndex(ends[vehicle_index])
        time_dimension.CumulVar(start_index).SetRange(0, time_horizon)
        time_dimension.CumulVar(end_index).SetRange(0, time_horizon)

    for pickup_delivery in pickup_deliveries:
        if not isinstance(pickup_delivery, list) or len(pickup_delivery) < 2:
            continue
        pickup = max(0, min(_safe_int(pickup_delivery[0], 0), len(nodes) - 1))
        delivery = max(0, min(_safe_int(pickup_delivery[1], 0), len(nodes) - 1))
        if pickup == delivery:
            continue
        pickup_index = manager.NodeToIndex(pickup)
        delivery_index = manager.NodeToIndex(delivery)
        routing.AddPickupAndDelivery(pickup_index, delivery_index)
        routing.solver().Add(routing.VehicleVar(pickup_index) == routing.VehicleVar(delivery_index))
        routing.solver().Add(time_dimension.CumulVar(pickup_index) <= time_dimension.CumulVar(delivery_index))

    if allow_dropping:
        for node_index in range(len(nodes)):
            if node_index in starts or node_index in ends:
                continue
            routing.AddDisjunction([manager.NodeToIndex(node_index)], drop_penalty)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.FromSeconds(time_limit_seconds)
    if seed > 0:
        search_parameters.random_seed = seed

    solution = routing.SolveWithParameters(search_parameters)
    if solution is None:
        return {
            "status": "Infeasible",
            "objective": None,
            "variables": [],
            "constraints": [],
            "routes": [],
            "unserved": [],
            "pickup_deliveries": pickup_deliveries,
            "time_windows_applied": bool(time_windows),
            "solve_time": time.time() - start,
            "lp_sensitivity": False,
        }

    routes, variables, total_distance, total_load, unserved = _extract_routes(
        solution,
        routing,
        manager,
        nodes,
        vehicles,
        distance_matrix,
        demands,
        distance_scale,
        time_dimension=time_dimension,
    )

    constraint_rows = []
    for vehicle_index, vehicle in enumerate(vehicles):
        route = routes[vehicle_index] if vehicle_index < len(routes) else {"load": 0.0}
        capacity = _safe_float(vehicle.get("capacity", 0.0), 0.0)
        load = _safe_float(route.get("load", 0.0), 0.0)
        constraint_rows.append({
            "Constraint": f"vehicle_capacity_{vehicle_index}",
            "Shadow Price": 0.0,
            "Slack": round(max(0.0, capacity - load), 2),
        })

    return {
        "status": "Optimal",
        "objective": round(total_distance / distance_scale, 2),
        "variables": variables,
        "constraints": constraint_rows,
        "routes": routes,
        "unserved": unserved,
        "total_distance": round(total_distance / distance_scale, 2),
        "total_load": round(total_load, 2),
        "num_vehicles": len(routes),
        "pickup_deliveries": pickup_deliveries,
        "time_windows_applied": bool(time_windows),
        "solve_time": time.time() - start,
        "lp_sensitivity": False,
    }