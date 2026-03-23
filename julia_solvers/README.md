# Julia Solvers Runtime

Julia optimization ecosystem for OptiMystic, handling all non-CP solver types.

**Design**: Python CLI delegates non-CP requests to Julia subprocess via JSON I/O. Julia dispatches to task-specific solvers (MIP, GA, CG, ST) with automatic fallback chains.

## Solver-Domain Compatibility

### MIP (Mixed-Integer Programming) - JuMP + HiGHS

| Domain | Compatibility | Role | Required Input |
|--------|---|---|---|
| **scheduling** | ✅ | Fallback if CP not used | IR (variables, constraints, objective) |
| **cutting** | ✅ | Fallback if CG data unavailable | IR + domain params (Items, Stocks) |
| **packing** | ✅ | Primary | IR (bin capacity, item weights, values) |
| **resourcing** | ✅ | Fallback if ST data unavailable | IR (resource capacity, demand) |
| **generic** | ✅ | Primary | Direct IR |

**File**: [src/solvers/mip.jl](src/solvers/mip.jl)

**Key Features:**
- Builds generic LP/MIP model from IR (variable types, constraint parsing)
- Detects GA hotspots and injects warmstart values (start_values, fixed_values)
- `set_silent()` suppresses HiGHS logging for clean JSON stdout
- Status mapping: `OPTIMAL`, `INFEASIBLE`, `TIME_LIMIT`, `FEASIBLE`, etc.

**Example Call:**
```julia
result = solve_mip_from_ir(ir, opts)
# => { status, objective, variables, constraints, solve_time }
```

---

### GA (Genetic Algorithm / Evolutionary Search)

| Role | Compatibility |
|---|---|
| **Solver** (solver="ga") | All domains via IR |
| **Warmstart provider** | Auto-embedded in MIP/CG/ST |
| **Hotspot extraction** | Detects converged variables for fixed_values |

**File**: [src/solvers/ga.jl](src/solvers/ga.jl)

**Key Functions:**
- `solve_ga_hotspots()` — Evolutionary search returning candidate solution + hotspots
- `solve_ga_only()` — Standalone GA (pure evolutionary, no MIP refinement)
- `_make_initial_population()` — Random/feasible population generation
- `_repair_candidate!()` — Constraint violation repair
- `_mutate_value()` — Perturbation operator
- `_crossover()` — Parent combination
- `_ga_options()` — Parameter configuration (seed, generations, population, elite_k, mutation_rate)

**Hotspot-Based Warmstart Flow:**
1. GA runs evolutionary loop (generations)
2. Elite candidates converge on variable values
3. Hotspot detection: convergence threshold crossed → include in fixed_values
4. MIP receives start_values (elite best) + fixed_values (hotspots)
5. MIP solver uses these to initialize branch-and-bound

**Example Call:**
```julia
# As standalone solver
result = solve_ga_only(ir, opts)
# => { status, objective, variables, solve_time }

# As warmstart provider (internal to MIP/CG/ST)
candidates, hotspots = solve_ga_hotspots(ir, opts)
# candidates => elite solutions
# hotspots => { var_name => fixed_value, ... }
```

**Parameters:**
```json
{
  "GA": {
    "seed": 42,
    "generations": 100,
    "population": 50,
    "elite_k": 5,
    "mutation_rate": 0.1,
    "hotspot_threshold": 0.95
  }
}
```

---

### CG (Column Generation)

| Domain | Compatibility | Trigger |
|---|---|---|
| **cutting** | ✅ Primary | `Mode="cutting"` + Items/ItemLens/Demands/Stocks |
| **All others** | ✅ Fallback | Missing CG data → GA + MIP fallback |

**File**: [src/solvers/cg.jl](src/solvers/cg.jl)

**Specialized Path (Cutting Stock):**

Model Structure:
- **Master LP**: Minimize cost across bin types, duals inform pricing
- **Pricing Subproblem**: Integer knapsack (maximize reduced-cost utility per bin)
- **Integer Master**: Final solve with all columns (binary: use this pattern)

Flow:
1. `_cg_initial_patterns()` — Generate trivial patterns (one item type per bin)
2. `_cg_solve_master_lp()` — Solve LP relaxation, extract duals
3. `_cg_pricing_knapsack()` — Solve integer knapsack with dual values
4. Repeat until no improving columns found
5. `_solve_cg_cutting()` — Solve integer master with all patterns

