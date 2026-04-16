from __future__ import annotations

from typing import Any, Dict, List

from fastmcp import FastMCP
from pydantic import ValidationError

from python_solvers.api.solver_api import run_optimization
from python_solvers.mcp_schema import DOMAIN_PARAM_MODELS, DomainName, OptimizationRequest
from python_solvers.mcp_utils import (
    apply_forecast_to_payload,
    build_domain_payload_from_records,
    load_dataframe_from_path,
    logical_error_feedback,
    normalize_mapped_records,
    to_jsonable,
    validation_feedback,
)
from python_solvers.forecasting import forecast_demand as run_forecast_demand
from python_solvers.r_bridge import ensure_r_bridge, run_r_post_analysis


mcp = FastMCP("OptiMystic AI COO")


@mcp.tool(
    name="optimize",
    description=(
        "Run an OptiMystic optimization job. "
        "Input is domain/solver/params JSON and output is a structured solve result with "
        "status, objective, variables, constraints, solve_time, and domain-specific details."
    ),
)
def optimize(request: OptimizationRequest) -> Dict[str, Any]:
    """Execute optimization using existing OptiMystic runtime (Python + Julia routing)."""

    try:
        normalized_request = OptimizationRequest.model_validate(request.model_dump())

        param_model = DOMAIN_PARAM_MODELS.get(normalized_request.domain)
        if param_model is not None:
            validated_params = param_model.model_validate(normalized_request.params)
            runtime_params = validated_params.model_dump()
        else:
            runtime_params = dict(normalized_request.params)

        result = run_optimization(normalized_request.domain, normalized_request.solver, runtime_params)

        logical_error = logical_error_feedback(normalized_request.domain, runtime_params, result)
        if logical_error is not None:
            return {
                "ok": False,
                "error": logical_error,
                "result": result,
            }

        return {"ok": True, "result": result}
    except ValidationError as exc:
        feedback = validation_feedback(exc)
        return {
            "ok": False,
            "error": {
                "code": "validation_error",
                "message": feedback["message"],
                "details": feedback["details"],
            },
        }
    except ValueError as exc:
        return {
            "ok": False,
            "error": {
                "code": "invalid_request",
                "message": str(exc),
            },
        }
    except RuntimeError as exc:
        return {
            "ok": False,
            "error": {
                "code": "solver_runtime_error",
                "message": str(exc),
            },
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": {
                "code": "internal_error",
                "message": str(exc),
            },
        }


@mcp.tool(
    name="read_company_data",
    description=(
        "Read a local CSV/XLSX file and return lightweight reconnaissance output: "
        "file name, total rows, column names, and top sample rows."
    ),
)
def read_company_data(file_path: str, max_rows: int = 3) -> Dict[str, Any]:
    max_rows = max(1, min(int(max_rows or 3), 20))

    try:
        full_df, src = load_dataframe_from_path(file_path)
        total_rows = int(len(full_df))
        sample_df = full_df.head(max_rows)

        sample_clean = sample_df.where(sample_df.notna(), None)
        return {
            "ok": True,
            "file_name": src.name,
            "file_path": str(src),
            "total_rows": int(total_rows),
            "columns": [str(c) for c in sample_df.columns],
            "sample_data": to_jsonable(sample_clean.to_dict(orient="records")),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": {
                "code": "read_company_data_failed",
                "message": str(exc),
            },
        }


@mcp.tool(
    name="forecast_demand",
    description=(
        "Forecast demand from historical CSV/XLSX time-series using StatsForecast AutoARIMA. "
        "Returns point forecast and confidence bounds that can be fed into optimization."
    ),
)
def forecast_demand(
    file_path: str,
    time_col: str,
    target_col: str,
    item_col: str | None = None,
    horizon: int = 7,
    freq: str = "D",
    confidence_level: int = 95,
) -> Dict[str, Any]:
    try:
        return run_forecast_demand(
            file_path=file_path,
            time_col=time_col,
            target_col=target_col,
            item_col=item_col,
            horizon=horizon,
            freq=freq,
            level=confidence_level,
        )
    except Exception as exc:
        return {
            "ok": False,
            "error": {
                "code": "forecast_demand_failed",
                "message": str(exc),
            },
        }


@mcp.tool(
    name="bridge_forecast_to_payload",
    description=(
        "Apply forecast output rows to optimization payload demand fields. "
        "Use this after forecast_demand and before optimize for robust planning."
    ),
)
def bridge_forecast_to_payload(
    domain: DomainName,
    payload: Dict[str, Any],
    forecast_rows: List[Dict[str, Any]],
    bound: str = "upper",
    min_demand: int = 1,
    round_mode: str = "ceil",
) -> Dict[str, Any]:
    try:
        merged = apply_forecast_to_payload(
            domain=domain,
            payload=dict(payload) if isinstance(payload, dict) else {},
            forecast_rows=forecast_rows,
            bound=bound,
            min_demand=min_demand,
            round_mode=round_mode,
        )
        return {
            "ok": True,
            "payload": merged["payload"],
            "meta": merged["meta"],
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": {
                "code": "bridge_forecast_to_payload_failed",
                "message": str(exc),
            },
        }


