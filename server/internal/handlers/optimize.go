package handlers

import (
	"encoding/json"
	"io"
	"net/http"

	"github.com/optimystic/server/internal/solver"

	"github.com/optimystic/server/internal/services"
)

// HandleOptimize manages the full optimization flow: request parsing, solver execution, and result dispatching.
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

	// 1. Unmarshal request into solver-compatible structure
	var req solver.OptimizeRequest
	if err := json.Unmarshal(body, &req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// 2. Execute solver bridge (CLI execution & raw parsing)
	result, err := solver.RunSolver(req)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// 3. Dispatch raw details to domain-specific output models
	finalDetails, err := services.DispatchResults(result, req.TemplateType)
	if err != nil {
		http.Error(w, "Result processing failed: "+err.Error(), http.StatusInternalServerError)
		return
	}

	// 4. Map raw sensitivity data if available
	sensitivity, _ := services.MapSensitivity(result.Sensitivity)

	// 5. Construct final unified response
	response := map[string]interface{}{
		"status":      result.Status,
		"objective":   result.Objective,
		"solve_time":  result.SolveTime,
		"details":     finalDetails,
		"sensitivity": sensitivity,
	}

	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(response); err != nil {
		http.Error(w, "Failed to encode response", http.StatusInternalServerError)
		return
	}
}