package handlers

import (
	"encoding/json"
	"net/http"
	"strings"

	"github.com/optimystic/server/internal/models"
	"github.com/optimystic/server/internal/solver"
	"github.com/optimystic/server/internal/services"
)

func writeJSON(w http.ResponseWriter, statusCode int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	_ = json.NewEncoder(w).Encode(payload)
}

func HandleOptimize(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "method_not_allowed"})
		return
	}
	defer r.Body.Close()

	var req models.OptimizeRequest
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid_json"})
		return
	}
	if strings.TrimSpace(req.TemplateType) == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "template_type_required"})
		return
	}
	if req.Params == nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "params_required"})
		return
	}

	result, err := solver.RunSolver(solver.OptimizeRequest{
		TemplateType: req.TemplateType,
		Params:       req.Params,
		Sense:        req.Sense,
		SolverType:   req.SolverType,
	})
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": err.Error()})
		return
	}

	finalDetails, err := services.DispatchResults(result, req.TemplateType)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "result_processing_failed", "detail": err.Error()})
		return
	}

	sensitivity, _ := services.MapSensitivity(result.Sensitivity)

	writeJSON(w, http.StatusOK, models.OptimizeResponse{
		Status:      result.Status,
		Objective:   result.Objective,
		SolveTime:   result.SolveTime,
		Variables:   result.Variables,
		Constraints: result.Constraints,
		Details:     finalDetails,
		Sensitivity: sensitivity,
	})
}