using Random

const _GA_LIB_TRIED = Ref(false)
const _GA_LIB_MODULE = Ref{Any}(nothing)
const _GA_UNIFORMBIN_TRIED = Ref(false)
const _GA_UNIFORMBIN_FN = Ref{Any}(nothing)

function _bool_from_any(value::Any, default::Bool=false)
    if value isa Bool
        return value
    end
    s = lowercase(strip(string(value)))
    if s in ("1", "true", "yes", "y", "on")
        return true
    end
    if s in ("0", "false", "no", "n", "off")
        return false
    end
    return default
end

function _get_ga_library_module()
    if _GA_LIB_TRIED[]
        return _GA_LIB_MODULE[]
    end

    _GA_LIB_TRIED[] = true
    try
        @eval import Evolutionary
        _GA_LIB_MODULE[] = Evolutionary
    catch
        _GA_LIB_MODULE[] = nothing
    end
    return _GA_LIB_MODULE[]
end

function _get_uniformbin_fn()
    if _GA_UNIFORMBIN_TRIED[]
        return _GA_UNIFORMBIN_FN[]
    end
    _GA_UNIFORMBIN_TRIED[] = true

    lib = _get_ga_library_module()
    if lib !== nothing && hasproperty(lib, :uniformbin)
        _GA_UNIFORMBIN_FN[] = getproperty(lib, :uniformbin)
    else
        _GA_UNIFORMBIN_FN[] = nothing
    end
    return _GA_UNIFORMBIN_FN[]
end

function _random_value_for_var(var_def::Dict{String, Any})
    vtype = string(get(var_def, "type", "Continuous"))
    lb = _to_float(get(var_def, "lb", 0.0), 0.0)
    ub = haskey(var_def, "ub") ? _to_float(get(var_def, "ub", lb + 10.0), lb + 10.0) : (lb + 10.0)

    if vtype == "Binary"
        return rand(Bool) ? 1.0 : 0.0
    elseif vtype == "Integer"
        lo = Int(floor(lb))
        hi = Int(ceil(ub))
        if hi < lo
            hi = lo
        end
        return Float64(rand(lo:hi))
    else
        return lb + rand() * max(0.0, ub - lb)
    end
end

function _repair_candidate!(candidate::Dict{String, Float64}, vars::Vector{Dict{String, Any}}, ir::Dict{String, Any})
    # Keep values in domain bounds and satisfy simple fixed constraints exactly.
    for v in vars
        vn = string(get(v, "name", ""))
        if isempty(vn)
            continue
        end
        if !haskey(candidate, vn)
            candidate[vn] = _random_value_for_var(v)
        end
        val = get(candidate, vn, 0.0)
        lb = _to_float(get(v, "lb", 0.0), 0.0)
        ub = haskey(v, "ub") ? _to_float(get(v, "ub", lb), lb) : Inf
        val = max(lb, min(ub, val))

        vtype = string(get(v, "type", "Continuous"))
        if vtype == "Binary"
            val = val >= 0.5 ? 1.0 : 0.0
        elseif vtype == "Integer"
            val = round(val)
        end
        candidate[vn] = val
    end

    for raw_constraint in _as_vector(get(ir, "constraints", Any[]))
        c = _as_dict(raw_constraint)
        if lowercase(string(get(c, "type", "linear"))) != "fix"
            continue
        end
        vn = string(get(c, "var", ""))
        if isempty(vn)
            continue
        end
        candidate[vn] = _to_float(get(c, "value", 0.0), 0.0)
    end
    return candidate
end

function _mutate_value(current::Float64, var_def::Dict{String, Any})
    vtype = string(get(var_def, "type", "Continuous"))
    lb = _to_float(get(var_def, "lb", 0.0), 0.0)
    ub = haskey(var_def, "ub") ? _to_float(get(var_def, "ub", lb), lb) : (lb + 10.0)
    if ub < lb
        ub = lb
    end

    if vtype == "Binary"
        return current >= 0.5 ? 0.0 : 1.0
    elseif vtype == "Integer"
        step = rand((-1, 1)) * max(1.0, round((ub - lb) / 10))
        return max(lb, min(ub, round(current + step)))
    else
        delta = (rand() - 0.5) * max(1e-6, (ub - lb) * 0.2)
        return max(lb, min(ub, current + delta))
    end
end

function _crossover(parent_a::Dict{String, Float64}, parent_b::Dict{String, Float64}, var_names::Vector{String})
    child = Dict{String, Float64}()
    for vn in var_names
        if rand() < 0.5
            child[vn] = get(parent_a, vn, get(parent_b, vn, 0.0))
        else
            child[vn] = get(parent_b, vn, get(parent_a, vn, 0.0))
        end
    end
    return child
