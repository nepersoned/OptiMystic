import json

from core.utils import bridge_logic, services, solver_engine


def run_case(mode, params):
    mapped = bridge_logic.map_params_by_mode(mode, params)
    obj, const, vars_config = bridge_logic.generate_logic(mode, params)
    store = {
        "variables": vars_config,
        "parameters": services.build_parameter_store(mapped),
    }
    sense = mapped.get("Sense", params.get("Sense", "minimize"))
    result = solver_engine.solve_model(store, sense, obj, const)
    dashboard = services.process_results(result, store, mode)
    sensitivity = services.process_sensitivity(result, store, mode)

    print("\n==", mode, "==")
    print(json.dumps({"result": result, "dashboard": dashboard, "sensitivity": sensitivity}, indent=2))


def main():
    run_case(
        "cutting",
        {
            "Items": ["A", "B"],
            "ItemLens": [4, 6],
            "Demands": {"A": 2, "B": 1},
            "Stocks": [{"Name": "S1", "Length": 10, "Cost": 5, "Limit": 10}],
            "Kerf": 0,
            "Sense": "minimize",
        },
    )

    run_case(
        "packing",
        {
            "Items": ["Box1", "Box2", "Box3"],
            "Weights": [3, 5, 2],
            "Values": [6, 10, 4],
            "Demands": {"Box1": 2, "Box2": 1, "Box3": 3},
            "Capacity": 10,
            "Sense": "maximize",
            "Relax": True,
        },
    )

    run_case(
        "resource_allocation",
        {
            "Items": ["TaskA", "TaskB", "TaskC"],
            "Weights": [2, 3, 4],
            "WeightsRAM": [1, 4, 2],
            "Values": [5, 7, 6],
            "Demands": {"TaskA": 2, "TaskB": 1, "TaskC": 1},
            "Capacity": 8,
            "CapacityRAM": 6,
            "Sense": "minimize",
            "Relax": True,
        },
    )

    run_case(
        "scheduling",
        {
            "Items": ["E1", "E2", "E3"],
            "Values": [1, 1, 1],
            "Shifts": ["Day", "Night"],
            "Demands": {"Day": 2, "Night": 1},
            "MaxShiftsPerEmployee": 1,
            "Sense": "maximize",
            "Relax": True,
        },
    )


if __name__ == "__main__":
    main()
