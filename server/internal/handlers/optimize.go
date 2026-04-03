package handlers

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"strings"

	"github.com/optimystic/server/internal/models"
	"github.com/optimystic/server/internal/services"
	"github.com/optimystic/server/internal/solver"
)

func writeJSON(w http.ResponseWriter, statusCode int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	_ = json.NewEncoder(w).Encode(payload)
}

type apiError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}

func writeAPIError(w http.ResponseWriter, statusCode int, code string, message string) {
	writeJSON(w, statusCode, apiError{Code: code, Message: message})
}

func toRawVariables(values []map[string]interface{}) []models.RawVariable {
	result := make([]models.RawVariable, 0, len(values))
	for _, value := range values {
		result = append(result, models.RawVariable(value))
	}
	return result
}

func toRawConstraints(values []map[string]interface{}) []models.RawConstraint {
	result := make([]models.RawConstraint, 0, len(values))
	for _, value := range values {
		result = append(result, models.RawConstraint(value))
	}
	return result
}

func HandleOptimize(w http.ResponseWriter, r *http.Request) {
	defer r.Body.Close()

	var req models.OptimizeRequest
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&req); err != nil {
		writeAPIError(w, http.StatusBadRequest, "invalid_json", "Request body is not valid JSON")
		return
	}
	if strings.TrimSpace(req.TemplateType) == "" {
		req.TemplateType = req.Domain
	}
	if strings.TrimSpace(req.SolverType) == "" {
		req.SolverType = req.Solver
	}
	if strings.TrimSpace(req.TemplateType) == "" {
		writeAPIError(w, http.StatusBadRequest, "template_type_required", "template_type (or domain) is required")
		return
	}
	if req.Params == nil {
		writeAPIError(w, http.StatusBadRequest, "params_required", "params is required")
		return
	}

	result, err := solver.RunSolver(solver.OptimizeRequest{
		TemplateType: req.TemplateType,
		Params:       req.Params,
		Sense:        req.Sense,
		SolverType:   req.SolverType,
	})
	if err != nil {
		slog.Error("solver_execution_failed", "template_type", req.TemplateType, "solver_type", req.SolverType, "error", err.Error())
		writeAPIError(w, http.StatusInternalServerError, "solver_execution_failed", err.Error())
		return
	}

	finalDetails, err := services.DispatchResults(result, req.TemplateType, req.SolverType)
	if err != nil {
		slog.Error("result_processing_failed", "template_type", req.TemplateType, "error", err.Error())
		writeAPIError(w, http.StatusInternalServerError, "result_processing_failed", err.Error())
		return
	}

	sensitivity, err := services.MapSensitivity(result.Sensitivity)
	if err != nil {
		slog.Error("sensitivity_mapping_failed", "template_type", req.TemplateType, "error", err.Error())
		writeAPIError(w, http.StatusInternalServerError, "sensitivity_mapping_failed", err.Error())
		return
	}

	writeJSON(w, http.StatusOK, models.OptimizeResponse{
		Status:      result.Status,
		Objective:   result.Objective,
		SolveTime:   result.SolveTime,
		Variables:   toRawVariables(result.Variables),
		Constraints: toRawConstraints(result.Constraints),
		Details:     finalDetails,
		Sensitivity: sensitivity,
	})
}
