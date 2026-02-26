package services

import (
	"encoding/json"

	"github.com/optimystic/server/internal/models"
)

// ProcessResourcingResults maps details to ResourcingOutput
func ProcessResourcingResults(details map[string]interface{}) (*models.ResourcingOutput, error) {
	jsonBytes, err := json.Marshal(details)
	if err != nil {
		return nil, err
	}

	var output models.ResourcingOutput
	if err := json.Unmarshal(jsonBytes, &output); err != nil {
		return nil, err
	}
	return &output, nil
}