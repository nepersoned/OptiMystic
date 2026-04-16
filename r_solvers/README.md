# R Analytics Runtime

R layer for post-processing and visualization of OptiMystic optimization outputs.

## Purpose

- Convert solver JSON to analysis-friendly tables
- Produce domain-oriented summary metrics
- Render charts for notebooks and decision reviews

## Core Files

- `utils.R`: shared helpers and mode normalization
- `processors.R`: main result dispatch and summary creation
- `analytics.R`: repeated-run diagnostics and comparison helpers
- `plotting.R`: common plotting utilities
- `domains/*.R`: domain-specific enrichments

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

## Scope Note

R is an analytics layer, not a primary optimizer runtime. Optimization execution remains in Python/Julia.
