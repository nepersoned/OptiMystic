using Random

function solve_mip(payload::Dict{String, Any})
    params = _as_dict(get(payload, "params", Dict{String, Any}()))
    ir = _extract_ir(params)
    sense = _normalize_sense(get(params, "Sense", "minimize"))
    opts = _ga_options(params)

    seed = _to_int(get(opts, "seed", 0), 0)
    if seed != 0
        Random.seed!(seed)
    end

    ga = solve_ga_hotspots(
        ir,
        sense;
        population=_to_int(get(opts, "population", 48), 48),
        generations=_to_int(get(opts, "generations", 18), 18),
        elite_k=_to_int(get(opts, "elite_k", 6), 6),
        hotspot_threshold=_to_float(get(opts, "hotspot_threshold", 0.85), 0.85),
        mutation_rate=_to_float(get(opts, "mutation_rate", 0.15), 0.15),
    )
    start_values = Dict{String, Float64}()
    for (k, v) in get(ga, "start_values", Dict{String, Float64}())
        start_values[string(k)] = _to_float(v, 0.0)
    end

    result = solve_mip_from_ir(ir, sense; warm_start=start_values)
    result["details"] = Dict(
        "engine" => "MIP",
        "message" => "MIP solved with GA warm start",
        "hotspot_count" => length(get(ga, "hotspots", Any[])),
    )
    return result
end

function route_solver(payload::Dict{String, Any})
    solver = lowercase(string(get(payload, "solver", "mip")))

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
        return solve_ga_only(payload)
    end
    if solver == "cg"
        return solve_cg(payload)
    end
    if solver == "st"
        return solve_st(payload)
    end
    return solve_mip(payload)
end
