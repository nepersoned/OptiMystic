"""
Django API views for OptiMystic Solver.
"""
import json
from typing import Tuple

from django.http import HttpRequest, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.utils import bridge_logic, solver_engine, services


def _get_params_from_payload(payload: dict) -> Tuple[dict, str]:
    """
    Resolve params and sense from request payload.
    Supports (1) direct params dict, (2) frontend table format (cut_table, cut_stock_table, kerf_val).
    Returns (params, sense).
    """
    params = payload.get("params", {})
    sense = params.get("Sense", payload.get("sense", "minimize"))

    # Frontend table format (e.g. from legacy Dash or future JS form)
    if "cut_table" in payload or "cut_stock_table" in payload:
        data_inputs = {**payload, **params}
        params = services.get_params(data_inputs, sense)

    return params, sense


@csrf_exempt
@require_http_methods(["POST"])
def optimize_view(request: HttpRequest):
    """
    POST /api/optimize/
    Body (JSON): { "template_type": "cutting", "params": { "Items": [...], "ItemLens": [...], ... } }
    or table format: { "cut_table": [...], "cut_stock_table": [...], "kerf_val": 5 }
    Returns solver result + dashboard summary (cutting) or raw result.
    """
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON payload")

    template_type = (payload.get("template_type") or "cutting").strip().lower()
    params, sense = _get_params_from_payload(payload)

    mapped = bridge_logic.map_params_by_mode(template_type, params)
    obj, const, vars_config = bridge_logic.generate_logic(template_type, params)

    store_data = {
        "variables": vars_config,
        "parameters": services.build_parameter_store(mapped),
    }

    result = solver_engine.solve_model(store_data, sense, obj, const)

    if result.get("status") == "Error":
        return JsonResponse(result, status=400, safe=False)

    dashboard = services.process_results(result, store_data, template_type)
    sensitivity = services.process_sensitivity(result, store_data, template_type)
    response = {
        **result,
        "dashboard": dashboard,
        "sensitivity": sensitivity,
    }

    return JsonResponse(response, safe=False)


@require_http_methods(["GET"])
def health_view(request: HttpRequest):
    """GET /api/health/"""
    return JsonResponse({"status": "ok"})
