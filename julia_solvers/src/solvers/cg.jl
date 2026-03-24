using Random
using JuMP
using HiGHS

function _cg_build_master_model(patterns::Vector{Vector{Int}}, demands::Vector{Float64}, stock_cost::Float64)
    m = Model(HiGHS.Optimizer)
    set_silent(m)
    try
        set_attribute(m, "output_flag", false)
    catch err
        @warn "Failed to set CG master output_flag" error=err
    end

    θ = VariableRef[]
    p_count = length(patterns)
    n = length(demands)
    for p in 1:p_count
        v = @variable(m, lower_bound=0.0, base_name="theta_$(p)")
        push!(θ, v)
    end

    demand_cons = Vector{ConstraintRef}(undef, n)
    for i in 1:n
        demand_cons[i] = @constraint(m, sum(patterns[p][i] * θ[p] for p in 1:p_count) >= demands[i])
    end
    @objective(m, Min, stock_cost * sum(v for v in θ))
    return m, θ, demand_cons
end

function _cg_add_pattern!(m::Model, θ::Vector{VariableRef}, demand_cons::Vector{ConstraintRef}, pattern::Vector{Int}, stock_cost::Float64)
    new_idx = length(θ) + 1
    new_var = @variable(m, lower_bound=0.0, base_name="theta_$(new_idx)")
    push!(θ, new_var)
    for i in eachindex(demand_cons)
        set_normalized_coefficient(demand_cons[i], new_var, pattern[i])
    end
    set_objective_coefficient(m, new_var, stock_cost)
    return nothing
end

function _cg_build_pricing_model(item_lens::Vector{Float64}, kerf::Float64, stock_len::Float64)
    n = length(item_lens)
    m = Model(HiGHS.Optimizer)
    set_silent(m)
    try
        set_attribute(m, "output_flag", false)
    catch err
        @warn "Failed to set CG pricing output_flag" error=err
    end

    @variable(m, a[1:n] >= 0, Int)
    @constraint(m, sum((item_lens[i] + kerf) * a[i] for i in 1:n) <= stock_len + kerf)
    @objective(m, Max, 0.0)
    return m, a
end

function _cg_pricing_knapsack!(m::Model, a, duals::Vector{Float64})
    n = length(duals)
    for i in 1:n
        set_objective_coefficient(m, a[i], duals[i])
    end

    optimize!(m)
    feasible = primal_status(m) == MOI.FEASIBLE_POINT
    if !feasible
        return 0.0, [0 for _ in 1:n]
    end
    pattern = [Int(round(value(a[i]))) for i in 1:n]
    return objective_value(m), pattern
end

function _cg_initial_patterns(item_lens::Vector{Float64}, kerf::Float64, stock_len::Float64)
    patterns = Vector{Vector{Int}}()
    n = length(item_lens)
    for i in 1:n
        p = [0 for _ in 1:n]
        capacity = stock_len + kerf
        unit = item_lens[i] + kerf
        if unit <= 0
            continue
        end
        p[i] = max(1, Int(floor(capacity / unit)))
        push!(patterns, p)
    end
    return patterns
end

