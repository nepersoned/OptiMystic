package services

import (
	"encoding/json"

	"github.com/optimystic/server/internal/models"
)

// ProcessCuttingResults maps details to CuttingOutput
func ProcessCuttingResults(details map[string]interface{}) (*models.CuttingOutput, error) {
	jsonBytes, err := json.Marshal(details)
	if err != nil {
		return nil, err
	}

	var output models.CuttingOutput
	if err := json.Unmarshal(jsonBytes, &output); err != nil {
		return nil, err
	}
	return &output, nil
}