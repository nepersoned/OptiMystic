package services

import (
	"encoding/json"
	"fmt"

	"github.com/optimystic/server/internal/models"
	"github.com/optimystic/server/internal/solver"
)

// DispatchResults routes raw solver output to domain-specific processors
func DispatchResults(res *solver.OptimizeResponse, domain string) (interface{}, error) {
	if res.Status == "Error" {
		return nil, fmt.Errorf("solver error: status is Error")
	}

	switch domain {
	case "cutting", "manufacturing":
		return ProcessCuttingResults(res.Details)
	case "packing", "logistics":
		return ProcessPackingResults(res.Details)
	case "resourcing", "it", "resource_allocation":
		return ProcessResourcingResults(res.Details)
	case "scheduling", "hr", "nsp":
		return ProcessSchedulingResults(res.Details)
	default:
		return nil, fmt.Errorf("unsupported domain: %s", domain)
	}
}

// MapSensitivity converts raw sensitivity data to model struct
func MapSensitivity(raw map[string]interface{}) (*models.SensitivityOutput, error) {
	if raw == nil {
		return nil, nil
	}

	jsonBytes, _ := json.Marshal(raw)
	var output models.SensitivityOutput
	if err := json.Unmarshal(jsonBytes, &output); err != nil {
		return nil, err
	}
	return &output, nil
}