end

function _crossover_with_library(parent_a::Dict{String, Float64}, parent_b::Dict{String, Float64}, var_names::Vector{String})
    uniformbin_fn = _get_uniformbin_fn()
    if uniformbin_fn === nothing
        return _crossover(parent_a, parent_b, var_names)
    end

    a = [get(parent_a, vn, 0.0) for vn in var_names]
    b = [get(parent_b, vn, 0.0) for vn in var_names]

    child_vec = nothing
    try
        # Phase-1 integration: use an external crossover operator when available.
        child_vec = uniformbin_fn(a, b)
    catch
        child_vec = nothing
    end

    if !(child_vec isa AbstractVector) || length(child_vec) != length(var_names)
        return _crossover(parent_a, parent_b, var_names)
    end

    child = Dict{String, Float64}()
    for i in 1:length(var_names)
        child[var_names[i]] = _to_float(child_vec[i], get(a, i, 0.0))
    end
    return child
end

function _make_initial_population(vars::Vector{Dict{String, Any}}, population::Int)
    population_size = max(1, population)
    result = Vector{Dict{String, Float64}}(undef, population_size)
    for idx in 1:population_size
        cand = Dict{String, Float64}()
        for v in vars
            vn = string(get(v, "name", ""))
            if isempty(vn)
                continue
            end
            cand[vn] = _random_value_for_var(v)
        end
        result[idx] = cand
    end
    return result
end

function _ga_options(params::Dict{String, Any})
    ga_cfg = _as_dict(get(params, "GA", Dict{String, Any}()))
    return Dict{String, Any}(
        "population" => max(12, _to_int(get(ga_cfg, "population", 48), 48)),
        "generations" => max(4, _to_int(get(ga_cfg, "generations", 30), 30)),
        "elite_k" => max(2, _to_int(get(ga_cfg, "elite_k", 8), 8)),
        "hotspot_threshold" => max(0.5, min(0.99, _to_float(get(ga_cfg, "hotspot_threshold", 0.85), 0.85))),
        "mutation_rate" => max(0.01, min(0.8, _to_float(get(ga_cfg, "mutation_rate", 0.15), 0.15))),
        "seed" => _to_int(get(ga_cfg, "seed", 0), 0),
        "library_ops" => _bool_from_any(get(ga_cfg, "library_ops", false), false),
    )
end

function _eval_candidate(ir::Dict{String, Any}, candidate::Dict{String, Float64}, sense::String)
    obj = 0.0
    for raw_term in _as_vector(get(ir, "objective", Any[]))
        term = _as_dict(raw_term)
        var_name = string(get(term, "var", ""))
        obj += _to_float(get(term, "coef", 0.0), 0.0) * get(candidate, var_name, 0.0)
    end

    penalty = 0.0
    for raw_constraint in _as_vector(get(ir, "constraints", Any[]))
        c = _as_dict(raw_constraint)
        ctype = lowercase(string(get(c, "type", "linear")))
        if ctype == "fix"
            vn = string(get(c, "var", ""))
            target = _to_float(get(c, "value", 0.0), 0.0)
            penalty += abs(get(candidate, vn, 0.0) - target) * 10000.0
            continue
        end

        lhs = 0.0
        for raw_term in _as_vector(get(c, "terms", Any[]))
            t = _as_dict(raw_term)
            vn = string(get(t, "var", ""))
            lhs += _to_float(get(t, "coef", 0.0), 0.0) * get(candidate, vn, 0.0)
        end

        rhs = _to_float(get(c, "rhs", 0.0), 0.0)
        rel = string(get(c, "sense", "<="))
        if rel == "<="
            penalty += max(0.0, lhs - rhs) * 10000.0
        elseif rel == ">="
            penalty += max(0.0, rhs - lhs) * 10000.0
        else
            penalty += abs(lhs - rhs) * 10000.0
        end
    end

    score = sense == "maximize" ? (obj - penalty) : (-obj - penalty)
    return score, obj
end

