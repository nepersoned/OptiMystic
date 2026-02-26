package services

import (
	"encoding/json"

	"github.com/optimystic/server/internal/models"
)

// ProcessPackingResults maps details to PackingOutput
func ProcessPackingResults(details map[string]interface{}) (*models.PackingOutput, error) {
	jsonBytes, err := json.Marshal(details)
	if err != nil {
		return nil, err
	}

	var output models.PackingOutput
	if err := json.Unmarshal(jsonBytes, &output); err != nil {
		return nil, err
	}
	return &output, nil
}