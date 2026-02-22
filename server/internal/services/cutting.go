package services

import (
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"server/internal/models"
	"server/internal/solver"
)

func ProcessCuttingResults(resp *solver.SolveResponse, input *models.CuttingInput) *models.CuttingOutput {
	if resp == nil || resp.Status != "Optimal" {
		return &models.CuttingOutput{
			TotalCost:  0,
			TotalWaste: 0,
			NumBins:    0,
			BinPlans:   []models.BinPlan{},
			Report:     "No cutting plan generated.",
			ItemCounts: make(map[string]int),
			Status:     "no_solution",
		}
	}

	if len(input.Items) == 0 || len(input.ItemLens) == 0 {
		return &models.CuttingOutput{Status: "error", Report: "Invalid input"}
	}

	rawBins := make(map[string]*BinData)
	totalCost := 0.0
	totalWaste := 0.0

	for _, v := range resp.Variables {
		val := v.Value
		if val < 0.001 { // Skip near-zero
			continue
		}

		varName := v.Variable

		if strings.Contains(varName, "A_IT") {
			binID, itemIdx, err := parseColumnGenerationVar(varName)
			if err != nil {
				continue
			}
			if itemIdx >= len(input.Items) {
				continue
			}

			if rawBins[binID] == nil {
				rawBins[binID] = &BinData{
					StockIdx: extractStockIndex(binID),
					Items:    []ItemData{},
				}
			}

			for i := 0; i < int(val); i++ {
				rawBins[binID].Items = append(rawBins[binID].Items, ItemData{
					Name: input.Items[itemIdx],
					Len:  input.ItemLens[itemIdx],
				})
			}
		}

		if strings.HasPrefix(varName, "Cut_") {
			binID, itemIdx, err := parseMIPVar(varName, input.Items)
			if err != nil {
				continue
			}
			if itemIdx >= len(input.Items) {
				continue
			}

			if rawBins[binID] == nil {
				rawBins[binID] = &BinData{
					StockIdx: extractStockIndex(binID),
					Items:    []ItemData{},
				}
			}

			for i := 0; i < int(val); i++ {
				rawBins[binID].Items = append(rawBins[binID].Items, ItemData{
					Name: input.Items[itemIdx],
					Len:  input.ItemLens[itemIdx],
				})
			}
		}
	}

	sortedBinIDs := getSortedKeys(rawBins)
	binPlans := []models.BinPlan{}
	itemCounts := make(map[string]int)

	for _, binID := range sortedBinIDs {
		binData := rawBins[binID]
		stock := input.Stocks[binData.StockIdx]

		totalCost += stock.Cost

		currentPos := 0.0
		for i, item := range binData.Items {
			currentPos += item.Len
			if input.Kerf > 0 && i < len(binData.Items)-1 {
				currentPos += input.Kerf
			}
		}

		waste := stock.Length - currentPos
		if waste < 0 {
			waste = 0
		}
		totalWaste += waste

		usagePct := (currentPos / stock.Length) * 100.0

		binPlans = append(binPlans, models.BinPlan{
			Stock: stock.Name,
			Plan:  fmt.Sprintf("%d cut", len(binData.Items)),
			Usage: fmt.Sprintf("%.1f%%", usagePct),
		})

		for _, item := range binData.Items {
			itemCounts[item.Name]++
		}
	}

	reportLines := []string{
		"### Execution Summary",
		fmt.Sprintf("- **Total Material Cost:** $%.2f", totalCost),
		fmt.Sprintf("- **Total Scrap Generated:** %.1f mm", totalWaste),
		fmt.Sprintf("- **Bins Used:** %d", len(rawBins)),
	}

	topItems := getTopItems(itemCounts, 5)
	for _, item := range topItems {
		reportLines = append(reportLines, fmt.Sprintf("- %s: %d pcs", item.Name, item.Count))
	}

	report := strings.Join(reportLines, "\n")

	return &models.CuttingOutput{
		TotalCost:  round(totalCost, 2),
		TotalWaste: round(totalWaste, 2),
		NumBins:    len(rawBins),
		BinPlans:   binPlans,
		Report:     report,
		ItemCounts: itemCounts,
		Status:     "ok",
	}
}

type BinData struct {
	StockIdx int
	Items    []ItemData
}

type ItemData struct {
	Name string
	Len  float64
}

type TopItem struct {
	Name  string
	Count int
}

func parseColumnGenerationVar(varName string) (string, int, error) {
	re := regexp.MustCompile(`A_IT(\d+)_(.+)`)
	matches := re.FindStringSubmatch(varName)
	if len(matches) < 3 {
		return "", 0, fmt.Errorf("invalid var format: %s", varName)
	}

	itemIdx, err := strconv.Atoi(matches[1])
	if err != nil {
		return "", 0, err
	}

	binID := matches[2]

	return binID, itemIdx, nil
}

func parseMIPVar(varName string, items []string) (string, int, error) {
	rem := strings.TrimPrefix(varName, "Cut_")

	stPos := strings.LastIndex(rem, "_ST")
	cgPos := strings.LastIndex(rem, "_CG")

	var pos int
	if stPos > cgPos {
		pos = stPos
	} else {
		pos = cgPos
	}

	var itemPart, binID string
	if pos == -1 {
		parts := strings.Split(rem, "_")
		if len(parts) < 2 {
			return "", 0, fmt.Errorf("invalid MIP var: %s", varName)
		}
		itemPart = strings.Join(parts[:len(parts)-1], "_")
		binID = parts[len(parts)-1]
	} else {
		itemPart = rem[:pos]
		binID = rem[pos+1:]
	}

	// Find item index
	itemIdx := -1
	cleanItemPart := strings.Map(func(r rune) rune {
		if r < 'A' || r > 'z' {
			return '_'
		}
		return r
	}, itemPart)

	for i, item := range items {
		cleanItem := strings.Map(func(r rune) rune {
			if r < 'A' || r > 'z' {
				return '_'
			}
			return r
		}, item)

		if strings.Contains(cleanItemPart, cleanItem) || item == itemPart {
			itemIdx = i
			break
		}
	}

	if itemIdx == -1 {
		return "", 0, fmt.Errorf("item not found: %s", itemPart)
	}

	return binID, itemIdx, nil
}

// extractStockIndex: "ST3" → 3
func extractStockIndex(binID string) int {
	re := regexp.MustCompile(`ST(\d+)`)
	matches := re.FindStringSubmatch(binID)
	if len(matches) < 2 {
		return 0
	}

	idx, err := strconv.Atoi(matches[1])
	if err != nil {
		return 0
	}

	return idx
}

// getSortedKeys: map 키를 정렬해서 반환
func getSortedKeys(m map[string]*BinData) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// getTopItems: itemCounts에서 상위 N개 추출
func getTopItems(counts map[string]int, n int) []TopItem {
	items := make([]TopItem, 0, len(counts))
	for name, count := range counts {
		items = append(items, TopItem{Name: name, Count: count})
	}

	// Sort by count descending
	sort.Slice(items, func(i, j int) bool {
		return items[i].Count > items[j].Count
	})

	if len(items) > n {
		items = items[:n]
	}

	return items
}

// round: 소수점 자리수 반올림
func round(val float64, decimals int) float64 {
	multiplier := 1.0
	for i := 0; i < decimals; i++ {
		multiplier *= 10
	}
	return float64(int(val*multiplier+0.5)) / multiplier
}
