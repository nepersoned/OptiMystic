using JuMP
using HiGHS
import MathOptInterface as MOI

function _status_from_model(model::Model)
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

function _build_mip_model(ir::Dict{String, Any};
    sense::String="minimize",
    warm_start::Dict{String, Float64}=Dict{String, Float64}(),
    fixed_values::Dict{String, Float64}=Dict{String, Float64}(),
    time_limit_seconds::Float64=10.0,
)
    model = Model(HiGHS.Optimizer)
    set_silent(model)
    try
        set_attribute(model, "time_limit", max(1.0, time_limit_seconds))
    catch err
        @warn "Failed to set MIP time_limit" value=max(1.0, time_limit_seconds) error=err
    end
    try
        set_attribute(model, "output_flag", false)
    catch err
        @warn "Failed to set MIP output_flag" error=err
    end

    vars = Dict{String, VariableRef}()
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
        if vtype == "Binary"
            set_binary(v)
            set_lower_bound(v, 0.0)
            set_upper_bound(v, 1.0)
        elseif vtype == "Integer"
            set_integer(v)
            set_lower_bound(v, lb)
            if ub_raw !== nothing
                set_upper_bound(v, _to_float(ub_raw, lb))
            end
        else
            set_lower_bound(v, lb)
            if ub_raw !== nothing
                set_upper_bound(v, _to_float(ub_raw, lb))
            end
        end

        if haskey(warm_start, name)
            try
                set_start_value(v, warm_start[name])
            catch err
                @warn "Failed to set start value" variable=name value=warm_start[name] error=err
            end
        end

        if haskey(fixed_values, name)
            try
                fix(v, fixed_values[name]; force=true)
            catch err
                @warn "Failed to fix variable" variable=name value=fixed_values[name] error=err
            end
        end

        vars[name] = v
    end

    objective_terms = _as_vector(get(ir, "objective", Any[]))
    obj_expr = AffExpr(0.0)
    for raw_term in objective_terms
        term = _as_dict(raw_term)
        var_name = string(get(term, "var", ""))
        if !haskey(vars, var_name)
            continue
        end
        coef = _to_float(get(term, "coef", 0.0), 0.0)
        add_to_expression!(obj_expr, coef, vars[var_name])
    end

    if sense == "maximize"
        @objective(model, Max, obj_expr)
    else
        @objective(model, Min, obj_expr)
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

        expr = AffExpr(0.0)
        terms = _as_vector(get(c, "terms", Any[]))
        for raw_term in terms
            t = _as_dict(raw_term)
            var_name = string(get(t, "var", ""))
            if !haskey(vars, var_name)
                continue
            end
            coef = _to_float(get(t, "coef", 0.0), 0.0)
            add_to_expression!(expr, coef, vars[var_name])
        end

        rhs = _to_float(get(c, "rhs", 0.0), 0.0)
        rel = string(get(c, "sense", "<="))
        if rel == ">="
            @constraint(model, expr >= rhs)
        elseif rel == "==" || rel == "="
            @constraint(model, expr == rhs)
        else
            @constraint(model, expr <= rhs)
        end
    end

    return model, vars, order
end

function solve_mip_from_ir(ir::Dict{String, Any}, sense::String;
    warm_start::Dict{String, Float64}=Dict{String, Float64}(),
    fixed_values::Dict{String, Float64}=Dict{String, Float64}(),
    time_limit_seconds::Float64=10.0,
)
    started = time()
    model, vars, order = _build_mip_model(
        ir;
        sense=sense,
        warm_start=warm_start,
        fixed_values=fixed_values,
        time_limit_seconds=time_limit_seconds,
    )

    optimize!(model)

    status = _status_from_model(model)
    objective = nothing
    if primal_status(model) == MOI.FEASIBLE_POINT
        objective = objective_value(model)
    end

    variables = Vector{Any}()
    if primal_status(model) == MOI.FEASIBLE_POINT
        for name in order
            if !haskey(vars, name)
                continue
            end
            push!(variables, Dict("Variable" => name, "Value" => value(vars[name])))
        end
    end

    return Dict{String, Any}(
        "status" => status,
        "objective" => objective,
        "variables" => variables,
        "constraints" => Any[],
        "solve_time" => time() - started,
        "lp_sensitivity" => false,
    )
end
