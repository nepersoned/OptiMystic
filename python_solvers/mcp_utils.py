from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from pydantic import ValidationError


def format_loc(loc: tuple[Any, ...]) -> str:
    out = ""
    for part in loc:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            if out:
                out += "."
            out += str(part)
    return out


def validation_feedback(exc: ValidationError) -> Dict[str, Any]:
    errors = exc.errors(include_url=False)
    if not errors:
        return {
            "message": "Validation Error: 입력 스키마를 확인하고 다시 JSON을 생성하세요.",
            "details": [],
        }

    first = errors[0]
    loc = format_loc(tuple(first.get("loc", ())))
    msg = str(first.get("msg", "invalid input"))
    field_text = f"'{loc}'" if loc else "입력"
    return {
        "message": f"Validation Error: {field_text} 값이 유효하지 않습니다 ({msg}). 스키마를 확인하고 다시 JSON을 생성하세요.",
        "details": errors,
    }


def to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def load_dataframe_from_path(file_path: str) -> tuple[pd.DataFrame, Path]:
    src = Path(file_path).expanduser()
    if not src.is_absolute():
        src = (Path.cwd() / src).resolve()
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {src}")

    suffix = src.suffix.lower()
    if suffix in {".csv", ".txt", ".tsv"}:
        sep = "\t" if suffix == ".tsv" else ","
        return pd.read_csv(src, sep=sep), src
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(src), src
    raise ValueError("지원 포맷은 csv/tsv/xlsx/xls 입니다.")


def normalize_mapped_records(df: pd.DataFrame, mapping_rule: Dict[str, str]) -> List[Dict[str, Any]]:
    renamed = df.rename(columns=mapping_rule)
    target_columns = [str(v) for v in mapping_rule.values() if str(v).strip()]
    if not target_columns:
        return []

    existing_columns = [c for c in target_columns if c in renamed.columns]
    if not existing_columns:
        return []

    trimmed = renamed[existing_columns].copy()
    trimmed = trimmed.where(pd.notna(trimmed), None)
    records = [to_jsonable(row) for row in trimmed.to_dict(orient="records")]
    return [r for r in records if isinstance(r, dict)]


