using JuMP
using Ipopt
using Random
import MathOptInterface as MOI

function _status_from_nlp(model::Model)
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

function _nlp_options(params::Dict{String, Any})
    cfg = _as_dict(get(params, "NLP", Dict{String, Any}()))
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
        merged["time_limit_seconds"] = get(params, "TimeLimit", get(params, "time_limit", 10))
    end
    return merged
end

function _nlp_spec(params::Dict{String, Any})
    return _as_dict(get(params, "NLP", Dict{String, Any}()))
end

function _safe_symbol(name::String)
    cleaned = replace(name, r"[^A-Za-z0-9_]" => "_")
    if isempty(cleaned)
        cleaned = "x"
    end
    if !occursin(r"^[A-Za-z_]", cleaned)
        cleaned = "v_" * cleaned
    end
    return Symbol(cleaned)
end

function _is_nonlinear_node(node::Any)
    if node isa Number || node isa AbstractString
        return false
    end
    if !(node isa Dict)
        return false
    end
    raw = _as_dict(node)
    if haskey(raw, "var") || haskey(raw, "const") || haskey(raw, "value")
        return false
    end
    op = lowercase(string(get(raw, "op", get(raw, "type", ""))))
    if op in ("mul", "div", "pow", "sin", "cos", "tan", "exp", "log", "sqrt", "abs", "min", "max")
        return true
    end
    args = _as_vector(get(raw, "args", get(raw, "terms", Any[])))
    return any(_is_nonlinear_node(arg) for arg in args)
end

function _nl_ast_to_expr(node::Any, alias_map::Dict{String, Symbol})
    if node isa Number
        return Float64(node)
    end
    if node isa AbstractString
        name = String(node)
        if haskey(alias_map, name)
            return alias_map[name]
        end
        try
            return parse(Float64, name)
        catch
            return _safe_symbol(name)
        end
    end
    if !(node isa Dict)
        return 0.0
    end

    raw = _as_dict(node)
    if haskey(raw, "const")
        return _to_float(get(raw, "const", 0.0), 0.0)
    end
    if haskey(raw, "value") && !haskey(raw, "op")
        return _to_float(get(raw, "value", 0.0), 0.0)
    end
    if haskey(raw, "var")
        return get(alias_map, string(get(raw, "var", "")), _safe_symbol(string(get(raw, "var", ""))))
    end

    op = lowercase(string(get(raw, "op", get(raw, "type", ""))))
    args = _as_vector(get(raw, "args", get(raw, "terms", Any[])))

    if op in ("add", "sum")
        if isempty(args)
            return 0.0
        end
        expr = _nl_ast_to_expr(args[1], alias_map)
        for idx in Iterators.drop(eachindex(args), 1)
            expr = :($expr + $(_nl_ast_to_expr(args[idx], alias_map)))
        end
        return expr
    elseif op == "sub"
        if isempty(args)
            return 0.0
        end
        expr = _nl_ast_to_expr(args[1], alias_map)
        for idx in Iterators.drop(eachindex(args), 1)
            expr = :($expr - $(_nl_ast_to_expr(args[idx], alias_map)))
        end
        return expr
    elseif op == "mul"
        if isempty(args)
            return 1.0
        end
        expr = _nl_ast_to_expr(args[1], alias_map)
        for idx in Iterators.drop(eachindex(args), 1)
            expr = :($expr * $(_nl_ast_to_expr(args[idx], alias_map)))
        end
        return expr
    elseif op == "div"
        if isempty(args)
            return 1.0
        end
        expr = _nl_ast_to_expr(args[1], alias_map)
        for idx in Iterators.drop(eachindex(args), 1)
            expr = :($expr / $(_nl_ast_to_expr(args[idx], alias_map)))
        end
        return expr
    elseif op == "pow" && length(args) >= 2
        return :($(_nl_ast_to_expr(args[1], alias_map)) ^ $(_nl_ast_to_expr(args[2], alias_map)))
    elseif op == "neg" && !isempty(args)
        return :(-$(_nl_ast_to_expr(args[1], alias_map)))
    elseif op in ("sin", "cos", "tan", "exp", "log", "sqrt", "abs") && !isempty(args)
        return Expr(:call, Symbol(op), _nl_ast_to_expr(args[1], alias_map))
    elseif op in ("min", "max") && !isempty(args)
        return Expr(:call, Symbol(op), (_nl_ast_to_expr(arg, alias_map) for arg in args)...)
    end

    return 0.0
end

