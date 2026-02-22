"""
Column generation for cutting stock. Pyomo for master/sub; knapsack isolated.
"""
from typing import Any, Dict, List, Optional, Tuple

try:
    import pyomo.environ as pyo
except ImportError:
    pyo = None


def build_model(domain: str, params: Dict[str, Any]) -> Tuple[Any, List[Any], List[Dict[str, Any]]]:
    """
    Build and solve CG model for cutting domain.
    Returns (model, [], []) for solver_engine compatibility.
    """
    if domain != "cutting":
        return [], [], []
    
    if pyo is None:
        raise RuntimeError("Pyomo required for logic_cg")
    
    cg_solver = CuttingStockCG(params)
    prob, patterns, x_int, duals = cg_solver.solve()
    res_dict = format_results_for_dashboard(prob, patterns, x_int, params.get("Items", []), duals)
    
    # Build structured output for solver_engine
    fixed_vars = []
    constraints = []
    obj_parts = []

    for v in res_dict["variables"]:
        fixed_vars.append({"name": v["Variable"], "type": "Continuous"})
        if v["Variable"].startswith("U_"):
            obj_parts.append(
                {"coef": float(cg_solver.stock_cost), "var": v["Variable"]}
            )
        constraints.append(
            {"type": "fix", "var": v["Variable"], "value": float(v["Value"])}
        )

    demand_consts = []
    for i, name in enumerate(params.get("Items", [])):
        item_var_names = [
            v["Variable"]
            for v in res_dict["variables"]
            if v["Variable"].startswith(f"A_IT{i}_")
        ]
        if item_var_names:
            terms = [{"coef": 1.0, "var": vn} for vn in item_var_names]
            demand_consts.append(
                {
                    "type": "linear",
                    "terms": terms,
                    "sense": ">=",
                    "rhs": float(params.get("Demands", {}).get(name, 0)),
                }
            )

    objective_terms = obj_parts if obj_parts else []
    return objective_terms, demand_consts + constraints, fixed_vars


def solve_knapsack(
    duals: List[float],
    item_lens: List[float],
    kerf: float,
    stock_len: float,
) -> Tuple[List[int], float]:
    """
    Pricing subproblem: max sum_i duals[i]*a_i s.t. sum_i (len_i+kerf)*a_i <= stock_len+kerf, a_i integer.
    Returns (new_pattern as list of counts, objective value).
    """
    if pyo is None:
        raise RuntimeError("Pyomo required for logic_cg")

    n = len(duals)
    if n == 0:
        return [], 0.0

    m = pyo.ConcreteModel()
    m.I = pyo.Set(initialize=range(n))
    m.a = pyo.Var(m.I, domain=pyo.NonNegativeIntegers)
    m.OBJ = pyo.Objective(
        expr=sum(duals[i] * m.a[i] for i in m.I),
        sense=pyo.maximize,
    )
    m.Cap = pyo.Constraint(
        expr=sum((item_lens[i] + kerf) * m.a[i] for i in m.I) <= stock_len + kerf
    )

    opt = pyo.SolverFactory("cbc")
    res = opt.solve(m, tee=False)
    if res.solver.termination_condition != pyo.TerminationCondition.optimal:
        return [0] * n, 0.0

    pattern = [int(pyo.value(m.a[i], default=0)) for i in m.I]
    obj_val = float(pyo.value(m.OBJ))
    return pattern, obj_val


