"""
Domain: Scheduling (HR / Resource Planning)
Maps raw employee/shift input → common schema.
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
    Map raw employee/shift payload to common schema.
    Input can be:
      - Employees/Workers (list of dicts) with Name, Duration, Hours
      - Or Items (list of names) + Durations/Hours
    """
    items = raw_params.get("Employees", raw_params.get("Workers", raw_params.get("Items", [])))
    shifts = raw_params.get("Shifts", raw_params.get("Slots", []))

    if isinstance(items, list) and items and isinstance(items[0], dict):
        names = [x.get("Name", x.get("id", f"E_{i}")) for i, x in enumerate(items)]
        durations = [float(x.get("Duration", x.get("Hours", 8))) for x in items]
    else:
        names = list(raw_params.get("Items", []))
        durations = raw_params.get("Durations", raw_params.get("Hours", [8] * len(names)))

    n = len(names)
    demands = raw_params.get("Demands", raw_params.get("MinStaff", {}))
    sense = raw_params.get("Sense", "maximize")

    if not shifts:
        shifts = list(demands.keys()) if demands else []

    return {
        "Items": names,
        "Weights": _safe_list(durations, n),
        "Values": raw_params.get("Values", raw_params.get("Satisfaction", [1] * n)),
        "Demands": demands,
        "Sense": sense,
        "Shifts": shifts,
        "MaxShiftsPerEmployee": int(raw_params.get("MaxShiftsPerEmployee", 1)),
        "Rules": raw_params.get("Rules", raw_params.get("Constraints", [])),
        "Mode": "scheduling",
    }
