# Julia Solvers Runtime

Julia runtime for OptiMystic solver families beyond Python CP/VRP.

## Solver Families

Implemented in `src/solvers/`:
- `mip.jl`
- `ga.jl`
- `cg.jl`
- `st.jl`
- `nlp.jl`
- `minlp.jl`

Dispatcher:
- `src/solvers/router.jl`

CLI entry:
- `cli_solver.jl`

## Role in System

Python API delegates selected domains/solver types to Julia.
Julia returns standardized JSON fields:
- `status`
- `objective`
- `variables`
- `constraints`
- `solve_time`
- `details` (when available)

## Typical Domain Mapping

- `packing` -> `mip` (primary)
- `cutting` -> `cg`/`mip`
- `resourcing` -> `st`/`mip`
- `generic` -> `nlp`/`minlp`/`mip`

## Local Run (Julia only)

```bash
cd /app/julia_solvers
julia --project=. cli_solver.jl --domain packing --solver mip --input-json '{"params":{"Items":[{"Name":"A","Weight":2,"Value":5,"Demand":1}],"Vehicles":[{"Capacity":3}]}}'
```

## Development Notes

- Keep `Project.toml` / `Manifest.toml` in sync.
- Runtime I/O contract is JSON-first for stable interop with Python API and agent loop.
- If extending solver families, register new route in `src/solvers/router.jl`.
