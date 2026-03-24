"""
Data cleaning, result summary, and JSON-friendly output for the solver.
Migrated from analytics_cutting.py: UI (Dash/Plotly) removed; logic only.
"""
import re
from typing import Any, Dict, List, Tuple


MODE_ALIASES = {
    "manufacturing": "cutting",
    "cutting": "cutting",
    "logistics": "packing",
    "packing": "packing",
    "resource": "resource_allocation",
    "it": "resource_allocation",
    "cloud": "resource_allocation",
    "resource_allocation": "resource_allocation",
    "resourcing": "resource_allocation",
    "hr": "scheduling",
    "nsp": "scheduling",
    "scheduling": "scheduling",
    "generic": "generic",
    "formula": "generic",
    "custom": "generic",
}

def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def normalize_mode(mode: str | None) -> str:
    return MODE_ALIASES.get((mode or "cutting").strip().lower(), (mode or "cutting").strip().lower())


def parameter_map(store: Dict[str, Any]) -> Dict[str, Any]:
    parameters = store.get("parameters", {}) if isinstance(store, dict) else {}
    if isinstance(parameters, dict):
        return parameters
    if isinstance(parameters, list):
        mapped: Dict[str, Any] = {}
        for item in parameters:
            if isinstance(item, dict) and "name" in item:
                mapped[item["name"]] = item.get("data")
        return mapped
    return {}


def get_params(data_inputs: Dict[str, Any], sense: str = "minimize") -> Dict[str, Any]:
    """
    Parse cutting UI payload into solver params. No UI dependencies.
    Returns: Items, ItemLens, Demands, Prices, Stocks, Sense, Kerf.
    """
    cut_data = data_inputs.get("cut_table", [])
    stock_data = data_inputs.get("cut_stock_table", [])
    kerf = safe_float(data_inputs.get("kerf_val", 0))

    items: List[str] = []
    item_lens: List[float] = []
    demands: Dict[str, float] = {}
    prices: Dict[str, float] = {}

    for r in cut_data:
        name = str(r.get("Item", "")).strip()
        if name and r.get("Length") is not None:
            items.append(name)
            item_lens.append(safe_float(r["Length"]))
            demands[name] = safe_float(r.get("Demand"))
            prices[name] = safe_float(r.get("Price", 0))

    stocks: List[Dict[str, Any]] = [
        {
            "Name": str(r.get("Name", f"ST_{i}")),
            "Length": safe_float(r.get("Length")),
            "Cost": safe_float(r.get("Cost", 100)),
            "Limit": safe_float(r.get("Limit", 500)),
        }
        for i, r in enumerate(stock_data)
        if r.get("Length") is not None
    ]

    return {
        "Items": items,
        "ItemLens": item_lens,
        "Demands": demands,
        "Prices": prices,
        "Stocks": stocks,
        "Sense": sense,
        "Kerf": kerf,
    }


def build_parameter_store(params: Dict[str, Any]) -> Dict[str, Any]:
    """Keep solver parameters as a plain dict."""
    return dict(params or {})


def normalize_solver_response(result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {"status": "Error", "error_msg": "Invalid solver response"}
    result.setdefault("variables", [])
    result.setdefault("constraints", [])
    return result


def split_objective_and_constraints(logic_output: Tuple[Any, Any, Any]) -> Tuple[Any, Any, Any]:
    obj, constraints, variables = logic_output
    return obj, constraints, variables


def _clean_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "_", str(name))


def _get_variable_name(variable: Dict[str, Any]) -> str:
    if not isinstance(variable, dict):
        return ""
    return str(variable.get("Variable") or variable.get("name") or "")


def _get_variable_value(variable: Dict[str, Any]) -> float:
    if not isinstance(variable, dict):
        return 0.0
    return safe_float(variable.get("Value", variable.get("value", 0.0)), 0.0)


def process_results(
    res: Dict[str, Any],
    store: Dict[str, Any],
    mode: str | None = None,
) -> Dict[str, Any]:
    """
    Parse solver variables into bin plans and summary.
    """
    mode = normalize_mode(mode)
    if mode == "cutting":
        return _process_cutting_results(res, store)
    return _process_generic_results(res, store, mode)


