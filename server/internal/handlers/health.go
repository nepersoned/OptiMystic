package handlers

import (
	"encoding/json"
	"net/http"
)

// health.go: HTTP handler for health check.
// Replaces Django's core/views.py::health_view

// Responsibilities:
// - Respond with {"status": "ok"} to GET /api/health/

type HealthResponse struct {
	Status string `json:"status"`
}

func HandleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	err := json.NewEncoder(w).Encode(HealthResponse{Status: "ok"})
	if err != nil {
		return
	}
}
