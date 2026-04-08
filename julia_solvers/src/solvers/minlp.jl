using JuMP
using Ipopt
using HiGHS
using Juniper
using Random
import MathOptInterface as MOI

function _status_from_minlp(model::Model)
    ts = termination_status(model)
    ps = primal_status(model)
    if ts == MOI.OPTIMAL
        return "Optimal"
    end
    if ps == MOI.FEASIBLE_POINT
        return "Feasible"
    end
    if ts == MOI.INFEASIBLE
        return "Infeasible"
    end
    if ts == MOI.INVALID_MODEL
        return "ModelInvalid"
    end
    if ts == MOI.TIME_LIMIT && ps == MOI.FEASIBLE_POINT
        return "Feasible"
    end
    return "Unknown"
end

function _minlp_options(params::Dict{String, Any})
    cfg = _as_dict(get(params, "MINLP", Dict{String, Any}()))
    ga_cfg = _as_dict(get(params, "GA", Dict{String, Any}()))
    merged = Dict{String, Any}(ga_cfg)
    for (k, v) in cfg
        merged[string(k)] = v
    end
    if !haskey(merged, "population")
        merged["population"] = 48
    end
    if !haskey(merged, "generations")
        merged["generations"] = 30
    end
    if !haskey(merged, "elite_k")
        merged["elite_k"] = 8
    end
    if !haskey(merged, "hotspot_threshold")
        merged["hotspot_threshold"] = 0.9
    end
    if !haskey(merged, "mutation_rate")
        merged["mutation_rate"] = 0.15
    end
    if !haskey(merged, "library_ops")
        merged["library_ops"] = false
    end
    if !haskey(merged, "seed")
        merged["seed"] = 0
    end
    if !haskey(merged, "time_limit_seconds")
        merged["time_limit_seconds"] = get(params, "TimeLimit", get(params, "time_limit", 20))
    end
    if !haskey(merged, "variable_threshold")
        merged["variable_threshold"] = 10000
    end
    return merged
end

function _minlp_spec(params::Dict{String, Any})
    return _as_dict(get(params, "MINLP", get(params, "NLP", Dict{String, Any}())))
end

function _build_minlp_model(ir::Dict{String, Any}, minlp_spec::Dict{String, Any};
    sense::String="minimize",
    warm_start::Dict{String, Float64}=Dict{String, Float64}(),
    time_limit_seconds::Float64=20.0,
)
    model = Model(Juniper.Optimizer)
    set_silent(model)
    try
        set_optimizer_attribute(model, "nl_solver", Ipopt.Optimizer)
    catch err
        @warn "Failed to set MINLP nl_solver" error=err
    end
    try
        set_optimizer_attribute(model, "mip_solver", HiGHS.Optimizer)
    catch err
        @warn "Failed to set MINLP mip_solver" error=err
    end
    try
        set_optimizer_attribute(model, "time_limit", max(1.0, time_limit_seconds))
    catch err
        @warn "Failed to set MINLP time_limit" error=err
    end
    vars = Dict{String, VariableRef}()
    aliases = Dict{String, Symbol}()
    order = String[]
    variables = _as_vector(get(ir, "variables", Any[]))

    for raw_var in variables
        var_def = _as_dict(raw_var)
        name = string(get(var_def, "name", ""))
        if isempty(name)
            continue
        end
        push!(order, name)
        vtype = string(get(var_def, "type", "Continuous"))
        lb = _to_float(get(var_def, "lb", 0.0), 0.0)
        ub_raw = get(var_def, "ub", nothing)

        v = @variable(model, base_name=name)
        set_lower_bound(v, lb)
        if ub_raw !== nothing
            set_upper_bound(v, _to_float(ub_raw, lb))
        end
        if vtype == "Binary"
            set_binary(v)
            set_lower_bound(v, 0.0)
            set_upper_bound(v, 1.0)
        elseif vtype == "Integer"
            set_integer(v)
        end

        if haskey(warm_start, name)
            try
                set_start_value(v, warm_start[name])
            catch err
                @warn "Failed to set MINLP warm-start value" variable=name value=warm_start[name] error=err
            end
        end

        vars[name] = v
        alias = _safe_symbol(name)
        aliases[name] = alias
        try
            @eval $(alias) = $v
        catch err
            @warn "Failed to bind MINLP alias" variable=name alias=String(alias) error=err
        end
    end

    objective_terms = _as_vector(get(ir, "objective", Any[]))
    linear_objective = 0.0
    for raw_term in objective_terms
        term = _as_dict(raw_term)
        var_name = string(get(term, "var", ""))
        if !haskey(vars, var_name)
            continue
        end
        coef = _to_float(get(term, "coef", 0.0), 0.0)
        if linear_objective == 0.0
            linear_objective = :($coef * $(aliases[var_name]))
        else
            linear_objective = :($linear_objective + $coef * $(aliases[var_name]))
        end
    end

    nonlinear_objective = get(minlp_spec, "objective_expr", get(minlp_spec, "objective", nothing))
    has_nonlinear_objective = nonlinear_objective !== nothing && _is_nonlinear_node(nonlinear_objective)
    if has_nonlinear_objective
        combined_objective = _nl_ast_to_expr(nonlinear_objective, aliases)
        if linear_objective != 0.0
            combined_objective = :($combined_objective + $linear_objective)
        end
        if sense == "maximize"
            @eval JuMP.@NLobjective($model, Max, $(combined_objective))
        else
            @eval JuMP.@NLobjective($model, Min, $(combined_objective))
        end
    else
        if linear_objective == 0.0
            linear_objective = 0.0
        end
        if sense == "maximize"
            @eval JuMP.@objective($model, Max, $(linear_objective))
        else
            @eval JuMP.@objective($model, Min, $(linear_objective))
        end
    end

    constraints = _as_vector(get(ir, "constraints", Any[]))
    for raw_constraint in constraints
        c = _as_dict(raw_constraint)
        ctype = lowercase(string(get(c, "type", "linear")))
        if ctype == "fix"
            var_name = string(get(c, "var", ""))
            if haskey(vars, var_name)
                val = _to_float(get(c, "value", 0.0), 0.0)
                @constraint(model, vars[var_name] == val)
            end
            continue
        end

        rhs = _to_float(get(c, "rhs", 0.0), 0.0)
        rel = string(get(c, "sense", "<="))
        nonlinear_expr = haskey(c, "expr") || haskey(c, "lhs")
        if nonlinear_expr
            expr_source = get(c, "expr", get(c, "lhs", nothing))
            nl_expr = _nl_ast_to_expr(expr_source, aliases)
            if rel == ">="
                @eval JuMP.@NLconstraint($model, $(nl_expr) >= $rhs)
            elseif rel == "==" || rel == "="
                @eval JuMP.@NLconstraint($model, $(nl_expr) == $rhs)
            else
                @eval JuMP.@NLconstraint($model, $(nl_expr) <= $rhs)
            end
        else
            expr = 0.0
            terms = _as_vector(get(c, "terms", Any[]))
            for raw_term in terms
                term = _as_dict(raw_term)
                var_name = string(get(term, "var", ""))
                if !haskey(vars, var_name)
                    continue
                end
                coef = _to_float(get(term, "coef", 0.0), 0.0)
                if expr == 0.0
                    expr = :($coef * $(aliases[var_name]))
                else
                    expr = :($expr + $coef * $(aliases[var_name]))
                end
            end
            if rel == ">="
                @eval JuMP.@constraint($model, $(expr) >= $rhs)
            elseif rel == "==" || rel == "="
                @eval JuMP.@constraint($model, $(expr) == $rhs)
            else
                @eval JuMP.@constraint($model, $(expr) <= $rhs)
            end
        end
    end

    return model, vars, order