function _solve_nlp_ga_guidance(ir::Dict{String, Any}, sense::String, opts::Dict{String, Any})
    seed = _to_int(get(opts, "seed", 0), 0)
    if seed != 0
        Random.seed!(seed)
    end

    ga_result = solve_ga_hotspots(
        ir,
        sense;
        population=_to_int(get(opts, "population", 48), 48),
        generations=_to_int(get(opts, "generations", 30), 30),
        elite_k=_to_int(get(opts, "elite_k", 8), 8),
        hotspot_threshold=_to_float(get(opts, "hotspot_threshold", 0.9), 0.9),
        mutation_rate=_to_float(get(opts, "mutation_rate", 0.15), 0.15),
        library_ops=_bool_from_any(get(opts, "library_ops", false), false),
    )

    warm_start = Dict{String, Float64}()
    fixed_values = Dict{String, Float64}()
    for (k, v) in get(ga_result, "start_values", Dict{String, Float64}())
        warm_start[string(k)] = _to_float(v, 0.0)
    end
    for (k, v) in get(ga_result, "fixed_values", Dict{String, Float64}())
        fixed_values[string(k)] = _to_float(v, 0.0)
    end

    return ga_result, warm_start, fixed_values
end

function _build_nlp_model(ir::Dict{String, Any}, nlp_spec::Dict{String, Any};
    sense::String="minimize",
    warm_start::Dict{String, Float64}=Dict{String, Float64}(),
    fixed_values::Dict{String, Float64}=Dict{String, Float64}(),
    time_limit_seconds::Float64=10.0,
)
    model = Model(Ipopt.Optimizer)
    set_silent(model)
    try
        set_attribute(model, "max_cpu_time", max(1.0, time_limit_seconds))
    catch err
        @warn "Failed to set NLP time limit" value=max(1.0, time_limit_seconds) error=err
    end
    try
        set_attribute(model, "print_level", 0)
    catch err
        @warn "Failed to set NLP print_level" error=err
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
            set_lower_bound(v, 0.0)
            set_upper_bound(v, 1.0)
        end

        if haskey(warm_start, name)
            try
                set_start_value(v, warm_start[name])
            catch err
                @warn "Failed to set NLP warm-start value" variable=name value=warm_start[name] error=err
            end
        end

        if haskey(fixed_values, name)
            try
                fix(v, fixed_values[name]; force=true)
            catch err
                @warn "Failed to fix NLP hotspot variable" variable=name value=fixed_values[name] error=err
            end
        end

        vars[name] = v
        alias = _safe_symbol(name)
        aliases[name] = alias
        try
            @eval $(alias) = $v
        catch err
            @warn "Failed to bind NLP alias" variable=name alias=String(alias) error=err
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

    nonlinear_objective = get(nlp_spec, "objective_expr", get(nlp_spec, "objective", nothing))
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

function solve_nlp(payload::Dict{String, Any})
    started = time()
    params = _as_dict(get(payload, "params", Dict{String, Any}()))
    ir = _extract_ir(params)
    sense = _normalize_sense(get(params, "Sense", "minimize"))
    opts = _nlp_options(params)
    nlp_spec = _nlp_spec(params)

    ga_result, warm_start, fixed_values = _solve_nlp_ga_guidance(ir, sense, opts)
    time_limit_seconds = _to_float(get(opts, "time_limit_seconds", 10), 10.0)

    model, vars, order = _build_nlp_model(
        ir,
        nlp_spec;
        sense=sense,
        warm_start=warm_start,
        fixed_values=fixed_values,
        time_limit_seconds=time_limit_seconds,
    )

    optimize!(model)

    status = _status_from_nlp(model)
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
    start_values = get(ga_result, "start_values", Dict{String, Float64}())
    fixed_values_out = get(ga_result, "fixed_values", Dict{String, Float64}())
    nonlinear_terms = 0
    if get(nlp_spec, "objective_expr", get(nlp_spec, "objective", nothing)) !== nothing
        nonlinear_terms += 1
    end
    for raw_constraint in _as_vector(get(nlp_spec, "constraints", Any[]))
        c = _as_dict(raw_constraint)
        if haskey(c, "expr") || haskey(c, "lhs")
            nonlinear_terms += 1
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
            "engine" => "NLP",
            "message" => "NLP solved with GA-guided warm start",
            "ga_hotspot_count" => length(ga_hotspots),
            "ga_fixed_count" => length(keys(fixed_values_out)),
            "ga_start_count" => length(keys(start_values)),
            "variable_count" => length(order),
            "constraint_count" => length(_as_vector(get(ir, "constraints", Any[]))),
            "nonlinear_term_count" => nonlinear_terms,
        ),
    )
end