function _solve_cg_cutting(params::Dict{String, Any}, opts::Dict{String, Any})
    started = time()
    items = [string(x) for x in _as_vector(get(params, "Items", Any[]))]
    if isempty(items)
        return Dict{String, Any}("status" => "Error", "error_msg" => "CG requires Items", "solve_time" => time() - started)
    end

    lens_raw = _as_vector(get(params, "ItemLens", get(params, "Weights", Any[])))
    item_lens = [_to_float(i <= length(lens_raw) ? lens_raw[i] : 0.0, 0.0) for i in 1:length(items)]
    if any(x -> x <= 0.0, item_lens)
        return Dict{String, Any}("status" => "Error", "error_msg" => "CG requires positive item lengths", "solve_time" => time() - started)
    end

    demands_map = _as_dict(get(params, "Demands", Dict{String, Any}()))
    demands = [_to_float(get(demands_map, items[i], 0.0), 0.0) for i in 1:length(items)]
    kerf = max(0.0, _to_float(get(params, "Kerf", 0.0), 0.0))

    stocks = _as_vector(get(params, "Stocks", Any[]))
    if isempty(stocks)
        return Dict{String, Any}("status" => "Error", "error_msg" => "CG requires Stocks", "solve_time" => time() - started)
    end
    stock = _as_dict(stocks[1])
    for s in stocks
        sdict = _as_dict(s)
        if _to_float(get(sdict, "Length", 0.0), 0.0) > _to_float(get(stock, "Length", 0.0), 0.0)
            stock = sdict
        end
    end
    stock_len = _to_float(get(stock, "Length", 0.0), 0.0)
    stock_cost = _to_float(get(stock, "Cost", 1.0), 1.0)
    if stock_len <= 0
        return Dict{String, Any}("status" => "Error", "error_msg" => "CG requires positive stock length", "solve_time" => time() - started)
    end

    patterns = _cg_initial_patterns(item_lens, kerf, stock_len)
    if isempty(patterns)
        return Dict{String, Any}("status" => "Error", "error_msg" => "Failed to build initial patterns", "solve_time" => time() - started)
    end

    max_iterations = max(10, _to_int(get(_as_dict(get(opts, "CG", Dict{String, Any}())), "max_iterations", 80), 80))
    iterations = 0
    master_status = "Unknown"
    master_duals = [0.0 for _ in 1:length(items)]
    master_model, master_theta, demand_cons = _cg_build_master_model(patterns, demands, stock_cost)
    pricing_model, pricing_a = _cg_build_pricing_model(item_lens, kerf, stock_len)

    while iterations < max_iterations
        iterations += 1
        optimize!(master_model)
        master_status = _status_from_model(master_model)
        feasible_master = primal_status(master_model) == MOI.FEASIBLE_POINT
        if feasible_master
            master_duals = [dual(demand_cons[i]) for i in eachindex(demand_cons)]
        else
            master_duals = [0.0 for _ in eachindex(demand_cons)]
        end
        if master_status == "Infeasible" || master_status == "ModelInvalid"
            break
        end

        pricing_obj, new_pattern = _cg_pricing_knapsack!(pricing_model, pricing_a, master_duals)
        if pricing_obj <= stock_cost + 1e-6
            break
        end
        if any(p -> p == new_pattern, patterns)
            break
        end
        push!(patterns, new_pattern)
        _cg_add_pattern!(master_model, master_theta, demand_cons, new_pattern, stock_cost)
    end

    # Integer master problem with generated columns.
    m = Model(HiGHS.Optimizer)
    set_silent(m)
    try
        set_attribute(m, "output_flag", false)
    catch err
        @warn "Failed to set CG integer-master output_flag" error=err
    end

    p_count = length(patterns)
    n = length(items)
    @variable(m, Θ[1:p_count] >= 0, Int)
    for i in 1:n
        @constraint(m, sum(patterns[p][i] * Θ[p] for p in 1:p_count) >= demands[i])
    end
    @objective(m, Min, stock_cost * sum(Θ[p] for p in 1:p_count))
    optimize!(m)

    status = _status_from_model(m)
    feasible = primal_status(m) == MOI.FEASIBLE_POINT
    objective_val = feasible ? objective_value(m) : nothing

    variables = Vector{Any}()
    if feasible
        bin_idx = 0
        for p in 1:p_count
            count = Int(round(value(Θ[p])))
            if count <= 0
                continue
            end
            for _ in 1:count
                bin_id = "CG_$(bin_idx)"
                push!(variables, Dict("Variable" => "U_$(bin_id)", "Value" => 1.0))
                for i in 1:n
                    qty = patterns[p][i]
                    if qty > 0
                        push!(variables, Dict("Variable" => "A_IT$(i-1)_$(bin_id)", "Value" => float(qty)))
                    end
                end
                bin_idx += 1
            end
        end
    end

    constraints_data = Any[]
    for i in 1:length(master_duals)
        push!(constraints_data, Dict("Constraint" => "demand_$(i-1)", "Shadow Price" => master_duals[i], "Slack" => 0.0))
    end

    return Dict{String, Any}(
        "status" => status,
        "objective" => objective_val,
        "variables" => variables,
        "constraints" => constraints_data,
        "solve_time" => time() - started,
        "lp_sensitivity" => false,
        "details" => Dict(
            "engine" => "CG",
            "message" => "Column generation (master + pricing) solved",
            "iterations" => iterations,
            "pattern_count" => length(patterns),
        ),
    )
end

function solve_cg(payload::Dict{String, Any})
    params = _as_dict(get(payload, "params", Dict{String, Any}()))
    ir = _extract_ir(params)
    sense = _normalize_sense(get(params, "Sense", "minimize"))
    opts = _ga_options(params)

    # Prefer domain-aware CG when cutting payload is present.
    if lowercase(string(get(params, "Mode", ""))) == "cutting" && !isempty(_as_vector(get(params, "Items", Any[])))
        return _solve_cg_cutting(params, params)
    end

    seed = _to_int(get(opts, "seed", 0), 0)
    if seed != 0
        Random.seed!(seed)
    end

    ga = solve_ga_hotspots(
        ir,
        sense;
        population=_to_int(get(opts, "population", 48), 48),
        generations=_to_int(get(opts, "generations", 20), 20),
        elite_k=_to_int(get(opts, "elite_k", 6), 6),
        hotspot_threshold=_to_float(get(opts, "hotspot_threshold", 0.85), 0.85),
        mutation_rate=_to_float(get(opts, "mutation_rate", 0.15), 0.15),
        library_ops=_bool_from_any(get(opts, "library_ops", false), false),
    )
    start_values = Dict{String, Float64}()
    fixed_values = Dict{String, Float64}()

    for (k, v) in get(ga, "start_values", Dict{String, Float64}())
        start_values[string(k)] = _to_float(v, 0.0)
    end
    for (k, v) in get(ga, "fixed_values", Dict{String, Float64}())
        fixed_values[string(k)] = _to_float(v, 0.0)
    end

    mip = solve_mip_from_ir(ir, sense; warm_start=start_values, fixed_values=fixed_values)
    mip["details"] = Dict(
        "engine" => "CG",
        "message" => "CG fallback: GA hotspot + MIP refinement",
        "hotspot_count" => length(get(ga, "hotspots", Any[])),
    )
    return mip
end