class CuttingStockCG:
    def __init__(self, params: Dict[str, Any]):
        self.items = params.get("Items", [])
        self.demands = params.get("Demands", {})
        self.item_lens = params.get("ItemLens", [])
        self.kerf = float(params.get("Kerf", 0.0))

        raw_stocks = params.get("Stocks", [])
        if not raw_stocks:
            self.main_stock = {"Name": "Default", "Length": 1000, "Cost": 100}
        else:
            self.main_stock = max(raw_stocks, key=lambda x: float(x["Length"]))

        self.stock_len = float(self.main_stock["Length"])
        self.stock_cost = float(self.main_stock["Cost"])

    def solve(
        self,
    ) -> Tuple[Any, List[List[int]], Any, List[float]]:
        """Column generation loop: master (Pyomo) + pricing (knapsack). Returns (final_model, patterns, x_int_ref, duals)."""
        if pyo is None:
            raise RuntimeError("Pyomo required for logic_cg")

        patterns: List[List[int]] = []
        for i in range(len(self.items)):
            if self.item_lens[i] + self.kerf <= self.stock_len + self.kerf:
                pat = [0] * len(self.items)
                pat[i] = 1
                patterns.append(pat)

        opt = pyo.SolverFactory("cbc")
        loop_count = 0

        n_items = len(self.items)

        while True:
            loop_count += 1
            # Master LP
            master = pyo.ConcreteModel()
            master.J = pyo.Set(initialize=range(len(patterns)))
            master.I = pyo.Set(initialize=range(n_items))
            master.x = pyo.Var(master.J, domain=pyo.NonNegativeReals)
            master.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

            def demand_rule(m, i):
                demand = self.demands[self.items[i]]
                return sum(patterns[j][i] * m.x[j] for j in m.J) >= demand

            master.Demand = pyo.Constraint(master.I, rule=demand_rule)
            master.OBJ = pyo.Objective(
                expr=sum(self.stock_cost * master.x[j] for j in master.J),
                sense=pyo.minimize,
            )

            res = opt.solve(master, tee=False)
            duals = [0.0] * n_items
            if res.solver.termination_condition == pyo.TerminationCondition.optimal:
                try:
                    for i in master.I:
                        duals[i] = float(master.dual[master.Demand[i]])
                except Exception:
                    pass

            new_pat, best_reduced = solve_knapsack(
                duals, self.item_lens, self.kerf, self.stock_len
            )

            if best_reduced <= self.stock_cost + 1e-5:
                break
            if new_pat in patterns:
                break
            patterns.append(new_pat)
            if loop_count > 500:
                break

        # Master integer
        final = pyo.ConcreteModel()
        final.J = pyo.Set(initialize=range(len(patterns)))
        final.I = pyo.Set(initialize=range(n_items))
        final.x = pyo.Var(final.J, domain=pyo.NonNegativeIntegers)
        final.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

        def final_demand_rule(m, i):
            demand = self.demands[self.items[i]]
            return sum(patterns[j][i] * m.x[j] for j in m.J) >= demand

        final.Demand = pyo.Constraint(final.I, rule=final_demand_rule)
        final.OBJ = pyo.Objective(
            expr=sum(self.stock_cost * final.x[j] for j in final.J),
            sense=pyo.minimize,
        )

        res = opt.solve(final, tee=False, options={"seconds": 10})
        final_duals = [0.0] * n_items
        if res.solver.termination_condition == pyo.TerminationCondition.optimal:
            try:
                for i in final.I:
                    final_duals[i] = float(final.dual[final.Demand[i]])
            except Exception:
                pass

        return final, patterns, final.x, final_duals


def format_results_for_dashboard(
    prob: Any,
    patterns: List[List[int]],
    x_ref: Any,
    items: List[str],
    duals: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Build variables/constraints list and status/objective from Pyomo model."""
    if pyo is None:
        return {"status": "Error", "objective": None, "variables": [], "constraints": []}

    variables = []
    pat_idx = 0
    for j in prob.J:
        count = int(pyo.value(prob.x[j], default=0))
        if count <= 0:
            continue
        pat_content = patterns[j]
        for _ in range(count):
            bin_id = f"CG_Bin_{pat_idx}"
            pat_idx += 1
            variables.append({"Variable": f"U_{bin_id}", "Value": 1.0})
            for i_idx, qty in enumerate(pat_content):
                if qty > 0:
                    variables.append(
                        {"Variable": f"A_IT{i_idx}_{bin_id}", "Value": float(qty)}
                    )

    constraints_data = []
    if duals:
        for i, dual_val in enumerate(duals):
            constraints_data.append(
                {"Constraint": f"C_{i}", "Shadow Price": dual_val, "Slack": 0.0}
            )

    obj_val = float(pyo.value(prob.OBJ)) if prob.OBJ else 0.0
    status = "Optimal"

    return {
        "status": status,
        "objective": obj_val,
        "variables": variables,
        "constraints": constraints_data,
    }
