import json
import sys
import argparse
import os
import subprocess
import threading

# Allow running this file directly (python python_solvers/cli_solver.py)
# by ensuring project root is importable as a top-level package location.
if __package__ is None or __package__ == "":
    _HERE = os.path.dirname(os.path.abspath(__file__))
    _ROOT = os.path.dirname(_HERE)
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)

from python_solvers.logic import logic_cp
from python_solvers.utils import bridge_logic
from python_solvers.utils import services


_JULIA_MAIN = None
_JULIA_INCLUDE_DONE = False
_JULIA_LOCK = threading.Lock()


def _julia_command() -> str:
    return os.getenv("OPTIMYSTIC_JULIA", "julia")


def _julia_bridge_mode() -> str:
    return (os.getenv("OPTIMYSTIC_JULIA_BRIDGE", "subprocess") or "subprocess").strip().lower()


def _julia_timeout_seconds() -> int:
    value = os.getenv("OPTIMYSTIC_JULIA_TIMEOUT_SECONDS", "30")
    try:
        return max(1, int(float(value)))
    except (TypeError, ValueError):
        return 30


def _build_julia_payload(mapped_params: dict) -> dict:
    ir = mapped_params.get("IR", {}) if isinstance(mapped_params, dict) else {}
    payload = {
        "IR": ir,
        "Sense": mapped_params.get("Sense", "minimize"),
    }
    # ST solver may need scenario metadata for reporting/details.
    if isinstance(mapped_params.get("ST"), dict):
        payload["ST"] = mapped_params.get("ST")
    return payload


def _run_julia_solver(domain: str, solver: str, julia_params: dict) -> dict:
    if _julia_bridge_mode() == "juliacall":
        return _run_julia_solver_juliacall(domain, solver, julia_params)

    cmd = [
        _julia_command(),
        "--project=julia_solvers",
        "julia_solvers/cli_solver.jl",
        "--domain", domain,
        "--solver", solver,
        "--params", json.dumps(julia_params),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=_julia_timeout_seconds(),
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        msg = stderr or stdout or "Julia solver execution failed"
        raise RuntimeError(msg)

    output = (proc.stdout or "").strip()
    if not output:
        raise RuntimeError("Julia solver returned empty output")

    try:
        result = json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid Julia solver JSON: {exc}") from exc

    if isinstance(result, dict) and str(result.get("status", "")).lower() == "error":
        raise RuntimeError(result.get("error_msg") or result.get("error") or "Julia solver returned error")
    return result if isinstance(result, dict) else {}


def _run_julia_solver_juliacall(domain: str, solver: str, julia_params: dict) -> dict:
    global _JULIA_MAIN, _JULIA_INCLUDE_DONE

    try:
        from juliacall import Main as jl_main
    except Exception as exc:
        raise RuntimeError(f"juliacall bridge unavailable: {exc}") from exc

    with _JULIA_LOCK:
        if _JULIA_MAIN is None:
            _JULIA_MAIN = jl_main
        if not _JULIA_INCLUDE_DONE:
            _JULIA_MAIN.seval('include("julia_solvers/src/main.jl")')
            _JULIA_INCLUDE_DONE = True

    payload = {
        "domain": domain,
        "solver": solver,
        "params": julia_params,
    }
    try:
        result = _JULIA_MAIN.route_solver(payload)
        py_result = dict(result) if isinstance(result, dict) else result
    except Exception as exc:
        raise RuntimeError(f"Julia juliacall execution failed: {exc}") from exc

    if not isinstance(py_result, dict):
        raise RuntimeError("Julia juliacall returned non-dict result")
    if str(py_result.get("status", "")).lower() == "error":
        raise RuntimeError(py_result.get("error_msg") or py_result.get("error") or "Julia solver returned error")
    return py_result

def main():
    parser = argparse.ArgumentParser(description="OptiMystic Solver - Pure Calculator")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--solver", required=True)
    parser.add_argument("--params", required=True)
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        mapped_params = bridge_logic.map_params_by_mode(args.domain, params)

        solver_type = (args.solver or "").strip().lower()
        if solver_type == "cp":
            objective, constraints, variables = bridge_logic.generate_logic(args.domain, params, solver_type)
            store_data = {
                "variables": variables,
                "parameters": services.build_parameter_store(mapped_params),
            }
            result = logic_cp.solve_cp_model(store_data, objective)
        else:
            julia_payload = _build_julia_payload(mapped_params)
            result = _run_julia_solver(args.domain, solver_type or "mip", julia_payload)
            variables = mapped_params.get("IR", {}).get("variables", [])
            store_data = {
                "variables": variables,
                "parameters": services.build_parameter_store(mapped_params),
            }

        processed_data = services.process_results(result, store_data, args.domain)
        sensitivity_data = services.process_sensitivity(result, store_data, args.domain)

        output = {
            "status": result.get("status", "Error"),
            "objective": result.get("objective"),
            "variables": result.get("variables", []),
            "constraints": result.get("constraints", []),
            "solve_time": result.get("solve_time", 0),
            "lp_sensitivity": result.get("lp_sensitivity", False),
            "details": processed_data,
            "sensitivity": sensitivity_data
        }

        print(json.dumps(output))
        sys.exit(0)

    except json.JSONDecodeError as e:
        error = {"status": "Error", "error_msg": f"Invalid JSON: {str(e)}"}
        print(json.dumps(error))
        sys.exit(1)
    except Exception as e:
        error = {"status": "Error", "error_msg": str(e)}
        print(json.dumps(error))
        sys.exit(1)

if __name__ == "__main__":
    main()