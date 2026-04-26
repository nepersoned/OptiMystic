# Result processing and domain-specific handlers
# Migrated from python_solvers/utils/services.py

source("utils.R")
source("plotting.R")
source("analytics.R")
source("chart_data.R")

# Load domain-specific modules
tryCatch({
  source("domains/cutting.R")
}, error = function(e) {
  warning("Could not load cutting domain module")
})

tryCatch({
  source("domains/packing.R")
}, error = function(e) {
  warning("Could not load packing domain module")
})

tryCatch({
  source("domains/vrp.R")
}, error = function(e) {
  warning("Could not load VRP domain module")
})

tryCatch({
  source("domains/resourcing.R")
}, error = function(e) {
  warning("Could not load resourcing domain module")
})

tryCatch({
  source("domains/scheduling.R")
}, error = function(e) {
  warning("Could not load scheduling domain module")
})

tryCatch({
  source("domains/nlp.R")
}, error = function(e) {
  warning("Could not load NLP domain module")
})

tryCatch({
  source("domains/generic.R")
}, error = function(e) {
  warning("Could not load generic domain module")
})

# Main dispatcher for result processing
process_results <- function(res, store, mode = NULL) {
  if (!is.list(res)) {
    return(list(
      status = "Error",
      error_msg = "Invalid solver response"
    ))
  }
  
  # Normalize mode
  mode <- normalize_mode(mode)
  
  # Route to domain-specific processor
  switch(mode,
    "cutting" = process_cutting_results(res, store),
    "packing" = process_packing_results(res, store),
    "vrp" = process_vrp_results(res, store),
    "resourcing" = process_resourcing_results(res, store),
    "scheduling" = process_scheduling_results(res, store),
    "nlp" = process_nlp_results(res, store),
    "generic" = process_generic_results(res, store),
    # Fallback to generic
    process_generic_results(res, store)
  )
}

normalize_status <- function(status) {
  s <- tolower(as.character(status %||% "unknown"))
  if (s %in% c("optimal", "ok", "feasible")) {
    return("ok")
  }
  if (s %in% c("infeasible", "unbounded")) {
    return(s)
  }
  if (s %in% c("error", "failed")) {
    return("error")
  }
  s
}

# ============================================================================
# SENSITIVITY ANALYSIS
# ============================================================================

constraint_name <- function(constraint) {
  if (!is.list(constraint)) {
    return("Unknown")
  }
  as.character(constraint$Constraint %||% constraint$constraint %||% constraint$name %||% "Unknown")
}

constraint_shadow <- function(constraint) {
  if (!is.list(constraint)) {
    return(0)
  }
  safe_numeric(constraint$`Shadow Price` %||% constraint$shadow_price %||% constraint$dual %||% 0)
}

constraint_slack <- function(constraint) {
  if (!is.list(constraint)) {
    return(0)
  }
  safe_numeric(constraint$Slack %||% constraint$slack %||% 0)
}

process_cutting_sensitivity <- function(res, store) {
  consts <- res$constraints %||% list()
  params <- parameter_map(store)
  items <- params$Items %||% c()

  rows <- list()
  for (i in seq_along(consts)) {
    cst <- consts[[i]]
    c_name <- constraint_name(cst)
    # Optional remap: C_0 -> Items[1], C_1 -> Items[2], ...
    if (grepl("^C_[0-9]+$", c_name)) {
      idx <- suppressWarnings(as.integer(sub("^C_", "", c_name)))
      if (!is.na(idx) && (idx + 1) <= length(items)) {
        c_name <- as.character(items[[idx + 1]])
      }
    }
    rows[[length(rows) + 1]] <- list(
      Constraint = c_name,
      `Shadow Price` = constraint_shadow(cst),
      Slack = constraint_slack(cst)
    )
  }

  if (length(rows) == 0) {
    return(list(
      constraints = list(),
      top_bottleneck = NULL,
      insight = "No constraint data."
    ))
  }

  order_idx <- order(sapply(rows, function(x) abs(safe_numeric(x$`Shadow Price`, 0))), decreasing = TRUE)
  rows <- rows[order_idx]
  top <- rows[[1]]
  top_name <- as.character(top$Constraint %||% "Unknown")
  top_val <- abs(safe_numeric(top$`Shadow Price`, 0))

  list(
    constraints = rows,
    top_bottleneck = top_name,
    insight = sprintf("Bottleneck: %s (Shadow Price: %.4f)", top_name, top_val)
  )
}

process_general_sensitivity <- function(res) {
  consts <- res$constraints %||% list()
  rows <- list()

  for (cst in consts) {
    rows[[length(rows) + 1]] <- list(
      Constraint = constraint_name(cst),
      `Shadow Price` = constraint_shadow(cst),
      Slack = constraint_slack(cst)
    )
  }

  if (length(rows) == 0) {
    return(list(
      constraints = list(),
      top_bottleneck = NULL,
      insight = "No constraint data."
    ))
  }

  order_idx <- order(sapply(rows, function(x) abs(safe_numeric(x$`Shadow Price`, 0))), decreasing = TRUE)
  rows <- rows[order_idx]
  top <- rows[[1]]
  top_name <- as.character(top$Constraint %||% "Unknown")

  list(
    constraints = rows,
    top_bottleneck = top_name,
    insight = sprintf("Top bottleneck: %s", top_name)
  )
}

