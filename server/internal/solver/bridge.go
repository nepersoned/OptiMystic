package solver

import (
    "context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// OptimizeRequest represents the incoming JSON payload
type OptimizeRequest struct {
	TemplateType string                 `json:"template_type"`
	Params       map[string]interface{} `json:"params"`
	Sense        string                 `json:"sense,omitempty"`
	SolverType   string                 `json:"solver_type,omitempty"`
}

// OptimizeResponse represents the solver output parsed from Python
type OptimizeResponse struct {
	Status      string                   `json:"status"`
	Objective   *float64                 `json:"objective,omitempty"`
	Variables   []map[string]interface{} `json:"variables"`
	Constraints []map[string]interface{} `json:"constraints,omitempty"`
	Details     map[string]interface{}   `json:"details,omitempty"`
	Sensitivity map[string]interface{}   `json:"sensitivity,omitempty"`
	SolveTime   float64                  `json:"solve_time,omitempty"`
	Error       string                   `json:"error,omitempty"`
	ErrorMsg    string                   `json:"error_msg,omitempty"`
}

func normalizeDomain(domain string) string {
	switch strings.TrimSpace(strings.ToLower(domain)) {
	case "manufacturing":
		return "cutting"
	case "logistics":
		return "packing"
	case "vrp", "routing", "vehicle_routing":
		return "vrp"
	case "resource", "it", "cloud", "resource_allocation":
		return "resourcing"
	case "hr", "nsp":
		return "scheduling"
	case "formula", "custom":
		return "generic"
	default:
		return strings.TrimSpace(strings.ToLower(domain))
	}
}

func normalizeSolverType(solverType string) string {
	switch strings.TrimSpace(strings.ToLower(solverType)) {
	case "", "mip":
		return "mip"
	case "cg", "cp", "st", "ga", "vrp", "nlp":
		return strings.TrimSpace(strings.ToLower(solverType))
	default:
		return "mip"
	}
}

func pythonCommand() string {
	value := strings.TrimSpace(os.Getenv("OPTIMYSTIC_PYTHON"))
	if value != "" {
		return value
	}
	return "python"
}

func pythonTimeout() time.Duration {
	value := strings.TrimSpace(os.Getenv("OPTIMYSTIC_PYTHON_TIMEOUT_SECONDS"))
	if value == "" {
		return 180 * time.Second
	}
	seconds, err := strconv.Atoi(value)
	if err != nil || seconds <= 0 {
		return 180 * time.Second
	}
	return time.Duration(seconds) * time.Second
}

func SelectSolver(req OptimizeRequest) (string, error) {
	if normalizeDomain(req.TemplateType) == "" {
		return "", fmt.Errorf("template_type is required")
	}
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

func projectRoot() string {
	wd, err := os.Getwd()
	if err != nil {
		return "."
	}
	if filepath.Base(wd) == "server" {
		return filepath.Dir(wd)
	}
	return wd
}

// runPythonSolver executes the CLI script and parses the stdout JSON
func runPythonSolver(req OptimizeRequest) (*OptimizeResponse, error) {
	req.TemplateType = normalizeDomain(req.TemplateType)
	req.SolverType = normalizeSolverType(req.SolverType)
	if req.Params == nil {
		req.Params = map[string]interface{}{}
	}
	if req.Sense != "" {
		req.Params["Sense"] = req.Sense
	}

	paramsJson, err := json.Marshal(req.Params)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal params: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), pythonTimeout())
	defer cancel()

	cmd := exec.CommandContext(ctx, pythonCommand(), "python_solvers/cli_solver.py",
		"--domain", req.TemplateType,
		"--solver", req.SolverType,
		"--params", string(paramsJson),
	)
	cmd.Dir = projectRoot()

	output, err := cmd.CombinedOutput()
	if ctx.Err() == context.DeadlineExceeded {
		return nil, fmt.Errorf("python solver timed out after %s", pythonTimeout().String())
	}
	if err != nil {
		return nil, fmt.Errorf("python solver execution failed: %w: %s", err, strings.TrimSpace(string(output)))
	}

	var result OptimizeResponse
	if err := json.Unmarshal(output, &result); err != nil {
		return nil, fmt.Errorf("failed to parse python solver output: %w", err)
	}
	if strings.EqualFold(result.Status, "Error") {
		if result.Error != "" {
			return nil, fmt.Errorf("python solver returned error: %s", result.Error)
		}
		if result.ErrorMsg != "" {
			return nil, fmt.Errorf("python solver returned error: %s", result.ErrorMsg)
		}
		return nil, fmt.Errorf("python solver returned error")
	}

	return &result, nil
}