import json
import sys
import argparse
from python_solvers.utils import bridge_logic
from python_solvers.utils import solver_engine as solver_core
from python_solvers.utils import services

def main():
    parser = argparse.ArgumentParser(description="OptiMystic Solver - Pure Calculator")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--solver", required=True)
    parser.add_argument("--params", required=True)
    args = parser.parse_args()

    try:
        params = json.loads(args.params)

        objective, constraints, variables = bridge_logic.generate_logic(args.domain, params, args.solver)
        mapped_params = bridge_logic.map_params_by_mode(args.domain, params)

        store_data = {
            "variables": variables,
            "parameters": services.build_parameter_store(mapped_params)
        }

        sense = mapped_params.get("Sense", "minimize").lower()

        result = solver_core.solve_model(store_data, sense, objective, constraints)

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