**Example Call:**
```julia
result = solve_cg(ir, opts)
# If Mode="cutting" + Items present:
#   -> _solve_cg_cutting() [Master/Pricing/Integer Master]
#   => { status, objective, variables, patterns, solve_time }
# Else:
#   -> GA hotspot + MIP fallback
```

**Required Input (for specialized path):**
```json
{
  "Mode": "cutting",
  "Items": [
    { "Name": "A", "Length": 10, "Demand": 5 },
    { "Name": "B", "Length": 8, "Demand": 3 }
  ],
  "ItemLens": [10, 8],
  "Demands": { "A": 5, "B": 3 },
  "Stocks": [
    { "Length": 100, "Cost": 1.0, "Quantity": 10 }
  ],
  "Kerf": 0.1
}
```

---

### ST (Stochastic Two-Stage Optimization)

| Domain | Compatibility | Trigger |
|---|---|---|
| **resourcing** | ✅ Primary | `Mode="resourcing"` + Items/Scenarios |
| **All others** | ✅ Fallback | Missing ST data → GA + MIP fallback |

**File**: [src/solvers/st.jl](src/solvers/st.jl)

**Specialized Path (Stochastic Resourcing):**

Model Structure:
- **Stage 1**: X_i (resource quantities to allocate, first-stage integer decision)
- **Stage 2 (Recourse)**: Shortfall_s_i (unmet demand, second-stage continuous recourse)
- **Objective**: Maximize expected service value − expected shortfall penalty

Scenario Handling:
- Each scenario has demand distribution + realization probability
- Probabilities are auto-normalized
- Expected value = Σ_s probability_s × (served_s − shortfall_s)

Flow:
1. `_scenario_probability_vector()` — Normalize scenario weights
2. Build X_i variables (integer, first stage)
3. For each scenario: add Shortfall_s_i variables (continuous)
4. Add constraints linking X_i → served_s → Shortfall_s_i
5. Objective: Maximize Σ probability × (value × served − penalty × shortfall)
6. `solve_st_proxy_with_ir()` — HiGHS solve

**Example Call:**
```julia
result = solve_st(ir, opts)
# If Mode="resourcing" + Items + Scenarios present:
#   -> build full stochastic model
#   => { status, objective, variables, scenarios, solve_time }
# Else:
#   -> GA hotspot + MIP fallback
```

**Required Input (for specialized path):**
```json
{
  "Mode": "resourcing",
  "Items": [
    { "Name": "CPU_Core", "Value": 10, "CostPerUnit": 1.5 },
    { "Name": "RAM_GB", "Value": 5, "CostPerUnit": 0.8 }
  ],
  "Scenarios": [
    {
      "Name": "Demand_Low",
      "Probability": 0.3,
      "Demands": { "CPU_Core": 50, "RAM_GB": 100 }
    },
    {
      "Name": "Demand_High",
      "Probability": 0.7,
      "Demands": { "CPU_Core": 150, "RAM_GB": 300 }
    }
  ],
  "CPU": 200,
  "RAM": 400,
  "ShortfallPenalty": 5.0
}
```

---

## Runtime Dispatch (router.jl)

Entry point: `route_solver(ir, opts)`

**Dispatcher Logic:**
```
solver parameter
  ├─ "ga" → solve_ga_only()
  ├─ "cg" → solve_cg()
  │         ├─ Mode="cutting" + Items → _solve_cg_cutting()
  │         └─ else → GA + MIP fallback
  ├─ "st" → solve_st()
  │         ├─ Items + Scenarios → full stochastic
  │         └─ else → GA + MIP fallback
  └─ "mip" (default)
      └─ solve_mip()
          ├─ GA hotspot calculation
          └─ MIP warmstart solve
```

**File**: [src/solvers/router.jl](src/solvers/router.jl)

---

## Solver-Domain Selection Guide

| Goal | Domain | Solver | Trigger | Reason |
|---|---|---|---|---|
| Schedule staff | scheduling | cp | `template_type="scheduling"` | OR-Tools CP-SAT optimal for binary assignment |
| Schedule (relaxed) | scheduling | mip | Direct IR | Standard LP relaxation |
| Cutting stock | cutting | cg | `Mode="cutting"` + Items | Specialized column gen, educaitonal value |
| Cutting (large) | cutting | mip | No CG data | Generic MIP faster for many items |
| Bin packing | packing | mip | Default | Generic MIP handles variable dimensions |
| Resource allocation | resourcing | st | `Mode="resourcing"` + Scenarios | Risk-aware multi-stage planning |
| Resource (deterministic) | resourcing | mip | No scenarios | Simplification of ST |
| Custom opt. problem | generic | mip | Direct IR | Direct IR passthrough |
| Exploratory search | any | ga | `solver="ga"` | Pure evolutionary (no MIP refinement) |

