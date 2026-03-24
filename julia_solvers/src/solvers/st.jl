using JuMP
using HiGHS
using Random

function _st_status(model::Model)
    return _status_from_model(model)
end

function _scenario_probability_vector(scenarios::Vector{Any})
    probs = Float64[]
    for raw in scenarios
        s = _as_dict(raw)
        p = max(0.0, _to_float(get(s, "probability", 0.0), 0.0))
        push!(probs, p)
    end
    total = sum(probs)
    if total <= 0
        n = max(1, length(scenarios))
        return [1.0 / n for _ in 1:n]
    end
    return [p / total for p in probs]
end

function _solve_st_proxy_with_ir(ir::Dict{String, Any}, sense::String, opts::Dict{String, Any})
    seed = _to_int(get(opts, "seed", 0), 0)
    if seed != 0
        Random.seed!(seed)
    end

    ga = solve_ga_hotspots(
        ir,
        sense;
        population=_to_int(get(opts, "population", 48), 48),
        generations=_to_int(get(opts, "generations", 24), 24),
        elite_k=_to_int(get(opts, "elite_k", 8), 8),
        hotspot_threshold=_to_float(get(opts, "hotspot_threshold", 0.85), 0.85),
        mutation_rate=_to_float(get(opts, "mutation_rate", 0.15), 0.15),
        library_ops=_bool_from_any(get(opts, "library_ops", false), false),
    )
    start_values = Dict{String, Float64}()
    for (k, v) in get(ga, "start_values", Dict{String, Float64}())
        start_values[string(k)] = _to_float(v, 0.0)
    end

    mip = solve_mip_from_ir(ir, sense; warm_start=start_values)
    mip["details"] = Dict(
        "engine" => "ST",
        "message" => "ST fallback: IR + GA warm start",
        "hotspot_count" => length(get(ga, "hotspots", Any[])),
    )
    return mip
end

