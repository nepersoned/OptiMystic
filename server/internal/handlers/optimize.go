package handlers

import (
	"encoding/json"
	"io"
	"net/http"
	// "github.com/optimystic/server/internal/solver"
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
	defer r.Body.Close()

	var req OptimizeRequest
	if err := json.Unmarshal(body, &req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// TODO: Call bridge.SelectSolver()
	// TODO: Execute Python solver
	// TODO: Return JSON response

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(OptimizeResponse{
		Status: "Optimal",
	})
}
