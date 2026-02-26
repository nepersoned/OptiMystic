"""
Domain: Resource Allocation (IT / Cloud)
Maps raw resource/task input → common schema with CPU/RAM dimensions.
"""
from typing import Any, Dict, List


def _safe_list(values: List[Any], length: int, default: float = 0.0) -> List[Any]:
    if not isinstance(values, list):
        return [default] * length
    if len(values) >= length:
        return values[:length]
    return values + [default] * (length - len(values))


def map_params(raw_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map raw resource/task payload to common schema.
    Input can be:
      - Containers/Tasks (list of dicts) with CPU, RAM, Name, Cost
      - Or Items (list of names) + CPU + RAM + Values lists
    """
    items = raw_params.get("Containers", raw_params.get("Tasks", raw_params.get("Items", [])))
    
    if isinstance(items, list) and items and isinstance(items[0], dict):
        names = [x.get("Name", x.get("id", f"Task_{i}")) for i, x in enumerate(items)]
        cpu = [float(x.get("CPU", x.get("Cpu", 0))) for x in items]
        ram = [float(x.get("RAM", x.get("Memory", 0))) for x in items]
        values = [float(x.get("Cost", x.get("Priority", 0))) for x in items]
    else:
        names = list(raw_params.get("Items", []))
        cpu = raw_params.get("CPU", raw_params.get("Cpu", [0] * len(names)))
        ram = raw_params.get("RAM", raw_params.get("Memory", [0] * len(names)))
        values = raw_params.get("Values", raw_params.get("Costs", [0] * len(names)))

    n = len(names)
    servers = raw_params.get("Servers", raw_params.get("Nodes", [{"CPU": 64, "RAM": 128}]))
    if isinstance(servers, dict):
        servers = [servers]
    capacity_cpu = servers[0].get("CPU", servers[0].get("Cpu", 64)) if servers else 64
    capacity_ram = servers[0].get("RAM", servers[0].get("Memory", 128)) if servers else 128
    sense = raw_params.get("Sense", "minimize")

    return {
        "Items": names,
        "Weights": _safe_list(cpu, n),
        "WeightsRAM": _safe_list(ram, n),
        "Values": _safe_list(values, n),
        "Demands": raw_params.get("Demands", {name: 1 for name in names}),
        "Capacity": capacity_cpu,
        "CapacityRAM": capacity_ram,
        "Sense": sense,
        "Servers": servers,
        "Mode": "resourcing",
    }
