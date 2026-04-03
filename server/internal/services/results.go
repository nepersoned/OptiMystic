package services

import (
	"fmt"
	"strings"

	"github.com/mitchellh/mapstructure"
	"github.com/optimystic/server/internal/models"
	"github.com/optimystic/server/internal/solver"
)

func mapToStruct[T any](details map[string]interface{}) (*T, error) {
	var output T
	decoder, err := mapstructure.NewDecoder(&mapstructure.DecoderConfig{
		TagName:          "json",
		Result:           &output,
		WeaklyTypedInput: true,
	})
	if err != nil {
		return nil, err
	}
	if err := decoder.Decode(details); err != nil {
		return nil, err
	}
	return &output, nil
}

func normalizeDomain(domain string) string {
	switch strings.TrimSpace(strings.ToLower(domain)) {
	case "manufacturing", "cutting":
		return "cutting"
	case "logistics", "packing":
		return "packing"
	case "vrp", "routing", "vehicle_routing":
		return "vrp"
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

func DispatchResults(res *solver.OptimizeResponse, domain string, solverType string) (interface{}, error) {
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
		return mapToStruct[models.CuttingOutput](res.Details)
	case "packing":
		return mapToStruct[models.PackingOutput](res.Details)
	case "vrp":
		return mapToStruct[models.VRPOutput](res.Details)
	case "resourcing":
		return mapToStruct[models.ResourcingOutput](res.Details)
	case "scheduling":
		return mapToStruct[models.SchedulingOutput](res.Details)
	case "generic":
		if strings.TrimSpace(strings.ToLower(solverType)) == "nlp" {
			return mapToStruct[models.NlpOutput](res.Details)
		}
		return mapToStruct[models.GenericOutput](res.Details)
	default:
		return res.Details, nil
	}
}

func MapSensitivity(raw map[string]interface{}) (*models.SensitivityOutput, error) {
	if raw == nil {
		return nil, nil
	}

	return mapToStruct[models.SensitivityOutput](raw)
}
