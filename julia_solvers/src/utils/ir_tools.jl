function _normalize_sense(value::Any)
    sense = lowercase(string(value))
    return sense == "maximize" ? "maximize" : "minimize"
end

function _to_float(value::Any, default::Float64=0.0)
    try
        return Float64(value)
    catch
        return default
    end
end

function _to_int(value::Any, default::Int=0)
    try
        return Int(round(Float64(value)))
    catch
        return default
    end
end

function _as_vector(value::Any)
    return value isa Vector ? value : Any[]
end

function _as_dict(value::Any)
    return value isa Dict ? value : Dict{String, Any}()
end

function _extract_ir(params::Dict{String, Any})
    ir = get(params, "IR", Dict{String, Any}())
    return _as_dict(ir)
end
