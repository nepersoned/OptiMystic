from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
R_SOLVERS_DIR = PROJECT_ROOT / "r_solvers"


def _find_r_home() -> Path | None:
    if os.name == "nt":
        candidates: list[Path] = []
        r_home_env = os.environ.get("R_HOME")
        if r_home_env:
            candidates.append(Path(r_home_env))
        base_dir = Path("C:/Program Files/R")
        if base_dir.exists():
            candidates.extend(
                sorted([p for p in base_dir.glob("R-*") if p.is_dir()], key=lambda p: p.name, reverse=True)
            )
        for candidate in candidates:
            if (candidate / "bin" / "x64").exists() or (candidate / "bin").exists():
                return candidate
        return None
    else:
        r_home_env = os.environ.get("R_HOME")
        if r_home_env:
            return Path(r_home_env)
        opt_r_versions = (
            sorted(Path("/opt/R").glob("*"), key=lambda p: p.name, reverse=True)
            if Path("/opt/R").exists() else []
        )
        linux_candidates = [Path("/usr/lib/R"), Path("/usr/local/lib/R"), *opt_r_versions]
        for candidate in linux_candidates:
            if (candidate / "bin" / "R").exists():
                return candidate
        return None


def _configure_r_runtime_paths() -> None:
    r_home = _find_r_home()
    if r_home is None:
        return

    os.environ.setdefault("R_HOME", str(r_home))

    if os.name != "nt":
        return

    r_bin_x64 = r_home / "bin" / "x64"
    r_bin = r_bin_x64 if r_bin_x64.exists() else (r_home / "bin")
    current_path = os.environ.get("PATH", "")
    if str(r_bin) not in current_path:
        os.environ["PATH"] = f"{r_bin};{current_path}" if current_path else str(r_bin)

    add_dll_directory = getattr(os, "add_dll_directory", None)
    if callable(add_dll_directory):
        try:
            add_dll_directory(str(r_bin))
        except OSError:
            pass


def _get_robjects() -> Any:
    _configure_r_runtime_paths()
    return importlib.import_module("rpy2.robjects")


def _json_from_r_var(ro: Any, var_name: str) -> Dict[str, Any]:
    json_text = str(ro.r(f"jsonlite::toJSON({var_name}, auto_unbox = TRUE, null = 'null')")[0])
    return json.loads(json_text)


def ensure_r_bridge() -> Dict[str, Any]:
    ro = _get_robjects()

    ro.globalenv["optimystic_r_dir"] = R_SOLVERS_DIR.as_posix()
    ro.r("setwd(optimystic_r_dir)")

    for package in ("jsonlite", "ggplot2", "dplyr", "tidyr"):
        ro.r(f"library({package})")

    ro.r("source('utils.R')")
    ro.r("source('chart_data.R')")
    ro.r("source('plotting.R')")
    ro.r("source('processors.R')")

    return {
        "ok": True,
        "r_version": str(ro.r("R.version.string")[0]),
        "r_workdir": R_SOLVERS_DIR.as_posix(),
    }


def run_r_post_analysis(
    mode: str,
    run_result: Dict[str, Any],
    run_results: List[Dict[str, Any]],
    store: Dict[str, Any] | None = None,
    confidence: float = 0.95,
    n_boot: int = 500,
    seed: int = 42,
) -> Dict[str, Any]:
    ro = _get_robjects()

    normalized_store = store if isinstance(store, dict) else {"parameters": []}
    normalized_mode = str(mode or "generic")
    normalized_result = run_result if isinstance(run_result, dict) else {}
    normalized_history = [r for r in (run_results or []) if isinstance(r, dict)]

    if not normalized_history and normalized_result:
        normalized_history = [normalized_result]

    if not normalized_result and normalized_history:
        normalized_result = normalized_history[0]

    ro.globalenv["optimystic_result_json"] = json.dumps(normalized_result, ensure_ascii=True)
    ro.globalenv["optimystic_store_json"] = json.dumps(normalized_store, ensure_ascii=True)
    ro.globalenv["optimystic_runs_json"] = json.dumps(normalized_history, ensure_ascii=True)
    ro.globalenv["optimystic_mode"] = normalized_mode
    ro.globalenv["optimystic_confidence"] = float(confidence)
    ro.globalenv["optimystic_n_boot"] = int(max(10, n_boot))
    ro.globalenv["optimystic_seed"] = int(seed)

    ro.r("optimystic_result <- jsonlite::fromJSON(optimystic_result_json, simplifyVector = FALSE)")
    ro.r("optimystic_store <- jsonlite::fromJSON(optimystic_store_json, simplifyVector = FALSE)")
    ro.r("optimystic_runs <- jsonlite::fromJSON(optimystic_runs_json, simplifyVector = FALSE)")

    ro.r("optimystic_processed <- process_results(optimystic_result, optimystic_store, optimystic_mode)")
    ro.r("optimystic_sensitivity <- process_sensitivity(optimystic_result, optimystic_store, optimystic_mode)")
    ro.r(
        "optimystic_decision <- process_decision_analytics("
        "optimystic_runs, mode = optimystic_mode, confidence = optimystic_confidence, "
        "n_boot = optimystic_n_boot, seed = optimystic_seed)"
    )
    ro.r(
        "optimystic_summary <- build_executive_summary_structured("
        "optimystic_processed, optimystic_sensitivity, optimystic_decision)"
    )
    ro.r(
        "optimystic_chart_data <- build_chart_data("
        "optimystic_processed, optimystic_sensitivity, optimystic_mode)"
    )

    return {
        "processed_result": _json_from_r_var(ro, "optimystic_processed"),
        "sensitivity": _json_from_r_var(ro, "optimystic_sensitivity"),
        "decision_analytics": _json_from_r_var(ro, "optimystic_decision"),
        "executive_summary": _json_from_r_var(ro, "optimystic_summary"),
        "chart_data": _json_from_r_var(ro, "optimystic_chart_data"),
    }


def analyze_with_r(
    mode: str,
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

        if not normalized_result and not normalized_history:
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
            "analysis": analysis,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": {
                "code": "r_analysis_failed",
                "message": str(exc),
            },
        }