---

## Architecture

```
cli_solver.py (non-cp request)
  └─ _run_julia_solver() subprocess
      └─ julia_solvers/src/main.jl
          └─ load IR from stdin (JSON)
          └─ router.jl: route_solver()
              ├─ mip.jl: solve_mip_from_ir()
              │   ├─ ga.jl: solve_ga_hotspots() [warmstart]
              │   └─ JuMP + HiGHS
              ├─ cg.jl: solve_cg()
              ├─ st.jl: solve_st()
              └─ ga.jl: solve_ga_only()
          └─ return JSON (status, objective, variables)
```

---

## Quick Start (Windows cmd.exe)

### 1) Install Julia & Dependencies

```cmd
# Download Julia from https://julialang.org/downloads/
# (Recommended: v1.10+ for stability)

# Add Julia to PATH, then:
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic\julia_solvers
julia --project=. -e "using Pkg; Pkg.instantiate()"
```

### 2) Test Julia Solvers Directly

```cmd
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic

# MIP example (packing)
python python_solvers\cli_solver.py --domain packing --solver mip --params "{\"Items\":[{\"Name\":\"A\",\"Weight\":2,\"Value\":10},{\"Name\":\"B\",\"Weight\":3,\"Value\":12}],\"Vehicles\":[{\"Capacity\":5}]}"

# CG example (cutting)
python python_solvers\cli_solver.py --domain cutting --solver cg --params "{\"Mode\":\"cutting\",\"Items\":[{\"Name\":\"A\",\"Length\":10,\"Demand\":5},{\"Name\":\"B\",\"Length\":8,\"Demand\":3}],\"Stocks\":[{\"Length\":100,\"Cost\":1.0}],\"Kerf\":0.1}"

# ST example (resourcing)
python python_solvers\cli_solver.py --domain resourcing --solver st --params "{\"Mode\":\"resourcing\",\"Items\":[{\"Name\":\"CPU\",\"Value\":10}],\"Scenarios\":[{\"Name\":\"S1\",\"Probability\":1.0,\"Demands\":{\"CPU\":50}}],\"CPU\":100,\"ShortfallPenalty\":5.0}"

# GA example (exploratory)
python python_solvers\cli_solver.py --domain generic --solver ga --params "{\"Items\":[{\"Name\":\"A\",\"Weight\":2},{\"Name\":\"B\",\"Weight\":3}],\"GA\":{\"seed\":42,\"generations\":50}}"
```

### 3) Test Go API End-to-End

```cmd
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic\server
go run .\cmd\server\main.go

# In another terminal:
curl -X POST http://localhost:8080/api/optimize ^
  -H "Content-Type: application/json" ^
  -d "{\"template_type\":\"packing\",\"solver_type\":\"mip\",\"params\":{...}}"
```

---

## Status Codes

All solvers return normalized status:

| Status | Meaning | Solver |
|--------|---------|--------|
| `Optimal` | Proven optimum found | MIP, CG, ST, GA |
| `Feasible` | Feasible solution (not proven optimal) | MIP (time_limit), GA |
| `Infeasible` | No feasible solution | MIP, CG, ST |
| `Unbounded` | Unbounded objective | MIP |
| `Error` | Solver failure / unsupported domain | Any |

---

## Debugging

### Julia Solver Logs

By default, HiGHS logging is suppressed (`set_silent()`). To enable:

```julia
# In mip.jl, comment out:
# optimizer = JuMP.optimizer_with_attributes(HiGHS.Optimizer, "log_to_console" => false)
# And use:
optimizer = JuMP.optimizer_with_attributes(HiGHS.Optimizer, "log_to_console" => true)
```

### JSON I/O Validation

Test direct Julia invocation:
```cmd
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic\julia_solvers
echo {\"IR\":[...]} | julia --project=. src/main.jl
```

### Warmstart Debugging

In `mip.jl`, add logging before HiGHS solve:
```julia
if opts["GA"]["enabled"]
    println(stderr, "GA hotspots: ", opts["GA"]["fixed_values"])
end
```

---

## Future Enhancements

- [ ] Warm-start caching across solver calls
- [ ] Parallel GA population evaluation
- [ ] CG dynamic column selection (heuristics beyond knapsack)
- [ ] ST risk measures (CVaR, robust optimization)
- [ ] Integration with Gurobi/CPLEX for larger problems
