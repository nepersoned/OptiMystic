# R Analytics & Visualization Runtime

R-based post-processing and visualization layer for OptiMystic solver outputs.

**Design**: Consumes JSON results from Python/Julia solvers, normalizes domain-specific data, and serves as the dedicated post-analysis layer in Jupyter workflows.

**Direction**: R is being expanded as the primary deep-analysis tier for business interpretation, statistical diagnostics, and high-quality visualization.

## Architecture

```
Python/Julia Solver
  ↓ (JSON result)
└─ R processors
   ├─ utils.R                  (common helpers)
   ├─ processors.R            (domain dispatchers)
   ├─ plotting.R              (shared visualization helpers)
   └─ domains/
      ├─ cutting.R            (cutting optimization)
      ├─ packing.R            (bin packing)
      └─ vrp.R                (vehicle routing)
  ↓
Jupyter Notebook
  ├─ data processing
  ├─ result analysis
  └─ interactive visualization (ggplot2)
```

## File Structure

### Core Files

#### `utils.R` — Common Utilities
- `safe_numeric()` — Type-safe numeric conversion
- `normalize_mode()` — Domain alias resolution
- `parameter_map()` — Parameter extraction helper
- `clean_name()` — Variable name normalization
- `get_variable_name()`, `get_variable_value()` — Variable parsing

**MODE_ALIASES:**
- `cutting`: manufacturing, cutting
- `packing`: logistics, packing
- `vrp`: routing, vehicle_routing, vrp
- `resourcing`: resource, it, cloud, resource_allocation
- `scheduling`: hr, nsp, scheduling
- `nlp`: nlp
- `generic`: formula, custom, generic

#### `processors.R` — Result Processing
- `process_results()` — Main dispatcher
- Domain-specific handlers:
  - `process_cutting_extended()` — Material cost, efficiency
  - `process_packing_extended()` — Capacity utilization, item selection
  - `process_vrp_extended()` — Route analysis, node coverage
  - `process_resourcing_results()` — Resource allocation
  - `process_scheduling_results()` — Shift assignments
  - `process_nlp_results()` — Nonlinear optimization
  - `process_generic_results()` — Fallback handler

#### `plotting.R` — Visualization Framework
- `prepare_df_generic()` — Convert results to data frames
- `plot_variables_bar()` — Top variables bar chart
- `plot_objective_summary()` — Objective metrics
- Domain dispatchers:
  - `plot_cutting()` — Routes to cutting plots
  - `plot_packing()` — Routes to packing plots
  - `plot_vrp()` — Routes to VRP plots

### Domain-Specific Modules (in `domains/`)

#### `domains/cutting.R` — Cutting Stock Optimization
**Functions:**
- `process_cutting_extended()` — Enhanced cutting analysis
- `parse_cutting_bins()` — Extract bin details from variables
- `calculate_cutting_metrics()` — Cost, efficiency, waste analysis
- `plot_cutting_efficiency()` — Material utilization pie chart
- `plot_cutting_cost()` — Cost breakdown bar chart

**Metrics:**
- Material efficiency percentage
- Total scrap/waste
- Cost per bin
- Efficiency trends

#### `domains/packing.R` — Bin Packing Optimization
**Functions:**
- `process_packing_extended()` — Enhanced packing analysis
- `parse_packing_items()` — Extract selected items
- `calculate_packing_metrics()` — Capacity, value analysis
- `plot_packing_utilization()` — Capacity usage pie chart
- `plot_packing_items()` — Item selection bar chart

**Metrics:**
- Capacity utilization percentage
- Total value achieved
- Items selected count
- Value per unit weight

#### `domains/vrp.R` — Vehicle Routing Optimization
**Functions:**
- `process_vrp_extended()` — Enhanced route analysis
- `calculate_route_statistics()` — Per-route metrics
- `calculate_vrp_coverage()` — Node serving analysis
- `plot_vrp_distance()` — Route distance chart
- `plot_vrp_coverage()` — Node coverage bar chart
- `plot_vrp_routes_summary()` — Routes overview

**Metrics:**
- Total distance per route
- Average stops per route
- Coverage percentage
- Unserved nodes count

## Usage in Jupyter Notebook

```r
# 1. Load core modules
setwd('r_solvers')
source('utils.R')
source('processors.R')

# 2. Load domain modules (optional, auto-loaded by processors.R)
source('domains/cutting.R')
source('domains/packing.R')
source('domains/vrp.R')

# 3. Process solver result
result <- fromJSON('{"status":"Optimal",...}')
store <- list(parameters = list(Items = c(...), ...))

# 4. Process and analyze
processed <- process_results(result, store, mode = "cutting")

# 5. Visualize
plot <- plot_cutting(processed, plot_type = "efficiency")
print(plot)
```

## Testing

**Jupyter Notebook Test Suite:** `examples/test_jupyterlab_full_pipeline.ipynb`

Tests included:
- Core module loading
- Cutting domain: processing & visualization
- Packing domain: processing & visualization
- VRP domain: processing & visualization
- Main dispatcher integration
- Complete pipeline validation
- Dynamic packing dashboard: selected items, efficiency, and capacity what-if

Run in Jupyter:
```r
setwd('../')
# Execute notebook cells sequentially
```

## Dependencies

**Required:**
- `dplyr` (data manipulation)
- `ggplot2` (publication-quality graphics)
- `jsonlite` (JSON I/O)
- `tidyr` (data reshaping)

**Installation:**
```r
install.packages(c("dplyr", "ggplot2", "jsonlite", "tidyr"))
```

**Optional (Phase 2+):**
- `plotly` (interactive plots)
- `leaflet` (geographic maps for VRP)
- `shiny` (interactive dashboards)

## Architecture Decisions

1. **Modular by Domain**: Each domain has its own file for easy maintenance and extension
2. **Two-Stage Processing**: `processors.R` handles data normalization; `domains/*.R` add specialized analysis
3. **Flexible Visualization**: `plotting.R` provides base utilities; domain files extend with specific charts
4. **Error Resilience**: tryCatch in `processors.R` loads domains gracefully (non-blocking if missing)
5. **Type Safety**: All functions handle NULL, NA, and type mismatches gracefully

## Future Roadmap

### Phase 2: Enhanced Visualization
- [ ] Add `plotly` for interactive plots
- [ ] Create Shiny dashboard stubs
- [ ] Sensitivity analysis plots
- [ ] Heatmaps for resource utilization

### Phase 3: Domain Expansion
- [ ] `domains/resourcing.R` — Resource allocation charts
- [ ] `domains/scheduling.R` — Gantt charts for assignments
- [ ] `domains/nlp.R` — Convergence diagnostics
- [ ] `domains/generic.R` — Custom IR analysis

### Phase 4: Advanced Post-Analysis
- [ ] Automated anomaly detection on solver outputs
- [ ] Scenario-comparison reports across solver runs
- [ ] Executive-ready summary templates per domain

## Notes

- All functions preserve input types and return consistent structures
- Domain dispatching is case-insensitive and alias-aware
- Domain modules source themselves from parent working directory
- Sensitivity analysis is stubbed; implement per domain as needed
- Compatible with Jupyter R kernel and RStudio