function solve_st(payload::Dict{String, Any})
    started = time()
    params = _as_dict(get(payload, "params", Dict{String, Any}()))
    ir = _extract_ir(params)
    sense = _normalize_sense(get(params, "Sense", "minimize"))
    st_spec = _as_dict(get(params, "ST", Dict{String, Any}()))
    opts = _ga_options(params)

    items = _as_vector(get(st_spec, "items", Any[]))
    scenarios = _as_vector(get(st_spec, "scenarios", Any[]))
    if isempty(items) || isempty(scenarios)
        return _solve_st_proxy_with_ir(ir, sense, opts)
    end

    item_names = [string(i) for i in items]
    n = length(item_names)
    s_count = length(scenarios)
    probs = _scenario_probability_vector(scenarios)

    cpu_map = _as_dict(get(st_spec, "cpu", Dict{String, Any}()))
    ram_map = _as_dict(get(st_spec, "ram", Dict{String, Any}()))
    values_base = _as_dict(get(st_spec, "values", Dict{String, Any}()))
    demands_base = _as_dict(get(st_spec, "demands", Dict{String, Any}()))
    cap_cpu = _to_float(get(st_spec, "capacity_cpu", 0.0), 0.0)
    cap_ram = _to_float(get(st_spec, "capacity_ram", 0.0), 0.0)
    penalty = max(0.0, _to_float(get(st_spec, "shortfall_penalty", 1000.0), 1000.0))

    # GA warm-start on IR if available.
    seed = _to_int(get(opts, "seed", 0), 0)
    if seed != 0
        Random.seed!(seed)
    end
    ga = solve_ga_hotspots(
        ir,
        sense;
        population=_to_int(get(opts, "population", 48), 48),
        generations=_to_int(get(opts, "generations", 24), 24),
        elite_k=_to_int(get(opts, "elite_k", 8), 8),
        hotspot_threshold=_to_float(get(opts, "hotspot_threshold", 0.85), 0.85),
        mutation_rate=_to_float(get(opts, "mutation_rate", 0.15), 0.15),
        library_ops=_bool_from_any(get(opts, "library_ops", false), false),
    )
    start_values = Dict{String, Float64}()
    for (k, v) in get(ga, "start_values", Dict{String, Float64}())
        start_values[string(k)] = _to_float(v, 0.0)
    end

    model = Model(HiGHS.Optimizer)
    set_silent(model)
    try
        set_attribute(model, "output_flag", false)
    catch err
        @warn "Failed to set ST output_flag" error=err
    end

    @variable(model, X[1:n] >= 0, Int)
    @variable(model, Shortfall[1:s_count, 1:n] >= 0)

    for i in 1:n
        vn = "X_$(i-1)"
        if haskey(start_values, vn)
            try
                set_start_value(X[i], start_values[vn])
            catch err
                @warn "Failed to set ST warm-start value" variable=vn value=start_values[vn] error=err
            end
        end
    end

    @constraint(model, CPU_CAP, sum(_to_float(get(cpu_map, item_names[i], 0.0), 0.0) * X[i] for i in 1:n) <= cap_cpu)
    @constraint(model, RAM_CAP, sum(_to_float(get(ram_map, item_names[i], 0.0), 0.0) * X[i] for i in 1:n) <= cap_ram)

    demand_constraints = Dict{Tuple{Int, Int}, ConstraintRef}()
    for s_idx in 1:s_count
        s_data = _as_dict(scenarios[s_idx])
        s_demands = _as_dict(get(s_data, "demands", Dict{String, Any}()))
        for i in 1:n
            rhs = _to_float(get(s_demands, item_names[i], get(demands_base, item_names[i], 0.0)), 0.0)
            demand_constraints[(s_idx, i)] = @constraint(model, X[i] + Shortfall[s_idx, i] >= rhs)
        end
    end

    expected_service = AffExpr(0.0)
    expected_shortfall = AffExpr(0.0)
    for s_idx in 1:s_count
        s_data = _as_dict(scenarios[s_idx])
        s_values = _as_dict(get(s_data, "values", Dict{String, Any}()))
        p = probs[s_idx]
        for i in 1:n
            value_coef = _to_float(get(s_values, item_names[i], get(values_base, item_names[i], 0.0)), 0.0)
            add_to_expression!(expected_service, p * value_coef, X[i])
            add_to_expression!(expected_shortfall, p * penalty, Shortfall[s_idx, i])
        end
    end

    if sense == "maximize"
        @objective(model, Max, expected_service - expected_shortfall)
    else
        @objective(model, Min, expected_shortfall - expected_service)
    end

    optimize!(model)

    status = _st_status(model)
    feasible = primal_status(model) == MOI.FEASIBLE_POINT
    objective_val = feasible ? objective_value(model) : nothing

    variables = Vector{Any}()
    if feasible
        for i in 1:n
            push!(variables, Dict("Variable" => "X_$(i-1)", "Value" => value(X[i])))
        end
        for s_idx in 1:s_count
            scenario_name = string(get(_as_dict(scenarios[s_idx]), "name", "scenario_$(s_idx-1)"))
            for i in 1:n
                sval = value(Shortfall[s_idx, i])
                if sval > 1e-8
                    push!(variables, Dict("Variable" => "Shortfall_$(scenario_name)_$(item_names[i])", "Value" => sval))
                end
            end
        end
    end

    constraints_data = Any[
        Dict("Constraint" => "CPU_CAP", "Shadow Price" => 0.0, "Slack" => 0.0),
        Dict("Constraint" => "RAM_CAP", "Shadow Price" => 0.0, "Slack" => 0.0),
    ]
    for s_idx in 1:s_count
        for i in 1:n
            cname = "DEMAND_$(s_idx-1)_$(i-1)"
            push!(constraints_data, Dict("Constraint" => cname, "Shadow Price" => 0.0, "Slack" => 0.0))
        end
    end

    return Dict{String, Any}(
        "status" => status,
        "objective" => objective_val,
        "variables" => variables,
        "constraints" => constraints_data,
        "solve_time" => time() - started,
        "lp_sensitivity" => false,
        "details" => Dict(
            "engine" => "ST",
            "message" => "Scenario-based stochastic model solved",
            "scenario_count" => s_count,
            "hotspot_count" => length(get(ga, "hotspots", Any[])),
        ),
    )
end
