"""
ORIGINAL: services.py from core/utils/ (before refactoring)

This file contains the complete original implementation of result processing.
Moved to _legacy_django for reference when implementing Go version.

Functions to port to Go:
1. _process_cutting_results() - 가장 복잡함
2. _process_generic_results() - Packing, Resourcing, Scheduling
3. process_sensitivity() - Sensitivity analysis
4. Helper functions for data transformation
"""

import re
from typing import Any, Dict, List, Tuple


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def build_parameter_store(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Turn params dict into list of {name, data} for store."""
    return [{"name": k, "data": v} for k, v in params.items()]


def _clean_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "_", str(name))


def process_results(
    res: Dict[str, Any],
    store: Dict[str, Any],
    mode: str | None = None,
) -> Dict[str, Any]:
    """Parse solver variables into bin plans and summary."""
    mode = (mode or "cutting").strip().lower()
    if mode in ("manufacturing", "cutting"):
        return _process_cutting_results(res, store)
    if mode == "logistics":
        mode = "packing"
    if mode in ("resource", "it", "cloud", "resource_allocation"):
        mode = "resource_allocation"
    if mode in ("hr", "nsp"):
        mode = "scheduling"
    if mode == "resourcing":
        mode = "resource_allocation"

    return _process_generic_results(res, store, mode)


def _process_cutting_results(
    res: Dict[str, Any],
    store: Dict[str, Any],
) -> Dict[str, Any]:
    """Process cutting results - MOST COMPLEX (reference for Go implementation)"""
    params_list = store.get("parameters", [])
    p = {x["name"]: x["data"] for x in params_list}
    items: List[str] = p.get("Items", [])
    lens: List[float] = p.get("ItemLens", [])
    stocks: List[Dict[str, Any]] = p.get("Stocks", [])
    kerf: float = safe_float(p.get("Kerf", 0))

    stock_map = {i: s for i, s in enumerate(stocks)}
    raw_bins: Dict[str, Dict[str, Any]] = {}
    total_cost = 0.0
    total_waste = 0.0
    cleaned_map = {_clean_name(it): i for i, it in enumerate(items)}

    if not res or not isinstance(res.get("variables"), list):
        return {
            "total_cost": 0.0,
            "total_waste": 0.0,
            "num_bins": 0,
            "bin_plans": [],
            "report": "No cutting plan generated.",
            "item_counts": {},
            "status": "no_solution",
        }

    for v in res["variables"]:
        val = safe_float(v.get("Value", 0))
        if val <= 0.001:
            continue

        varname = v.get("Variable", "")

        # Column-generation naming (A_IT...)
        if "A_IT" in varname:
            try:
                parts = varname.split("_")
                it_part = next(p for p in parts if p.startswith("IT"))
                item_idx = int(it_part.replace("IT", ""))
                bin_id = "_".join(parts[parts.index(it_part) + 1 :])
                s_idx = (
                    int(bin_id.split("_")[0].replace("ST", ""))
                    if "ST" in bin_id and "CG" not in bin_id
                    else 0
                )
                if bin_id not in raw_bins:
                    raw_bins[bin_id] = {"s_idx": s_idx, "items": []}
                for _ in range(int(round(val))):
                    raw_bins[bin_id]["items"].append({"name": items[item_idx], "len": lens[item_idx]})
            except (StopIteration, ValueError, IndexError, KeyError):
                continue

        # MIP naming (Cut_<Item>_<Bin>)
        elif varname.startswith("Cut_"):
            try:
                rem = varname[len("Cut_") :]
                pos = rem.rfind("_ST")
                if pos == -1:
                    pos = rem.rfind("_CG")
                if pos == -1:
                    parts = rem.rsplit("_", 1)
                    item_part = parts[0]
                    bin_id = parts[1] if len(parts) > 1 else "ST0"
                else:
                    item_part = rem[:pos]
                    bin_id = rem[pos + 1 :]

                clean_item = _clean_name(item_part)
                item_idx = cleaned_map.get(clean_item)
                if item_idx is None:
                    try:
                        item_idx = items.index(item_part)
                    except ValueError:
                        continue

                s_idx = int(bin_id.split("_")[0].replace("ST", "")) if "ST" in bin_id else 0
                if bin_id not in raw_bins:
                    raw_bins[bin_id] = {"s_idx": s_idx, "items": []}
                for _ in range(int(round(val))):
                    raw_bins[bin_id]["items"].append({"name": items[item_idx], "len": lens[item_idx]})
            except (ValueError, IndexError, KeyError):
                continue

    bin_plans: List[Dict[str, str]] = []
    for b_id in sorted(raw_bins.keys()):
        b_data = raw_bins[b_id]
        stock = stock_map.get(b_data["s_idx"], stocks[0] if stocks else {})
        total_cost += safe_float(stock.get("Cost", 0))
        current_pos = 0.0
        for i, item in enumerate(b_data["items"]):
            current_pos += item["len"]
            if kerf > 0 and i < len(b_data["items"]) - 1:
                current_pos += kerf
        waste = max(0.0, safe_float(stock.get("Length", 0)) - current_pos)
        total_waste += waste
        usage_pct = (current_pos / safe_float(stock.get("Length", 1))) * 100
        bin_plans.append({"Stock": stock.get("Name", ""), "Plan": f"{len(b_data['items'])} cut", "Usage": f"{usage_pct:.1f}%"})

    item_counts: Dict[str, int] = {}
    for b in raw_bins.values():
        for it in b["items"]:
            item_counts[it["name"]] = item_counts.get(it["name"], 0) + 1
    top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    report_lines = [
        "### Execution Summary",
        f"- **Total Material Cost:** ${total_cost:,.2f}",
        f"- **Total Scrap Generated:** {total_waste:,.1f} mm",
        f"- **Bins Used:** {len(raw_bins)}",
    ]
    for name, cnt in top_items:
        report_lines.append(f"- {name}: {cnt} pcs")
    report = "\n".join(report_lines)

    return {
        "total_cost": round(total_cost, 2),
        "total_waste": round(total_waste, 2),
        "num_bins": len(raw_bins),
        "bin_plans": bin_plans,
        "report": report,
        "item_counts": item_counts,
        "status": "ok",
    }


def _process_generic_results(
    res: Dict[str, Any],
    store: Dict[str, Any],
    mode: str,
) -> Dict[str, Any]:
    """Process generic results for all modes."""
    params_list = store.get("parameters", [])
    p = {x["name"]: x["data"] for x in params_list}
    items: List[str] = p.get("Items", [])
    var_values = {v.get("Variable", ""): safe_float(v.get("Value", 0)) for v in res.get("variables", [])}

    if mode == "packing":
        weights = p.get("Weights", [])
        values = p.get("Values", [])
        capacity = safe_float(p.get("Capacity", 0))
        selected = []
        used = 0.0
        total_value = 0.0

        for i, name in enumerate(items):
            qty = var_values.get(f"X_{i}", 0.0)
            if qty <= 0:
                continue
            weight = safe_float(weights[i] if i < len(weights) else 0)
            value = safe_float(values[i] if i < len(values) else 0)
            selected.append({"item": name, "count": qty, "weight": weight, "value": value})
            used += weight * qty
            total_value += value * qty

        usage_pct = (used / capacity * 100) if capacity > 0 else 0.0
        report = f"### Packing Summary\n- **Total Value:** {total_value:.2f}\n- **Used Capacity:** {used:.2f} / {capacity:.2f} ({usage_pct:.1f}%)"
        return {
            "mode": "packing",
            "total_value": round(total_value, 2),
            "used_capacity": round(used, 2),
            "capacity": round(capacity, 2),
            "items": selected,
            "report": report,
            "status": "ok",
        }

    return {"mode": mode, "report": "No dashboard available.", "status": "ok"}


def process_sensitivity(
    res: Dict[str, Any],
    store: Dict[str, Any],
    mode: str | None = None,
) -> Dict[str, Any]:
    """Build constraint/sensitivity summary from solver duals."""
    if not res.get("lp_sensitivity"):
        return {
            "constraints": [],
            "top_bottleneck": None,
            "insight": "Sensitivity available only for LP/CG models.",
        }
    return {"constraints": [], "top_bottleneck": None, "insight": ""}
