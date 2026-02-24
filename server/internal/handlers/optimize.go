package handlers

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os/exec"

	"github.com/optimystic/server/internal/solver"
)

// OptimizeRequest represents the incoming JSON payload
type OptimizeRequest struct {
	TemplateType string                 `json:"template_type"`
	Params       map[string]interface{} `json:"params"`
	Sense        string                 `json:"sense,omitempty"`
}

// OptimizeResponse represents the solver output
type OptimizeResponse struct {
	Status      string                 `json:"status"`
	Objective   float64                `json:"objective"`
	Variables   map[string]interface{} `json:"variables"`
	Constraints []interface{}          `json:"constraints,omitempty"`
	Dashboard   map[string]interface{} `json:"dashboard,omitempty"`
	Sensitivity map[string]interface{} `json:"sensitivity,omitempty"`
}

func HandleOptimize(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Failed to read request body", http.StatusBadRequest)
		return
	}
	defer func(Body io.ReadCloser) {
		err := Body.Close()
		if err != nil {

		}
	}(r.Body)

	var req OptimizeRequest
	if err := json.Unmarshal(body, &req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	solverName, err := solver.SelectSolver(req)
	if err != nil {
		http.Error(w, "Solver selection failed", http.StatusInternalServerError)
		return
	}

	if solverName == "python_solver" {
		domain := req.TemplateType
		paramsJson, err := json.Marshal(req.Params)
		if err != nil {
			http.Error(w, "Failed to marshal params", http.StatusInternalServerError)
			return
		}
		cmd := exec.Command("python", "python_solvers/cli_solver.py",
			"--domain", domain,
			"--solver", solverName,
			"--params", string(paramsJson),
		)
		output, err := cmd.Output()
		if err != nil {
			http.Error(w, "Python solver execution failed", http.StatusInternalServerError)
			return
		}
		var pyResult map[string]interface{}
		if err := json.Unmarshal(output, &pyResult); err != nil {
			http.Error(w, "Failed to parse Python solver output", http.StatusInternalServerError)
			return
		}

		var result OptimizeResponse
		if status, ok := pyResult["status"].(string); ok {
			result.Status = status
		}
		if obj, ok := pyResult["objective"].(float64); ok {
			result.Objective = obj
		}
		if vars, ok := pyResult["variables"].(map[string]interface{}); ok {
			result.Variables = vars
		} else if varsArr, ok := pyResult["variables"].([]interface{}); ok {
			result.Variables = make(map[string]interface{})
			for i, v := range varsArr {
				result.Variables[fmt.Sprintf("var_%d", i)] = v
			}
		}
		if cons, ok := pyResult["constraints"].([]interface{}); ok {
			result.Constraints = cons
		}
		if dash, ok := pyResult["dashboard"].(map[string]interface{}); ok {
			result.Dashboard = dash
		}
		if sens, ok := pyResult["lp_sensitivity"].(map[string]interface{}); ok {
			result.Sensitivity = sens
		}

		w.Header().Set("Content-Type", "application/json")
		err = json.NewEncoder(w).Encode(result)
		if err != nil {
			http.Error(w, "Failed to encode response", http.StatusInternalServerError)
			return
		}
	}
}