function solve_ga_hotspots(ir::Dict{String, Any}, sense::String;
    population::Int=48,
    generations::Int=30,
    elite_k::Int=8,
    hotspot_threshold::Float64=0.85,
    mutation_rate::Float64=0.15,
    library_ops::Bool=false,
)
    started = time()
    if population <= 0
        population = 48
    end
    if generations <= 0
        generations = 30
    end
    if elite_k <= 0
        elite_k = 8
    end
    mutation_rate = max(0.01, min(0.8, mutation_rate))

    vars = [_as_dict(v) for v in _as_vector(get(ir, "variables", Any[]))]
    var_names = [string(get(v, "name", "")) for v in vars if !isempty(string(get(v, "name", "")))]
    var_map = Dict{String, Dict{String, Any}}(string(get(v, "name", "")) => v for v in vars if !isempty(string(get(v, "name", ""))))

    if isempty(var_names)
        return Dict{String, Any}(
            "status" => "Unknown",
            "objective" => nothing,
            "hotspots" => Any[],
            "start_values" => Dict{String, Float64}(),
            "fixed_values" => Dict{String, Float64}(),
            "variables" => Any[],
            "constraints" => Any[],
            "solve_time" => time() - started,
            "lp_sensitivity" => false,
        )
    end

    best_candidate = Dict{String, Float64}()
    best_score = -Inf
    best_obj = 0.0
    elites = Vector{Dict{String, Float64}}(undef, 0)

    pool_candidates = _make_initial_population(vars, population)

    for _ in 1:generations
        pool = Vector{Tuple{Float64, Float64, Dict{String, Float64}}}(undef, length(pool_candidates))
        for idx in eachindex(pool_candidates)
            cand = _repair_candidate!(pool_candidates[idx], vars, ir)
            score, obj = _eval_candidate(ir, cand, sense)
            pool[idx] = (score, obj, cand)
        end

        sort!(pool, by=x -> x[1], rev=true)
        take_n = min(elite_k, length(pool))
        elites = Vector{Dict{String, Float64}}(undef, take_n)
        for i in 1:take_n
            elites[i] = pool[i][3]
        end

        if !isempty(pool) && pool[1][1] > best_score
            best_score = pool[1][1]
            best_obj = pool[1][2]
            best_candidate = copy(pool[1][3])
        end

        next_population = Vector{Dict{String, Float64}}(undef, population)
        for i in 1:take_n
            next_population[i] = copy(elites[i])
        end
        idx = take_n + 1
        while idx <= population
            p1 = elites[rand(1:length(elites))]
            p2 = elites[rand(1:length(elites))]
            child = library_ops ? _crossover_with_library(p1, p2, var_names) : _crossover(p1, p2, var_names)
            for vn in var_names
                if rand() < mutation_rate
                    child[vn] = _mutate_value(get(child, vn, 0.0), get(var_map, vn, Dict{String, Any}()))
                end
            end
            next_population[idx] = child
            idx += 1
        end
        pool_candidates = next_population
    end

    hotspots = String[]
    if !isempty(elites)
        for vn in var_names
            vals = [round(get(e, vn, 0.0), digits=6) for e in elites]
            if isempty(vals)
                continue
            end
            mode_val = vals[1]
            mode_count = count(x -> x == mode_val, vals)
            ratio = mode_count / length(vals)
            if ratio >= hotspot_threshold
                push!(hotspots, vn)
            end
        end
    end

    fixed_values = Dict{String, Float64}()
    for vn in hotspots
        fixed_values[vn] = get(best_candidate, vn, 0.0)
        if length(fixed_values) >= 25
            break
        end
    end

    return Dict{String, Any}(
        "status" => "Feasible",
        "objective" => best_obj,
        "hotspots" => hotspots,
        "start_values" => best_candidate,
        "fixed_values" => fixed_values,
        "variables" => [Dict("Variable" => k, "Value" => v) for (k, v) in best_candidate],
        "constraints" => Any[],
        "solve_time" => time() - started,
        "lp_sensitivity" => false,
    )
end

function solve_ga_only(payload::Dict{String, Any})
    params = _as_dict(get(payload, "params", Dict{String, Any}()))
    ir = _extract_ir(params)
    sense = _normalize_sense(get(params, "Sense", "maximize"))
    opts = _ga_options(params)
    seed = _to_int(get(opts, "seed", 0), 0)
    if seed != 0
        Random.seed!(seed)
    end
    return solve_ga_hotspots(
        ir,
        sense;
        population=_to_int(get(opts, "population", 48), 48),
        generations=_to_int(get(opts, "generations", 30), 30),
        elite_k=_to_int(get(opts, "elite_k", 8), 8),
        hotspot_threshold=_to_float(get(opts, "hotspot_threshold", 0.85), 0.85),
        mutation_rate=_to_float(get(opts, "mutation_rate", 0.15), 0.15),
        library_ops=_bool_from_any(get(opts, "library_ops", false), false),
    )
end
