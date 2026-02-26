package services

import (
	"encoding/json"

	"github.com/optimystic/server/internal/models"
)

// ProcessSchedulingResults maps details to SchedulingOutput
func ProcessSchedulingResults(details map[string]interface{}) (*models.SchedulingOutput, error) {
	jsonBytes, err := json.Marshal(details)
	if err != nil {
		return nil, err
	}

	var output models.SchedulingOutput
	if err := json.Unmarshal(jsonBytes, &output); err != nil {
		return nil, err
	}
	return &output, nil
}