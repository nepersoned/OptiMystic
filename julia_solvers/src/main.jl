module OptiMysticSolver

export run_main, route_solver

include("utils/io_contract.jl")
include("utils/ir_tools.jl")
include("solvers/mip.jl")
include("solvers/ga.jl")
include("solvers/cg.jl")
include("solvers/st.jl")
include("solvers/nlp.jl")
include("solvers/router.jl")

function run_main()
    started = time()
    try
        parsed = _parse_cli_args(ARGS)
        domain = lowercase(string(get(parsed, "domain", "generic")))
        solver = lowercase(string(get(parsed, "solver", "mip")))
        params_raw = get(parsed, "params", "{}")

        params = _safe_json_parse(params_raw)
        if !(params isa Dict)
            params = Dict{String, Any}()
        end

        payload = Dict{String, Any}(
            "domain" => domain,
            "solver" => solver,
            "params" => params,
        )

        result = route_solver(payload)
        result["solve_time"] = get(result, "solve_time", time() - started)
        result["details"] = get(result, "details", Dict{String, Any}())
        result["sensitivity"] = get(result, "sensitivity", Dict{String, Any}())

        _json_out(result)
    catch err
        stacktrace_str = sprint(showerror, err, catch_backtrace())
        _json_out(Dict{String, Any}(
            "status" => "Error",
            "error_msg" => string(err),
            "error_trace" => stacktrace_str,
            "objective" => nothing,
            "variables" => Any[],
            "constraints" => Any[],
            "solve_time" => time() - started,
            "lp_sensitivity" => false,
            "details" => Dict{String, Any}(),
            "sensitivity" => Dict{String, Any}(),
        ))
    end
end

end # module OptiMysticSolver

using .OptiMysticSolver: run_main, route_solver