def _process_cutting_results(
    res: Dict[str, Any],
    store: Dict[str, Any],
) -> Dict[str, Any]:
    """Process cutting results."""
    p = parameter_map(store)
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
            "mode": "cutting",
            "total_cost": 0.0,
            "total_waste": 0.0,
            "num_bins": 0,
            "bin_plans": [],
            "report": "No cutting plan generated.",
            "item_counts": {},
            "status": "no_solution",
        }

    for v in res["variables"]:
        val = _get_variable_value(v)
        if val <= 0.001:
            continue

        # Prefer structured solver outputs when available.
        structured_item_idx = v.get("item_index") if isinstance(v, dict) else None
        structured_bin_id = v.get("bin_id") if isinstance(v, dict) else None
        if structured_item_idx is not None and structured_bin_id is not None:
            try:
                item_idx = int(structured_item_idx)
                bin_id = str(structured_bin_id)
                s_idx = (
                    int(bin_id.split("_")[0].replace("ST", ""))
                    if "ST" in bin_id and "CG" not in bin_id
                    else 0
                )
                if bin_id not in raw_bins:
                    raw_bins[bin_id] = {"s_idx": s_idx, "items": []}
                for _ in range(int(round(val))):
                    raw_bins[bin_id]["items"].append({"name": items[item_idx], "len": lens[item_idx]})
                continue
            except (TypeError, ValueError, IndexError, KeyError):
                pass

        varname = _get_variable_name(v)
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
        label = f"Bin {b_id}"
        for i, item in enumerate(b_data["items"]):
            current_pos += item["len"]
            if kerf > 0 and i < len(b_data["items"]) - 1:
                current_pos += kerf
        waste = max(0.0, safe_float(stock.get("Length", 0)) - current_pos)
        total_waste += waste
        usage_pct = (current_pos / safe_float(stock.get("Length", 1))) * 100
        bin_plans.append({"Stock": label, "Plan": f"{len(b_data['items'])} cut", "Usage": f"{usage_pct:.1f}%"})

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
        "mode": "cutting",
        "total_cost": round(total_cost, 2),
        "total_waste": round(total_waste, 2),
        "num_bins": len(raw_bins),
        "bin_plans": bin_plans,
        "report": report,
        "item_counts": item_counts,
        "raw_bins": raw_bins,
        "status": "ok",
    }


def _process_generic_results(
    res: Dict[str, Any],
    store: Dict[str, Any],
    mode: str,
) -> Dict[str, Any]:
    """Process generic results for all modes."""
    p = parameter_map(store)
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

    if mode == "resource_allocation":
        cpu = p.get("Weights", [])
        ram = p.get("WeightsRAM", [])
        values = p.get("Values", [])
        cap_cpu = safe_float(p.get("Capacity", 0))
        cap_ram = safe_float(p.get("CapacityRAM", 0))
        selected = []
        used_cpu = 0.0
        used_ram = 0.0
        total_value = 0.0

        for i, name in enumerate(items):
            qty = var_values.get(f"X_{i}", 0.0)
            if qty <= 0:
                continue
            cpu_i = safe_float(cpu[i] if i < len(cpu) else 0)
            ram_i = safe_float(ram[i] if i < len(ram) else 0)
            val_i = safe_float(values[i] if i < len(values) else 0)
            selected.append({"item": name, "count": qty, "cpu": cpu_i, "ram": ram_i, "value": val_i})
            used_cpu += cpu_i * qty
            used_ram += ram_i * qty
            total_value += val_i * qty

        cpu_pct = (used_cpu / cap_cpu * 100) if cap_cpu > 0 else 0.0
        ram_pct = (used_ram / cap_ram * 100) if cap_ram > 0 else 0.0
        report = f"### Resource Allocation Summary\n- **CPU Used:** {used_cpu:.2f} / {cap_cpu:.2f} ({cpu_pct:.1f}%)\n- **RAM Used:** {used_ram:.2f} / {cap_ram:.2f} ({ram_pct:.1f}%)"
        return {
            "mode": "resource_allocation",
            "total_value": round(total_value, 2),
            "used_cpu": round(used_cpu, 2),
            "used_ram": round(used_ram, 2),
            "capacity_cpu": round(cap_cpu, 2),
            "capacity_ram": round(cap_ram, 2),
            "items": selected,
            "report": report,
            "status": "ok",
        }

    if mode == "scheduling":
        shifts = p.get("Shifts", [])
        if not shifts:
            shifts = list((p.get("Demands") or {}).keys())
        assignments = []
        shift_counts: Dict[str, int] = {str(s): 0 for s in shifts}

        for s_idx, shift in enumerate(shifts):
            for e_idx, emp in enumerate(items):
                val = var_values.get(f"Assign_{e_idx}_{s_idx}", 0.0)
                if val <= 0:
                    continue
                assignments.append({"employee": emp, "shift": shift, "value": val})
                shift_counts[str(shift)] = shift_counts.get(str(shift), 0) + int(round(val))

        report = f"### Scheduling Summary\n- **Total Assignments:** {len(assignments)}\n- **Shifts Covered:** {len(shift_counts)}"
        return {
            "mode": "scheduling",
            "shift_coverage": shift_counts,
            "assignments": assignments,
            "report": report,
            "status": "ok",
        }

    if mode == "generic":
        active_variables = []
        for variable in res.get("variables", []):
            value = safe_float(variable.get("Value", 0))
            if abs(value) <= 0.000001:
                continue
            active_variables.append({
                "name": str(variable.get("Variable", "")),
                "value": value,
            })

        objective_terms = ((p.get("IR") or {}).get("objective", []) if isinstance(p.get("IR"), dict) else [])
        constraints = ((p.get("IR") or {}).get("constraints", []) if isinstance(p.get("IR"), dict) else [])
        report = (
            "### Generic Optimization Summary\n"
            f"- **Objective Terms:** {len(objective_terms)}\n"
            f"- **Constraints:** {len(constraints)}\n"
            f"- **Active Variables:** {len(active_variables)}"
        )
        return {
            "mode": "generic",
            "status": "ok" if str(res.get("status", "")).lower() not in ("error", "infeasible") else str(res.get("status", "error")).lower(),
            "report": report,
            "objective_value": safe_float(res.get("objective", 0)),
            "variable_count": len(res.get("variables", [])),
            "constraint_count": len(constraints),
            "active_variables": active_variables,
        }

    return {
        "mode": mode,
        "report": "No dashboard available for this mode.",
        "status": "unsupported",
    }