process_scheduling_sensitivity <- function(res) {
  base <- process_general_sensitivity(res)
  rows <- base$constraints %||% list()
  if (length(rows) == 0) {
    return(base)
  }

  tight_count <- 0
  for (r in rows) {
    if (abs(safe_numeric(r$Slack, 0)) < 1e-9) {
      tight_count <- tight_count + 1
    }
  }

  base$insight <- sprintf(
    "Scheduling bottleneck: %s | Tight constraints: %d/%d",
    base$top_bottleneck %||% "Unknown",
    tight_count,
    length(rows)
  )
  base
}

process_resourcing_sensitivity <- function(res) {
  base <- process_general_sensitivity(res)
  rows <- base$constraints %||% list()
  if (length(rows) == 0) {
    return(base)
  }

  resource_rows <- list()
  for (r in rows) {
    cname <- tolower(as.character(r$Constraint %||% ""))
    if (grepl("cpu|ram|capacity|resource", cname)) {
      resource_rows[[length(resource_rows) + 1]] <- r
    }
  }

  if (length(resource_rows) > 0) {
    top_resource <- resource_rows[[1]]
    base$insight <- sprintf(
      "Resource bottleneck: %s (Shadow Price: %.4f)",
      top_resource$Constraint %||% "Unknown",
      abs(safe_numeric(top_resource$`Shadow Price`, 0))
    )
  }

  base
}

process_nlp_sensitivity <- function(res) {
  base <- process_general_sensitivity(res)
  rows <- base$constraints %||% list()
  if (length(rows) == 0) {
    return(base)
  }

  active_duals <- 0
  for (r in rows) {
    if (abs(safe_numeric(r$`Shadow Price`, 0)) > 1e-9) {
      active_duals <- active_duals + 1
    }
  }

  base$insight <- sprintf(
    "NLP sensitivity summary: %d/%d constraints have active dual impact. Top: %s",
    active_duals,
    length(rows),
    base$top_bottleneck %||% "Unknown"
  )
  base
}

process_sensitivity <- function(res, store, mode = NULL) {
  mode <- normalize_mode(mode)
  
  if (!("lp_sensitivity" %in% names(res)) || is.null(res$lp_sensitivity)) {
    return(list(
      constraints = list(),
      top_bottleneck = NULL,
      insight = "Sensitivity available only for LP/CG models."
    ))
  }

  if (mode == "cutting") {
    return(process_cutting_sensitivity(res, store))
  }

  if (mode == "scheduling") {
    return(process_scheduling_sensitivity(res))
  }

  if (mode == "resourcing") {
    return(process_resourcing_sensitivity(res))
  }

  if (mode == "nlp") {
    return(process_nlp_sensitivity(res))
  }

  process_general_sensitivity(res)
}

# ============================================================================
# DECISION ANALYTICS (RUN HISTORY)
# ============================================================================

process_decision_analytics <- function(run_results,
                                       mode = NULL,
                                       confidence = 0.95,
                                       n_boot = 1000,
                                       seed = 42) {
  analyze_run_history(
    run_results = run_results,
    mode = normalize_mode(mode),
    confidence = confidence,
    n_boot = n_boot,
    seed = seed
  )
}

compare_solver_performance <- function(run_results,
                                       solver_labels,
                                       mode = NULL,
                                       confidence = 0.95,
                                       n_boot = 1000,
                                       seed = 42) {
  compare_solver_variants(
    run_results = run_results,
    solver_labels = solver_labels,
    mode = normalize_mode(mode),
    confidence = confidence,
    n_boot = n_boot,
    seed = seed
  )
}

build_executive_summary <- function(processed_result = NULL,
                                    sensitivity = NULL,
                                    decision_analytics = NULL) {
  lines <- c()

  if (is.list(processed_result)) {
    mode <- as.character(processed_result$mode %||% "generic")
    status <- as.character(processed_result$status %||% "unknown")
    objective <- safe_numeric(processed_result$objective_value %||% processed_result$total_value %||% processed_result$total_distance, NA_real_)
    lines <- c(lines, sprintf("Mode: %s", mode))
    lines <- c(lines, sprintf("Status: %s", status))
    if (is.finite(objective)) {
      lines <- c(lines, sprintf("Primary objective metric: %.4f", objective))
    }
  }

  if (is.list(sensitivity)) {
    insight <- as.character(sensitivity$insight %||% "No sensitivity insight")
    lines <- c(lines, sprintf("Sensitivity insight: %s", insight))
  }

  if (is.list(decision_analytics)) {
    feasible_rate <- safe_numeric(decision_analytics$feasible_rate, NA_real_)
    recommendation <- as.character(decision_analytics$recommendation %||% "No recommendation")
    run_count <- as.integer(decision_analytics$run_count %||% 0)
    lines <- c(lines, sprintf("Observed runs: %d", run_count))
    if (is.finite(feasible_rate)) {
      lines <- c(lines, sprintf("Feasible rate: %.2f%%", feasible_rate * 100.0))
    }
    lines <- c(lines, sprintf("Decision recommendation: %s", recommendation))
  }

  if (length(lines) == 0) {
    return("No report inputs provided")
  }

  paste(lines, collapse = "\n")
}
