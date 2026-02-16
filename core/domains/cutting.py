"""
Domain: Cutting Stock (Manufacturing)
Maps raw cutting input → common schema.
"""
from typing import Any, Dict, List


def map_params(raw_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map raw cutting payload to common schema.
    Cutting input: Items, ItemLens, Demands, Prices, Stocks, Kerf, Sense
    """
    items = raw_params.get("Items", [])
    item_lens = raw_params.get("ItemLens", [])
    demands = raw_params.get("Demands", {})
    prices = raw_params.get("Prices", {})
    stocks = raw_params.get("Stocks", [])
    kerf = float(raw_params.get("Kerf", 0.0))
    sense = raw_params.get("Sense", "minimize")

    return {
        "Items": items,
        "Weights": item_lens,
        "Values": prices,
        "Demands": demands,
        "Sense": sense,
        "Stocks": stocks,
        "Kerf": kerf,
        "Mode": "cutting",
    }
