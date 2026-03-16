"""
Domain: Cutting Stock (Manufacturing)
Maps raw cutting input → common schema.
"""
from typing import Any, Dict, List


def _safe_list(values: List[Any], length: int, default: float = 0.0) -> List[Any]:
    """Ensure list has exact length, padding or truncating as needed."""
    if not isinstance(values, list):
        return [default] * length
    if len(values) >= length:
        return values[:length]
    return values + [default] * (length - len(values))


def map_params(raw_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map raw cutting payload to common schema.
    Input can be:
      - Items (list of dicts) with Name, Length, and Demands
      - Or Items (list of names) + ItemLens + Demands lists
    
    Cutting-specific fields:
      - Stocks: list of {Name, Length, Cost, Limit}
      - Kerf: blade width loss
      - Prices: revenue per item (optional)
      - Sense: minimize (cost) or maximize (revenue)
    """
    # Handle flexible item input format
    items = raw_params.get("Items", [])
    
    if isinstance(items, list) and items and isinstance(items[0], dict):
        # Items as dicts with Name, Length, etc.
        names = [x.get("Name", x.get("id", f"Item_{i}")) for i, x in enumerate(items)]
        item_lens = [float(x.get("Length", x.get("Len", 1.0))) for x in items]
        demands = raw_params.get("Demands", {})
        if not demands and names:
            demands = {n: 1 for n in names}
    else:
        # Items as list of names + separate lists
        names = list(raw_params.get("Items", []))
        # Support multiple field names for item lengths
        item_lens = (
            raw_params.get("ItemLens", None) 
            or raw_params.get("Lengths", None) 
            or raw_params.get("Len", None)
            or [1.0] * len(names)
        )
        demands = raw_params.get("Demands", {})

    n = len(names)
    prices = raw_params.get("Prices", raw_params.get("Values", {}))
    stocks = raw_params.get("Stocks", [{"Name": "Default", "Length": 1000, "Cost": 1, "Limit": 50}])
    if isinstance(stocks, dict):
        stocks = [stocks]
    kerf = float(raw_params.get("Kerf", 0.0))
    sense = raw_params.get("Sense", "minimize")

    # Normalize stocks to standard format
    normalized_stocks = []
    for stock in stocks:
        if isinstance(stock, dict):
            normalized_stocks.append({
                "Name": stock.get("Name", f"Stock_{len(normalized_stocks)}"),
                "Length": float(stock.get("Length", stock.get("Len", 1000))),
                "Cost": float(stock.get("Cost", 1)),
                "Limit": int(stock.get("Limit", 50)),
            })
        else:
            normalized_stocks.append({
                "Name": f"Stock_{len(normalized_stocks)}",
                "Length": float(stock),
                "Cost": 1,
                "Limit": 50,
            })

    mapped = {
        "Items": names,
        "ItemLens": _safe_list(item_lens, n, 1.0),
        "Weights": _safe_list(item_lens, n, 1.0),
        "Values": prices if prices else {n: 0 for n in names},
        "Demands": demands if demands else {n: 1 for n in names},
        "Sense": sense,
        "Stocks": normalized_stocks,
        "Kerf": kerf,
        "Mode": "cutting",
    }
    mapped["IR"] = build_ir(mapped)
    return mapped


def build_ir(params: Dict[str, Any]) -> Dict[str, Any]:
    items = list(params.get("Items", []))
    item_lens = _safe_list(params.get("Weights", []), len(items), 1.0)
    demands = params.get("Demands", {}) or {}
    prices = params.get("Values", {}) or {}
    stocks = list(params.get("Stocks", [])) or [{"Name": "Default", "Length": 1000, "Cost": 1, "Limit": 50}]
    kerf = float(params.get("Kerf", 0.0))
    sense = str(params.get("Sense", "minimize")).lower()
    max_bins = min(30, max(int(float(stock.get("Limit", 30))) for stock in stocks)) if stocks else 30

    variables = []
    objective = []
    constraints = []

    for s_idx, stock in enumerate(stocks):
        for b_idx in range(max_bins):
            use_name = f"Use_{s_idx}_{b_idx}"
            variables.append({"name": use_name, "type": "Binary", "lb": 0, "ub": 1})
            if sense == "minimize":
                objective.append({"var": use_name, "coef": float(stock.get("Cost", 0))})

    for i_idx, item in enumerate(items):
        for s_idx, stock in enumerate(stocks):
            for b_idx in range(max_bins):
                cut_name = f"Cut_{i_idx}_{s_idx}_{b_idx}"
                variables.append({"name": cut_name, "type": "Integer", "lb": 0})
                if sense != "minimize":
                    objective.append({"var": cut_name, "coef": float(prices.get(item, 0))})
                if i_idx == 0:
                    terms = [
                        {"var": f"Cut_{item_idx}_{s_idx}_{b_idx}", "coef": float(item_lens[item_idx]) + kerf}
                        for item_idx in range(len(items))
                    ]
                    terms.append({"var": f"Use_{s_idx}_{b_idx}", "coef": -(float(stock.get("Length", 0)) + kerf)})
                    constraints.append({
                        "name": f"capacity_{s_idx}_{b_idx}",
                        "type": "linear",
                        "terms": terms,
                        "sense": "<=",
                        "rhs": 0,
                    })

    for i_idx, item in enumerate(items):
        constraints.append({
            "name": f"demand_{i_idx}",
            "type": "linear",
            "terms": [
                {"var": f"Cut_{i_idx}_{s_idx}_{b_idx}", "coef": 1}
                for s_idx in range(len(stocks))
                for b_idx in range(max_bins)
            ],
            "sense": ">=",
            "rhs": float(demands.get(item, 0)),
        })

    return {
        "meta": {"domain": "cutting", "sense": sense},
        "variables": variables,
        "objective": objective,
        "constraints": constraints,
    }
