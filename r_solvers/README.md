# R Analytics Runtime

R layer for post-processing and visualization of OptiMystic optimization outputs.

## Purpose

- Convert solver JSON to analysis-friendly tables
- Produce domain-oriented summary metrics
- Render charts for notebooks and decision reviews

## Core Files

- `utils.R`: shared helpers and mode normalization
- `processors.R`: main result dispatch — handles all 6 domains
- `analytics.R`: repeated-run diagnostics, bootstrap confidence intervals
- `chart_data.R`: ECharts/Recharts JSON builders, KPI calculations
- `plotting.R`: common plotting utilities

## Integration

R analysis is invoked via `r_bridge.analyze_with_r()` in Python — do not call
R scripts directly from application code. The bridge handles:

- Cross-platform R_HOME discovery (Windows + Linux/Docker)
- `ensure_r_bridge()` — sources all 4 scripts into the R global env
- `run_r_post_analysis()` — executes the full analysis pipeline
- Error wrapping — returns `{"ok": False, "error": {...}}` on failure

## Returned Structure

```python
{
    "processed_result": {...},   # domain-specific KPIs and summaries
    "sensitivity": {...},        # shadow prices and slack analysis
    "decision_analytics": {...}, # bootstrap CI, run comparisons
    "executive_summary": {...},  # structured plain-language summary
    "chart_data": {...},         # ECharts-ready JSON
}
```

## Typical Notebook Use

```r
setwd('r_solvers')
source('utils.R')
source('processors.R')
source('analytics.R')
source('plotting.R')

result <- jsonlite::fromJSON('{"status":"Optimal","objective":10}')
store <- list(parameters = list())
processed <- process_results(result, store, mode = 'packing')
print(processed)
```

## Dependencies

```r
install.packages(c('dplyr', 'ggplot2', 'jsonlite', 'tidyr'))
```

## Docker / Linux

R is installed via `r-base` in the Docker image. `R_HOME` is set to `/usr/lib/R`
via `ENV R_HOME=/usr/lib/R` in both `Dockerfile.deps` and `docker/Dockerfile`.
No manual configuration needed in containerized environments.

## Scope Note

R is an analytics layer, not a primary optimizer runtime. Optimization execution
remains in Python (OR-Tools) and Julia (JuMP).
