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
    return JSON3.read(raw, Dict{String, Any})
end

function _json_out(payload::Dict{String, Any})
    println(JSON3.write(payload))
end
