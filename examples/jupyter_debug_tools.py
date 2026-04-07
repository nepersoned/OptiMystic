import json
import importlib
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(domain: str, solver: str, params: Dict[str, Any]) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "python_solvers" / "cli_solver.py"),
        "--domain",
        domain,
        "--solver",
        solver,
        "--params",
        json.dumps(params),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "Solver CLI failed")
    return json.loads(proc.stdout)


def run_python_only_cp_scheduling() -> Dict[str, Any]:
    params = {
        "Employees": [
            {"Name": "E1", "MaxShifts": 5},
            {"Name": "E2", "MaxShifts": 5},
        ],
        "Shifts": [
            {"Name": "Morning", "Demand": 1},
            {"Name": "Evening", "Demand": 1},
        ],
        "Values": {
            "E1": {"Morning": 1.0, "Evening": 0.7},
            "E2": {"Morning": 0.9, "Evening": 1.0},
        },
        "MaxShiftsPerEmployee": 5,
    }
    return _run_cli("scheduling", "cp", params)


def run_julia_only_mip_packing() -> Dict[str, Any]:
    params = {
        "Items": [
            {"Name": "A", "Weight": 2, "Value": 10},
            {"Name": "B", "Weight": 3, "Value": 12},
            {"Name": "C", "Weight": 4, "Value": 14},
        ],
        "Vehicles": [{"Capacity": 7}],
    }
    return _run_cli("packing", "mip", params)


def run_full_pipeline() -> Dict[str, Dict[str, Any]]:
    return {
        "python_cp": run_python_only_cp_scheduling(),
        "julia_mip": run_julia_only_mip_packing(),
    }


def explain_debug_pipeline() -> Dict[str, str]:
    return {
        "python_only": "Validate only Python CP scheduling logic (excluding Julia/R)",
        "julia_only": "Validate only Julia MIP execution path (called via Python CLI subprocess)",
        "r_bridge": "Validate rpy2 and r_solvers loading/connectivity",
        "full_pipeline": "End-to-end validation: Python/Julia outputs passed into R process_results",
    }


def run_section(section: str) -> Dict[str, Any]:
    name = (section or "").strip().lower()
    if name == "python":
        return {"python_cp": run_python_only_cp_scheduling()}
    if name == "julia":
        return {"julia_mip": run_julia_only_mip_packing()}
    if name == "full":
        return run_full_pipeline()
    raise ValueError("section must be one of: python, julia, full")


def ensure_r_bridge() -> Dict[str, Any]:
    """Initialize rpy2 bridge and load r_solvers modules."""
    try:
        ro = importlib.import_module("rpy2.robjects")
    except Exception as exc:
        raise RuntimeError(f"rpy2 import failed: {exc}") from exc

    r_dir = (PROJECT_ROOT / "r_solvers").as_posix()
    ro.r(f"setwd('{r_dir}')")
    ro.r("library(jsonlite)")
    ro.r("library(ggplot2)")
    ro.r("library(dplyr)")
    ro.r("library(tidyr)")
    ro.r("source('utils.R')")
    ro.r("source('plotting.R')")
    ro.r("source('processors.R')")

    r_version = str(ro.r("R.version.string")[0])
    return {
        "ok": True,
        "r_version": r_version,
        "r_workdir": r_dir,
    }


def run_r_postprocess(mode: str, solver_result: Dict[str, Any], store: Dict[str, Any]) -> Dict[str, Any]:
    """Run r_solvers::process_results from Python via rpy2 and return JSON-safe dict."""
    ro = importlib.import_module("rpy2.robjects")

    # Escape single quotes for safe embedding into R string literal.
    result_json = json.dumps(solver_result).replace("'", "\\'")
    store_json = json.dumps(store).replace("'", "\\'")
    mode_value = (mode or "generic").replace("'", "\\'")

    ro.r(f"py_result <- jsonlite::fromJSON('{result_json}', simplifyVector = FALSE)")
    ro.r(f"py_store <- jsonlite::fromJSON('{store_json}', simplifyVector = FALSE)")
    ro.r(f"py_mode <- '{mode_value}'")
    ro.r("py_processed <- process_results(py_result, py_store, py_mode)")
    processed_json = str(ro.r("jsonlite::toJSON(py_processed, auto_unbox = TRUE, null = 'null')")[0])
    return json.loads(processed_json)
