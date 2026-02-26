package models

// ------------------------------------------
// Shared structs
// ------------------------------------------

type SensitivityOutput struct {
	Constraints   []SensitivityConstraint `json:"constraints"`
	TopBottleneck string                  `json:"top_bottleneck"`
	Insight       string                  `json:"insight"`
}

type SensitivityConstraint struct {
	Constraint  string  `json:"Constraint"`
	ShadowPrice string  `json:"Shadow Price"`
	Slack       float64 `json:"Slack"`
}

// ------------------------------------------
// Domain: Cutting
// ------------------------------------------

type CuttingInput struct {
	Items   []CuttingItem  `json:"Items"`
	Stocks  []CuttingStock `json:"Stocks"`
	Kerf    float64        `json:"Kerf"`
	Sense   string         `json:"Sense,omitempty"`
	Demands map[string]int `json:"Demands,omitempty"`
}

type CuttingItem struct {
	Name   string  `json:"Name"`
	Length float64 `json:"Length"`
	Demand int     `json:"Demand"`
	Price  float64 `json:"Price,omitempty"`
}

type CuttingStock struct {
	Name   string  `json:"Name"`
	Length float64 `json:"Length"`
	Cost   float64 `json:"Cost"`
	Limit  int     `json:"Limit"`
}

type CuttingOutput struct {
	TotalCost  float64          `json:"total_cost"`
	TotalWaste float64          `json:"total_waste"`
	NumBins    int              `json:"num_bins"`
	BinPlans   []CuttingBinPlan `json:"bin_plans"`
	ItemCounts map[string]int   `json:"item_counts"`
	Status     string           `json:"status"`
	Report     string           `json:"report"`
}

type CuttingBinPlan struct {
	Stock string `json:"Stock"`
	Plan  string `json:"Plan"`
	Usage string `json:"Usage"`
}

// ------------------------------------------
// Domain: Packing
// ------------------------------------------

type PackingInput struct {
	Items    []PackingItem `json:"Items"`
	Vehicles []Vehicle     `json:"Vehicles"`
	Sense    string        `json:"Sense,omitempty"`
}

type PackingItem struct {
	Name   string  `json:"Name"`
	Weight float64 `json:"Weight"`
	Value  float64 `json:"Value"`
	Demand int     `json:"Demand,omitempty"`
}

type Vehicle struct {
	Capacity float64 `json:"Capacity"`
	Cost     float64 `json:"Cost,omitempty"`
}

type PackingOutput struct {
	TotalValue   float64               `json:"total_value"`
	UsedCapacity float64               `json:"used_capacity"`
	Capacity     float64               `json:"capacity"`
	Items        []PackingSelectedItem `json:"items"`
	Status       string                `json:"status"`
	Report       string                `json:"report"`
}

type PackingSelectedItem struct {
	Item   string  `json:"item"`
	Count  float64 `json:"count"`
	Weight float64 `json:"weight"`
	Value  float64 `json:"value"`
}

// ------------------------------------------
// Domain: Resourcing
// ------------------------------------------

type ResourcingInput struct {
	Items   []ResourceTask `json:"Items"`
	Servers []ServerNode   `json:"Servers"`
	Sense   string         `json:"Sense,omitempty"`
}

type ResourceTask struct {
	Name string  `json:"Name"`
	CPU  float64 `json:"CPU"`
	RAM  float64 `json:"RAM"`
	Cost float64 `json:"Cost,omitempty"`
}

type ServerNode struct {
	CPU float64 `json:"CPU"`
	RAM float64 `json:"RAM"`
}

type ResourcingOutput struct {
	TotalValue  float64                  `json:"total_value"`
	UsedCPU     float64                  `json:"used_cpu"`
	UsedRAM     float64                  `json:"used_ram"`
	CapacityCPU float64                  `json:"capacity_cpu"`
	CapacityRAM float64                  `json:"capacity_ram"`
	Items       []ResourcingSelectedItem `json:"items"`
	Status      string                   `json:"status"`
	Report      string                   `json:"report"`
}

type ResourcingSelectedItem struct {
	Item  string  `json:"item"`
	Count float64 `json:"count"`
	CPU   float64 `json:"cpu"`
	RAM   float64 `json:"ram"`
	Value float64 `json:"value"`
}

// ------------------------------------------
// Domain: Scheduling
// ------------------------------------------

type SchedulingInput struct {
	Items                []Employee     `json:"Items"`
	Shifts               []string       `json:"Shifts"`
	Demands              map[string]int `json:"Demands"`
	MaxShiftsPerEmployee int            `json:"MaxShiftsPerEmployee"`
	Sense                string         `json:"Sense,omitempty"`
}

type Employee struct {
	Name     string  `json:"Name"`
	Duration float64 `json:"Duration"`
	Value    float64 `json:"Value,omitempty"`
}

type SchedulingOutput struct {
	ShiftCoverage map[string]int         `json:"shift_coverage"`
	Assignments   []SchedulingAssignment `json:"assignments"`
	Status        string                 `json:"status"`
	Report        string                 `json:"report"`
}

type SchedulingAssignment struct {
	Employee string  `json:"employee"`
	Shift    string  `json:"shift"`
	Value    float64 `json:"value"`
}