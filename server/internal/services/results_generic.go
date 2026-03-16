package services

import (
	"encoding/json"

	"github.com/optimystic/server/internal/models"
)

// ProcessGenericResults maps details to GenericOutput.
func ProcessGenericResults(details map[string]interface{}) (*models.GenericOutput, error) {
	jsonBytes, err := json.Marshal(details)
	if err != nil {
		return nil, err
	}

	var output models.GenericOutput
	if err := json.Unmarshal(jsonBytes, &output); err != nil {
		return nil, err
	}
	return &output, nil
}