@mcp.tool(
    name="map_to_target_schema",
    description=(
        "Apply LLM mapping rules to source file columns and generate a domain payload validated "
        "against OptiMystic target schema."
    ),
)
def map_to_target_schema(
    file_path: str,
    mapping_rule: Dict[str, str],
    domain: DomainName,
) -> Dict[str, Any]:
    try:
        if not isinstance(mapping_rule, dict) or not mapping_rule:
            return {
                "ok": False,
                "error": {
                    "code": "invalid_mapping_rule",
                    "message": "mapping_rule은 {원본컬럼: 타겟필드} 형태의 비어있지 않은 dict 여야 합니다.",
                },
            }

        df, src = load_dataframe_from_path(file_path)
        records = normalize_mapped_records(df, mapping_rule)
        if not records:
            return {
                "ok": False,
                "error": {
                    "code": "mapping_result_empty",
                    "message": "mapping_rule 적용 후 남는 타겟 컬럼 데이터가 없습니다.",
                },
            }

        payload = build_domain_payload_from_records(domain, records)
        schema_model = DOMAIN_PARAM_MODELS.get(domain)
        if schema_model is None:
            return {
                "ok": False,
                "error": {
                    "code": "unknown_domain",
                    "message": f"지원하지 않는 domain 입니다: {domain}",
                },
            }

        try:
            validated_payload = schema_model.model_validate(payload)
        except ValidationError as exc:
            feedback = validation_feedback(exc)
            return {
                "ok": False,
                "error": {
                    "code": "validation_error",
                    "message": feedback["message"],
                    "details": feedback["details"],
                },
                "meta": {
                    "file_name": src.name,
                    "domain": domain,
                    "mapped_record_count": len(records),
                },
            }

        return {
            "ok": True,
            "file_name": src.name,
            "domain": domain,
            "mapped_record_count": len(records),
            "mapping_rule": mapping_rule,
            "payload": validated_payload.model_dump(),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": {
                "code": "map_to_target_schema_failed",
                "message": str(exc),
            },
        }


@mcp.tool(
    name="get_target_schema",
    description=(
        "Return OptiMystic target JSON schema for a domain so the agent can map source data "
        "into valid optimization payloads."
    ),
)
def get_target_schema(domain: DomainName) -> Dict[str, Any]:
    schema_model = DOMAIN_PARAM_MODELS.get(domain)
    if schema_model is None:
        return {
            "ok": False,
            "error": {
                "code": "unknown_domain",
                "message": f"지원하지 않는 domain 입니다: {domain}",
            },
        }

    return {
        "ok": True,
        "domain": domain,
        "schema": to_jsonable(schema_model.model_json_schema()),
    }


def _analyze_with_r_impl(
    mode: DomainName,
    run_result: Dict[str, Any] | None = None,
    run_results: List[Dict[str, Any]] | None = None,
    store: Dict[str, Any] | None = None,
    confidence: float = 0.95,
    n_boot: int = 500,
    seed: int = 42,
) -> Dict[str, Any]:
    try:
        bridge = ensure_r_bridge()

        normalized_result = run_result if isinstance(run_result, dict) else {}
        normalized_history = [row for row in (run_results or []) if isinstance(row, dict)]

        if not normalized_result and normalized_history:
            normalized_result = normalized_history[0]
        if not normalized_history and normalized_result:
            normalized_history = [normalized_result]

        if not normalized_result:
            return {
                "ok": False,
                "error": {
                    "code": "invalid_analysis_input",
                    "message": "run_result 또는 run_results 중 최소 1개는 필요합니다.",
                },
            }

        analysis = run_r_post_analysis(
            mode=mode,
            run_result=normalized_result,
            run_results=normalized_history,
            store=store,
            confidence=confidence,
            n_boot=n_boot,
            seed=seed,
        )

        return {
            "ok": True,
            "r_bridge": bridge,
            "analysis": to_jsonable(analysis),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": {
                "code": "r_analysis_failed",
                "message": str(exc),
            },
        }


@mcp.tool(
    name="analyze_with_r",
    description=(
        "Run post-analysis with r_solvers through rpy2. "
        "Accepts single run result or run history and returns processed_result, sensitivity, "
        "decision analytics, and executive summary."
    ),
)
def analyze_with_r(
    mode: DomainName,
    run_result: Dict[str, Any] | None = None,
    run_results: List[Dict[str, Any]] | None = None,
    store: Dict[str, Any] | None = None,
    confidence: float = 0.95,
    n_boot: int = 500,
    seed: int = 42,
) -> Dict[str, Any]:
    return _analyze_with_r_impl(
        mode=mode,
        run_result=run_result,
        run_results=run_results,
        store=store,
        confidence=confidence,
        n_boot=n_boot,
        seed=seed,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
