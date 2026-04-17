using JSON3

function _parse_cli_args(args::Vector{String})
    parsed = Dict{String, String}()
    i = 1
    while i <= length(args)
        token = args[i]
        if startswith(token, "--") && i < length(args)
            parsed[token[3:end]] = args[i + 1]
            i += 2
        else
            i += 1
        end
    end
    return parsed
end

function _safe_json_parse(raw::String)
    # Primary path: strict JSON.
    try
        return JSON3.read(raw, Dict{String, Any})
    catch
    end

    # PowerShell frequently passes escaped JSON for --params.
    candidates = String[]
    push!(candidates, raw)
    push!(candidates, replace(raw, "\\\"" => "\""))

    stripped = strip(raw)
    if length(stripped) >= 2
        if (startswith(stripped, "\"") && endswith(stripped, "\"")) ||
           (startswith(stripped, "'") && endswith(stripped, "'"))
            inner = stripped[2:end-1]
            push!(candidates, inner)
            push!(candidates, replace(inner, "\\\"" => "\""))
        end
    end

    for candidate in candidates
        try
            return JSON3.read(candidate, Dict{String, Any})
        catch
        end
    end

    error("invalid JSON for --params. Pass a valid JSON object string.")
end

function _json_out(payload::Dict{String, Any})
    println(JSON3.write(payload))
end
