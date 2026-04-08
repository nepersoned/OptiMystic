using Random

struct SolverPayload
    domain::String
    solver::String
    params::Dict{String, Any}
end

function _to_solver_payload(payload::Dict{String, Any})
    domain = lowercase(string(get(payload, "domain", "generic")))
    solver = lowercase(string(get(payload, "solver", "mip")))
    params_any = get(payload, "params", Dict{String, Any}())
    params = params_any isa Dict{String, Any} ? params_any : _as_dict(params_any)
    return SolverPayload(domain, solver, params)
end

function solve_mip(payload::Dict{String, Any})
    params = _as_dict(get(payload, "params", Dict{String, Any}()))
    ir = _extract_ir(params)
    sense = _normalize_sense(get(params, "Sense", "minimize"))
    opts = _ga_options(params)
    ga_cfg = _as_dict(get(params, "GA", Dict{String, Any}()))
    variable_count = length(_as_vector(get(ir, "variables", Any[])))
    ga_variable_threshold = max(0, _to_int(get(ga_cfg, "variable_threshold", 10000), 10000))
    use_ga = variable_count > ga_variable_threshold

    seed = _to_int(get(opts, "seed", 0), 0)
    if seed != 0
        Random.seed!(seed)
    end

    ga = if use_ga
        solve_ga_hotspots(
            ir,
            sense;
            population=_to_int(get(opts, "population", 48), 48),
            generations=_to_int(get(opts, "generations", 18), 18),
            elite_k=_to_int(get(opts, "elite_k", 6), 6),
            hotspot_threshold=_to_float(get(opts, "hotspot_threshold", 0.85), 0.85),
            mutation_rate=_to_float(get(opts, "mutation_rate", 0.15), 0.15),
            library_ops=_bool_from_any(get(opts, "library_ops", false), false),
        )
    else
        Dict{String, Any}(
            "status" => "Skipped",
            "hotspots" => Any[],
            "start_values" => Dict{String, Float64}(),
            "fixed_values" => Dict{String, Float64}(),
        )
    end
    start_values = Dict{String, Float64}()
    for (k, v) in get(ga, "start_values", Dict{String, Float64}())
        start_values[string(k)] = _to_float(v, 0.0)
    end
    for (k, v) in get(ga, "fixed_values", Dict{String, Float64}())
        key = string(k)
        if !haskey(start_values, key)
            start_values[key] = _to_float(v, 0.0)
        end
    end

    result = solve_mip_from_ir(ir, sense; warm_start=start_values)
    result["details"] = Dict(
        "engine" => "MIP",
        "message" => use_ga ? "MIP solved with GA warm start" : "MIP solved directly (GA skipped by variable threshold)",
        "hotspot_count" => length(get(ga, "hotspots", Any[])),
        "ga_used" => use_ga,
        "variable_count" => variable_count,
        "ga_variable_threshold" => ga_variable_threshold,
    )
    return result
end

function route_solver(payload::Dict{String, Any})
    return route_solver(_to_solver_payload(payload))
end

function route_solver(payload::SolverPayload)
    solver = payload.solver
    typed_payload = Dict{String, Any}(
        "domain" => payload.domain,
        "solver" => payload.solver,
        "params" => payload.params,
    )

    if solver == "cp"
        return Dict{String, Any}(
            "status" => "Error",
            "error_msg" => "CP is Python-only runtime",
            "objective" => nothing,
            "variables" => Any[],
            "constraints" => Any[],
            "solve_time" => 0.0,
            "lp_sensitivity" => false,
        )
    end
    if solver == "ga"
        return solve_ga_only(typed_payload)
    end
    if solver == "cg"
        return solve_cg(typed_payload)
    end
    if solver == "st"
        return solve_st(typed_payload)
    end
    if solver == "nlp"
        return solve_nlp(typed_payload)
    end
    if solver == "minlp"
        return solve_minlp(typed_payload)
    end
    return solve_mip(typed_payload)
end
