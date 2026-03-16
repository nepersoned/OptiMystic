package services

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/optimystic/server/internal/models"
	"github.com/optimystic/server/internal/solver"
)

func normalizeDomain(domain string) string {
	switch strings.TrimSpace(strings.ToLower(domain)) {
	case "manufacturing", "cutting":
		return "cutting"
	case "logistics", "packing":
		return "packing"
	case "resource", "it", "cloud", "resource_allocation", "resourcing":
		return "resourcing"
	case "hr", "nsp", "scheduling":
		return "scheduling"
	case "generic", "formula", "custom":
		return "generic"
	default:
		return strings.TrimSpace(strings.ToLower(domain))
	}
}

func DispatchResults(res *solver.OptimizeResponse, domain string) (interface{}, error) {
	if res == nil {
		return nil, fmt.Errorf("solver response is nil")
	}
	if res.Status == "Error" {
		return nil, fmt.Errorf("solver error: status is Error")
	}
	if res.Details == nil {
		res.Details = map[string]interface{}{
			"mode":   normalizeDomain(domain),
			"status": strings.ToLower(strings.TrimSpace(res.Status)),
			"report": "Result details were not provided by the solver.",
		}
	}

	switch normalizeDomain(domain) {
	case "cutting":
		return ProcessCuttingResults(res.Details)
	case "packing":
		return ProcessPackingResults(res.Details)
	case "resourcing":
		return ProcessResourcingResults(res.Details)
	case "scheduling":
		return ProcessSchedulingResults(res.Details)
	case "generic":
		return ProcessGenericResults(res.Details)
	default:
		return res.Details, nil
	}
}

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