def process_sensitivity(
    res: Dict[str, Any],
    store: Dict[str, Any],
    mode: str | None = None,
) -> Dict[str, Any]:
    """Build constraint/sensitivity summary from solver duals."""
    mode = normalize_mode(mode)
    
    if not res.get("lp_sensitivity"):
        return {
            "constraints": [],
            "top_bottleneck": None,
            "insight": "Sensitivity is available only for LP/CG models.",
        }

    if mode == "cutting":
        return _process_cutting_sensitivity(res, store)

    return _process_sensitivity_general(res)


def _process_cutting_sensitivity(
    res: Dict[str, Any],
    store: Dict[str, Any],
) -> Dict[str, Any]:
    """Process cutting sensitivity."""
    consts = res.get("constraints", [])
    p = parameter_map(store)
    items: List[str] = p.get("Items", [])

    if not consts:
        return {
            "constraints": [],
            "top_bottleneck": None,
            "insight": "Please run solver first.",
        }

    try:
        import pandas as pd
        df = pd.DataFrame(consts)
        item_map = {f"C_{i}": items[i] for i in range(len(items))}
        df["Constraint"] = df["Constraint"].map(item_map).fillna(df["Constraint"])
        df = df[df["Constraint"].isin(items)].copy()
        df["Impact"] = df["Shadow Price"].abs()
        df = df.sort_values(by="Impact", ascending=False)

        rows: List[Dict[str, Any]] = []
        for _, row in df[["Constraint", "Shadow Price", "Slack"]].iterrows():
            rows.append({
                "Constraint": str(row["Constraint"]),
                "Shadow Price": f"${safe_float(row['Shadow Price']):.2f}",
                "Slack": safe_float(row["Slack"]),
            })

        top_b = str(df.iloc[0]["Constraint"]) if not df.empty else "N/A"
        top_v = abs(safe_float(df.iloc[0]["Shadow Price"])) if not df.empty else 0.0
        
        return {
            "constraints": rows,
            "top_bottleneck": top_b,
            "insight": f"Bottleneck: **{top_b}** (Shadow Price: ${top_v:.2f})",
        }
    except ImportError:
        return {
            "constraints": [],
            "top_bottleneck": None,
            "insight": "Pandas required for sensitivity analysis.",
        }


def _process_sensitivity_general(res: Dict[str, Any]) -> Dict[str, Any]:
    """Generic sensitivity processing."""
    consts = res.get("constraints", [])
    
    if not consts:
        return {
            "constraints": [],
            "top_bottleneck": None,
            "insight": "No constraint data.",
        }
    
    try:
        import pandas as pd
        df = pd.DataFrame(consts)
        df["Impact"] = df.get("Shadow Price", 0).abs() if "Shadow Price" in df.columns else 0.0
        df = df.sort_values(by="Impact", ascending=False)
        
        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            rows.append({
                "Constraint": str(row.get("Constraint", "Unknown")),
                "Shadow Price": f"${safe_float(row.get('Shadow Price', 0)):.2f}",
                "Slack": safe_float(row.get("Slack", 0)),
            })
        
        top_b = str(df.iloc[0]["Constraint"]) if not df.empty else "N/A"
        return {
            "constraints": rows,
            "top_bottleneck": top_b,
            "insight": f"Top bottleneck: {top_b}",
        }
    except ImportError:
        return {
            "constraints": [],
            "top_bottleneck": None,
            "insight": "Pandas required.",
        }