def build_domain_payload_from_records(domain: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if domain == "packing":
        items = []
        for i, row in enumerate(records):
            item_name = row.get("Name", f"Item_{i}")
            items.append(
                {
                    "Name": item_name,
                    "Weight": row.get("Weight"),
                    "Value": row.get("Value", 1),
                    "Demand": row.get("Demand"),
                }
            )
        total_weight = 0.0
        for row in items:
            try:
                total_weight += float(row.get("Weight", 0) or 0) * float(row.get("Demand", 0) or 0)
            except Exception:
                pass
        return {
            "Items": items,
            "Vehicles": [{"Capacity": max(total_weight, 1.0)}],
        }

    if domain == "vrp":
        nodes = [{"Name": "Depot", "Demand": 0, "X": 0, "Y": 0}]
        for i, row in enumerate(records):
            nodes.append(
                {
                    "Name": row.get("Name", f"Node_{i}"),
                    "Demand": row.get("Demand", 0),
                    "X": row.get("X", row.get("x", i + 1)),
                    "Y": row.get("Y", row.get("y", 0)),
                }
            )
        total_demand = 0.0
        for row in nodes[1:]:
            try:
                total_demand += float(row.get("Demand", 0) or 0)
            except Exception:
                pass
        return {
            "Nodes": nodes,
            "Vehicles": [{"Name": "Vehicle_0", "Capacity": max(total_demand, 1.0)}],
        }

    if domain == "scheduling":
        employees = []
        total_demand = 0
        for i, row in enumerate(records):
            employees.append(
                {
                    "Name": row.get("Name", f"E_{i}"),
                    "MaxShifts": row.get("MaxShifts", 1),
                }
            )
            try:
                total_demand += int(float(row.get("Demand", 0) or 0))
            except Exception:
                pass
        if total_demand <= 0:
            total_demand = 1
        return {
            "Employees": employees,
            "Shifts": [{"Name": "Morning", "Demand": total_demand}],
        }

    if domain == "cutting":
        items = []
        total_length = 0.0
        for i, row in enumerate(records):
            length = row.get("Length", row.get("Weight"))
            demand = row.get("Demand")
            items.append(
                {
                    "Name": row.get("Name", f"Piece_{i}"),
                    "Length": length,
                    "Demand": demand,
                }
            )
            try:
                total_length += float(length or 0) * float(demand or 0)
            except Exception:
                pass
        return {
            "Items": items,
            "Stocks": [{"Name": "Stock_A", "Length": max(total_length, 1.0), "Cost": 1, "Limit": 1}],
            "Kerf": 0,
        }

    if domain == "resourcing":
        containers = []
        total_cpu = 0.0
        total_ram = 0.0
        for i, row in enumerate(records):
            cpu = row.get("CPU")
            ram = row.get("RAM")
            containers.append(
                {
                    "Name": row.get("Name", f"Task_{i}"),
                    "CPU": cpu,
                    "RAM": ram,
                    "Cost": row.get("Cost", 0),
                }
            )
            try:
                total_cpu += float(cpu or 0)
                total_ram += float(ram or 0)
            except Exception:
                pass
        return {
            "Containers": containers,
            "Servers": [{"CPU": max(total_cpu, 1.0), "RAM": max(total_ram, 1.0)}],
        }

    if domain == "generic":
        return {"IR": {"meta": {"domain": "generic"}, "variables": [], "objective": [], "constraints": []}}

    raise ValueError(f"지원하지 않는 domain 입니다: {domain}")


def apply_forecast_to_payload(
    domain: str,
    payload: Dict[str, Any],
    forecast_rows: List[Dict[str, Any]],
    bound: str = "upper",
    min_demand: int = 1,
    round_mode: str = "ceil",
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if not isinstance(forecast_rows, list) or not forecast_rows:
        raise ValueError("forecast_rows must be a non-empty list")

    value_key = (bound or "upper").strip().lower()
    if value_key not in {"lower", "point", "upper", "recommended_demand"}:
        raise ValueError("bound must be one of: lower, point, upper, recommended_demand")

    round_key = (round_mode or "ceil").strip().lower()
    if round_key not in {"ceil", "floor", "round"}:
        raise ValueError("round_mode must be one of: ceil, floor, round")

    def _to_int(value: Any) -> int | None:
        try:
            raw = float(value)
        except Exception:
            return None
        if round_key == "floor":
            out = math.floor(raw)
        elif round_key == "round":
            out = int(round(raw))
        else:
            out = math.ceil(raw)
        return max(int(min_demand), int(out))

    by_name: Dict[str, int] = {}
    all_value: int | None = None

    for row in forecast_rows:
        if not isinstance(row, dict):
            continue
        item_name = str(row.get("item", "")).strip()
        chosen = row.get(value_key, row.get("upper"))
        demand = _to_int(chosen)
        if demand is None:
            continue
        if item_name.lower() == "all" or not item_name:
            all_value = demand if all_value is None else max(all_value, demand)
            continue
        prev = by_name.get(item_name)
        by_name[item_name] = demand if prev is None else max(prev, demand)

    normalized_domain = (domain or "").strip().lower()
    updated = 0
    updated_items: List[str] = []

    def _apply(rows: List[Dict[str, Any]], name_key: str, demand_key: str, skip_first: bool = False) -> None:
        nonlocal updated
        start_index = 1 if skip_first else 0
        for row in rows[start_index:]:
            if not isinstance(row, dict):
                continue
            name = str(row.get(name_key, "")).strip()
            new_demand = by_name.get(name)
            if new_demand is None and all_value is not None:
                new_demand = all_value
            if new_demand is None:
                continue
            row[demand_key] = int(new_demand)
            updated += 1
            updated_items.append(name or f"index_{updated}")

    if normalized_domain == "packing":
        items = payload.get("Items")
        if isinstance(items, list):
            _apply(items, "Name", "Demand")
    elif normalized_domain == "cutting":
        items = payload.get("Items")
        if isinstance(items, list):
            _apply(items, "Name", "Demand")
    elif normalized_domain == "scheduling":
        shifts = payload.get("Shifts")
        if isinstance(shifts, list):
            _apply(shifts, "Name", "Demand")
    elif normalized_domain == "vrp":
        nodes = payload.get("Nodes")
        if isinstance(nodes, list):
            _apply(nodes, "Name", "Demand", skip_first=True)

    return {
        "payload": payload,
        "meta": {
            "domain": normalized_domain,
            "bound": value_key,
            "round_mode": round_key,
            "updated_count": updated,
            "updated_items": updated_items,
        },
    }


def logical_error_feedback(domain: str, params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any] | None:
    status = str(result.get("status", "")).strip().lower()
    if status not in {"infeasible", "unbounded"}:
        return None

    domain = (domain or "").strip().lower()
    if domain == "packing":
        items = params.get("Items", []) if isinstance(params.get("Items"), list) else []
        vehicles = params.get("Vehicles", []) if isinstance(params.get("Vehicles"), list) else []
        total_capacity = sum(float(v.get("Capacity", 0) or 0) for v in vehicles if isinstance(v, dict))
        total_weight_demand = sum(
            float(i.get("Weight", 0) or 0) * float(i.get("Demand", 0) or 0)
            for i in items
            if isinstance(i, dict)
        )
        if total_capacity < total_weight_demand:
            hint = (
                "현재 Vehicles의 Capacity 총합이 Items의 Weight x Demand 총합보다 작습니다. "
                "Capacity를 늘리거나 Demand를 낮춰 다시 시도하세요."
            )
        else:
            hint = "제약식 또는 수요/용량 값을 점검하고 완화해 다시 시도하세요."
    elif domain == "vrp":
        nodes = params.get("Nodes", []) if isinstance(params.get("Nodes"), list) else []
        vehicles = params.get("Vehicles", []) if isinstance(params.get("Vehicles"), list) else []
        total_capacity = sum(float(v.get("Capacity", 0) or 0) for v in vehicles if isinstance(v, dict))
        total_demand = sum(float(n.get("Demand", 0) or 0) for n in nodes[1:] if isinstance(n, dict))
        if total_capacity < total_demand:
            hint = "차량 총 용량이 고객 수요 총합보다 작습니다. 차량/용량을 늘리거나 수요를 조정하세요."
        else:
            hint = "시간창/픽업-배송 제약이 과도할 수 있습니다. 제약을 완화해 재시도하세요."
    elif domain == "scheduling":
        employees = params.get("Employees", []) if isinstance(params.get("Employees"), list) else []
        shifts = params.get("Shifts", []) if isinstance(params.get("Shifts"), list) else []
        global_max = float(params.get("MaxShiftsPerEmployee", 1) or 1)
        max_assignable = 0.0
        for emp in employees:
            if isinstance(emp, dict) and emp.get("MaxShifts") is not None:
                max_assignable += float(emp.get("MaxShifts", 0) or 0)
            else:
                max_assignable += global_max
        required = sum(float(s.get("Demand", 0) or 0) for s in shifts if isinstance(s, dict))
        if max_assignable < required:
            hint = "총 배정 가능 인력이 총 수요보다 적습니다. MaxShifts 또는 인원 수를 늘리세요."
        else:
            hint = "근무 규칙(Rules)이나 수요(Demand) 조건을 완화해 다시 시도하세요."
    elif domain == "cutting":
        items = params.get("Items", []) if isinstance(params.get("Items"), list) else []
        stocks = params.get("Stocks", []) if isinstance(params.get("Stocks"), list) else []
        demand_len = sum(float(i.get("Length", 0) or 0) * float(i.get("Demand", 0) or 0) for i in items if isinstance(i, dict))
        stock_len = sum(float(s.get("Length", 0) or 0) * float(s.get("Limit", 0) or 0) for s in stocks if isinstance(s, dict))
        if stock_len < demand_len:
            hint = "총 원자재 길이가 총 수요 길이보다 부족합니다. 재고 길이/수량을 늘리세요."
        else:
            hint = "Kerf 또는 수요/재고 제한 조건을 완화해 다시 시도하세요."
    elif domain == "resourcing":
        containers = params.get("Containers", []) if isinstance(params.get("Containers"), list) else []
        servers = params.get("Servers", []) if isinstance(params.get("Servers"), list) else []
        cpu_need = sum(float(c.get("CPU", 0) or 0) for c in containers if isinstance(c, dict))
        ram_need = sum(float(c.get("RAM", 0) or 0) for c in containers if isinstance(c, dict))
        cpu_cap = sum(float(s.get("CPU", 0) or 0) for s in servers if isinstance(s, dict))
        ram_cap = sum(float(s.get("RAM", 0) or 0) for s in servers if isinstance(s, dict))
        if cpu_need > cpu_cap or ram_need > ram_cap:
            hint = "CPU/RAM 총 수요가 서버 총 용량을 초과합니다. 서버 용량 또는 작업량을 조정하세요."
        else:
            hint = "자원/수요 제약을 완화해 다시 시도하세요."
    else:
        hint = "제약식이 모순되거나 목적함수 조건이 불안정합니다. 제약을 점검 후 재시도하세요."

    return {
        "code": f"optimization_{status}",
        "message": f"Optimization Failed ({status.title()}): {hint}",
        "retry_hint": hint,
    }
