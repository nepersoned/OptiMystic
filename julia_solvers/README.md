# Julia Solvers Runtime

Julia optimization ecosystem for OptiMystic, handling all non-CP solver types.

**Design**: Python CLI delegates non-CP requests to Julia subprocess via JSON I/O. Julia dispatches to task-specific solvers (MIP, GA, CG, ST, NLP, MINLP) with automatic fallback chains.

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
- Detects GA hotspots and injects warmstart hints (start_values + fixed_values merged as start hints)
- `set_silent()` suppresses HiGHS logging for clean JSON stdout
- Status mapping: `OPTIMAL`, `INFEASIBLE`, `TIME_LIMIT`, `FEASIBLE`, etc.

**Example Call:**
```julia
result = solve_mip_from_ir(ir, opts)
# => { status, objective, variables, constraints, solve_time }
```

---

### NLP (Nonlinear Programming)

| Role | Compatibility |
|---|---|
| **Solver** (solver="nlp") | Generic IR via JuMP + Ipopt |
| **Warmstart provider** | GA hotspots are injected as start-value hints |

**File**: [src/solvers/nlp.jl](src/solvers/nlp.jl)

**Key Features:**
- Parses a small nonlinear AST contract from `params.NLP`
- Builds Ipopt-backed JuMP models for smooth nonlinear objectives and constraints
- Uses GA hotspot results as warm starts (no hard fixing)
- Emits solver diagnostics including GA counts and nonlinear term counts

**Example Call:**
```julia
result = solve_nlp(payload)
# => { status, objective, variables, constraints, solve_time, details }
```

### MINLP (Mixed-Integer Nonlinear Programming)

| Role | Compatibility |
|---|---|
| **Solver** (solver="minlp") | Generic IR + nonlinear AST via Juniper + Ipopt + HiGHS |
| **Warmstart provider** | GA hotspots are injected as start-value hints |

**File**: [src/solvers/minlp.jl](src/solvers/minlp.jl)

**Key Features:**
- Handles mixed-integer nonlinear models by combining Juniper (outer MINLP orchestration), Ipopt (NLP subproblems), and HiGHS (MIP subproblems).
- Reuses the nonlinear AST parsing path used by NLP (`objective_expr`, nonlinear constraint expressions).
- Keeps GA guidance as warm-start only (no hard-fix anti-pattern).
- Emits MINLP-specific diagnostics (`discrete_variable_count`, `nonlinear_term_count`, GA usage).

**Example Call:**
```julia
result = solve_minlp(payload)
# => { status, objective, variables, constraints, solve_time, details }
```

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
- `_crossover_with_library()` — Optional external crossover operator (with native fallback)
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
    "hotspot_threshold": 0.95,
    "library_ops": true
  }
}
```

`library_ops=true` enables phase-1 hybrid GA behavior: if `Evolutionary.jl` is installed,
the crossover step tries a library operator first; otherwise it automatically falls back to
the built-in crossover.

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
  ├─ "nlp" → solve_nlp()
  │         └─ GA-guided nonlinear solve via Ipopt
  ├─ "minlp" → solve_minlp()
  │           └─ Juniper + Ipopt + HiGHS mixed-integer nonlinear solve
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
| Nonlinear generic model | generic | nlp | `solver="nlp"` + nonlinear AST in `params.NLP` | Ipopt-backed smooth NLP with GA warm start |
| Cutting stock | cutting | cg | `Mode="cutting"` + Items | Specialized column generation pipeline |
| Cutting (large) | cutting | mip | No CG data | Generic MIP faster for many items |
| Bin packing | packing | mip | Default | Generic MIP handles variable dimensions |
| Resource allocation | resourcing | st | `Mode="resourcing"` + Scenarios | Risk-aware multi-stage planning |
| Resource (deterministic) | resourcing | mip | No scenarios | Simplification of ST |
| Mixed-integer nonlinear model | generic | minlp | `solver="minlp"` + nonlinear AST in `params.MINLP` | Discrete + nonlinear support via Juniper |
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
                ├─ minlp.jl: solve_minlp()
              └─ ga.jl: solve_ga_only()
          └─ return JSON (status, objective, variables)
```

---

## Quick Start (One Verified Path)

For reliable demo/evaluation, use the same root smoke flow.

### 1) Prepare Julia packages once

```powershell
cd C:\Users\kevin\OneDrive\Desktop\OptiMystic\julia_solvers
julia --project=. -e "using Pkg; Pkg.instantiate()"
```

### 2) Run end-to-end test from JupyterLab

```powershell
cd C:\Users\kevin\OneDrive\Desktop\OptiMystic
jupyter lab
```

Open `examples/test_jupyterlab_full_pipeline.ipynb` and run the Julia-only section.

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