end

function solve_minlp(payload::Dict{String, Any})
    started = time()
    params = _as_dict(get(payload, "params", Dict{String, Any}()))
    ir = _extract_ir(params)
    sense = _normalize_sense(get(params, "Sense", "minimize"))
    opts = _minlp_options(params)
    minlp_spec = _minlp_spec(params)

    variable_count = length(_as_vector(get(ir, "variables", Any[])))
    ga_variable_threshold = max(0, _to_int(get(opts, "variable_threshold", 10000), 10000))
    use_ga = variable_count > ga_variable_threshold

    ga_result = Dict{String, Any}(
        "status" => "Skipped",
        "hotspots" => Any[],
        "start_values" => Dict{String, Float64}(),
        "fixed_values" => Dict{String, Float64}(),
    )
    warm_start = Dict{String, Float64}()
    if use_ga
        ga_result, warm_start = _solve_nlp_ga_guidance(ir, sense, opts)
    end

    time_limit_seconds = _to_float(get(opts, "time_limit_seconds", 20), 20.0)
    model, vars, order = _build_minlp_model(
        ir,
        minlp_spec,
        sense=sense,
        warm_start=warm_start,
        time_limit_seconds=time_limit_seconds,
    )

    optimize!(model)

    status = _status_from_minlp(model)
    objective = nothing
    if primal_status(model) == MOI.FEASIBLE_POINT
        objective = objective_value(model)
    end

    variables_out = Vector{Any}()
    if primal_status(model) == MOI.FEASIBLE_POINT
        for name in order
            if !haskey(vars, name)
                continue
            end
            push!(variables_out, Dict("Variable" => name, "Value" => value(vars[name])))
        end
    end

    ga_hotspots = get(ga_result, "hotspots", Any[])
    nonlinear_terms = 0
    if get(minlp_spec, "objective_expr", get(minlp_spec, "objective", nothing)) !== nothing
        nonlinear_terms += 1
    end
    for raw_constraint in _as_vector(get(minlp_spec, "constraints", Any[]))
        c = _as_dict(raw_constraint)
        if haskey(c, "expr") || haskey(c, "lhs")
            nonlinear_terms += 1
        end
    end

    discrete_count = 0
    for raw_var in _as_vector(get(ir, "variables", Any[]))
        v = _as_dict(raw_var)
        vtype = lowercase(string(get(v, "type", "Continuous")))
        if vtype in ("binary", "integer")
            discrete_count += 1
        end
    end

    return Dict{String, Any}(
        "status" => status,
        "objective" => objective,
        "variables" => variables_out,
        "constraints" => Any[],
        "solve_time" => time() - started,
        "lp_sensitivity" => false,
        "details" => Dict(
            "engine" => "MINLP",
            "solver" => "Juniper+Ipopt+HiGHS",
            "message" => use_ga ? "MINLP solved with GA-guided warm start" : "MINLP solved directly (GA skipped by variable threshold)",
            "ga_hotspot_count" => length(ga_hotspots),
            "ga_used" => use_ga,
            "variable_count" => variable_count,
            "discrete_variable_count" => discrete_count,
            "ga_variable_threshold" => ga_variable_threshold,
            "nonlinear_term_count" => nonlinear_terms,
        ),
    )
end
