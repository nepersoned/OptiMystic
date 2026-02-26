package solver

import (
	"encoding/json"
	"fmt"
	"os/exec"
)

// OptimizeRequest represents the incoming JSON payload
type OptimizeRequest struct {
	TemplateType string                 `json:"template_type"`
	Params       map[string]interface{} `json:"params"`
	Sense        string                 `json:"sense,omitempty"`
}

// OptimizeResponse represents the solver output parsed from Python
type OptimizeResponse struct {
	Status      string                   `json:"status"`
	Objective   float64                  `json:"objective"`
	Variables   []map[string]interface{} `json:"variables"`
	Constraints []map[string]interface{} `json:"constraints,omitempty"`
	Details     map[string]interface{}   `json:"details,omitempty"`
	Sensitivity map[string]interface{}   `json:"sensitivity,omitempty"`
	SolveTime   float64                  `json:"solve_time,omitempty"`
}

// SelectSolver determines which solver engine to use based on the request
func SelectSolver(req OptimizeRequest) (string, error) {
	// TODO: Implement dynamic solver selection logic
	return "python_solver", nil
}

// RunSolver is the main entry point that executes the selected solver
func RunSolver(req OptimizeRequest) (*OptimizeResponse, error) {
	solverName, err := SelectSolver(req)
	if err != nil {
		return nil, fmt.Errorf("solver selection failed: %w", err)
	}

	if solverName == "python_solver" {
		return runPythonSolver(req)
	}

	return nil, fmt.Errorf("unsupported solver: %s", solverName)
}

// runPythonSolver executes the CLI script and parses the stdout JSON
func runPythonSolver(req OptimizeRequest) (*OptimizeResponse, error) {
	paramsJson, err := json.Marshal(req.Params)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal params: %w", err)
	}

	cmd := exec.Command("python", "python_solvers/cli_solver.py",
		"--domain", req.TemplateType,
		"--solver", "mip", // Default to mip for now
		"--params", string(paramsJson),
	)

	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("python solver execution failed: %w", err)
	}

	var result OptimizeResponse
	if err := json.Unmarshal(output, &result); err != nil {
		return nil, fmt.Errorf("failed to parse python solver output: %w", err)
	}

	return &result, nil
}