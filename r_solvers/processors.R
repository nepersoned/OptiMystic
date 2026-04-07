# Result processing and domain-specific handlers
# Migrated from python_solvers/utils/services.py

source("utils.R")
source("plotting.R")

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
# DOMAIN-SPECIFIC PROCESSORS
# ============================================================================

# Cutting domain processor
process_cutting_results <- function(res, store) {
  params <- parameter_map(store)
  
  items <- params$Items %||% c()
  lens <- params$ItemLens %||% c()
  stocks <- params$Stocks %||% list()
  kerf <- safe_numeric(params$Kerf, 0)
  
  # Basic implementation: extract bin assignments from variables
  raw_bins <- list()
  total_cost <- 0.0
  total_waste <- 0.0
  
  if (!is.list(res$variables) || length(res$variables) == 0) {
    return(list(
      mode = "cutting",
      total_cost = 0.0,
      total_waste = 0.0,
      num_bins = 0,
      bin_plans = list(),
      report = "No cutting plan generated.",
      item_counts = list(),
      status = "no_solution"
    ))
  }
  
  # Parse variables (simplified)
  for (v in res$variables) {
    value <- get_variable_value(v)
    if (value <= 0.001) {
      next
    }
    # Variable parsing logic - placeholder for extension
  }
  
  # Summarize results
  list(
    mode = "cutting",
    total_cost = round(total_cost, 2),
    total_waste = round(total_waste, 2),
    num_bins = length(raw_bins),
    bin_plans = list(),
    report = sprintf("Bins used: %d, Total cost: $%.2f", length(raw_bins), total_cost),
    item_counts = list(),
    status = "ok"
  )
}

# Packing domain processor
process_packing_results <- function(res, store) {
  params <- parameter_map(store)
  
  items <- params$Items %||% c()
  weights <- params$Weights %||% c()
  values <- params$Values %||% c()
  capacity <- safe_numeric(params$Capacity, 0)
  
  var_values <- list()
  if (is.list(res$variables)) {
    for (v in res$variables) {
      var_name <- get_variable_name(v)
      var_values[[var_name]] <- get_variable_value(v)
    }
  }
  
  selected <- list()
  used <- 0.0
  total_value <- 0.0
  
  for (i in seq_along(items)) {
    qty <- safe_numeric(var_values[[sprintf("X_%d", i - 1)]], 0.0)
    if (qty <= 0) {
      next
    }
    item_weight <- safe_numeric(
      if (i <= length(weights)) weights[[i]] else 0,
      0
    )
    item_value <- safe_numeric(
      if (i <= length(values)) values[[i]] else 0,
      0
    )
    
    selected[[length(selected) + 1]] <- list(
      item = items[[i]],
      count = qty,
      weight = item_weight,
      value = item_value
    )
    
    used <- used + item_weight * qty
    total_value <- total_value + item_value * qty
  }
  
  usage_pct <- if (capacity > 0) (used / capacity * 100) else 0
  
  list(
    mode = "packing",
    total_value = round(total_value, 2),
    used_capacity = round(used, 2),
    capacity = round(capacity, 2),
    items = selected,
    report = sprintf(
      "Total Value: %.2f\nUsed Capacity: %.2f / %.2f (%.1f%%)",
      total_value, used, capacity, usage_pct
    ),
    status = normalize_status(res$status)
  )
}

# VRP domain processor
process_vrp_results <- function(res, store) {
  routes <- res$routes %||% list()
  unserved <- res$unserved %||% list()
  total_distance <- safe_numeric(res$total_distance %||% res$objective, 0)
  num_vehicles <- length(routes)
  
  list(
    mode = "vrp",
    total_distance = round(total_distance, 2),
    num_vehicles = num_vehicles,
    routes = routes,
    unserved = unserved,
    report = sprintf(
      "Total Distance: %.2f\nVehicles Used: %d\nUnserved: %d",
      total_distance, num_vehicles, length(unserved)
    ),
    status = res$status %||% "unknown"
  )
}

# Resourcing domain processor
process_resourcing_results <- function(res, store) {
  params <- parameter_map(store)
  
  items <- params$Items %||% c()
  weights <- params$Weights %||% c()
  cap <- safe_numeric(params$Capacity, 0)
  values <- params$Values %||% c()
  
  var_values <- list()
  if (is.list(res$variables)) {
    for (v in res$variables) {
      var_name <- get_variable_name(v)
      var_values[[var_name]] <- get_variable_value(v)
    }
  }
  
  selected <- list()
  used <- 0.0
  total_value <- 0.0
  
  for (i in seq_along(items)) {
    qty <- safe_numeric(var_values[[sprintf("X_%d", i - 1)]], 0.0)
    if (qty <= 0) {
      next
    }
    
    item_weight <- safe_numeric(if (i <= length(weights)) weights[[i]] else 0, 0)
    item_value <- safe_numeric(if (i <= length(values)) values[[i]] else 0, 0)
    
    selected[[length(selected) + 1]] <- list(
      item = items[[i]],
      count = qty,
      capacity_used = item_weight,
      value = item_value
    )
    
    used <- used + item_weight * qty
    total_value <- total_value + item_value * qty
  }
  
  usage_pct <- if (cap > 0) (used / cap * 100) else 0
  
  list(
    mode = "resourcing",
    total_value = round(total_value, 2),
    used_capacity = round(used, 2),
    capacity = round(cap, 2),
    items = selected,
    report = sprintf(
      "Total Value: %.2f\nCapacity Used: %.2f / %.2f (%.1f%%)",
      total_value, used, cap, usage_pct
    ),
    status = normalize_status(res$status)
  )
}

# Scheduling domain processor
process_scheduling_results <- function(res, store) {
  params <- parameter_map(store)
  
  items <- params$Items %||% c()
  shifts <- params$Shifts %||% list()
  if (length(shifts) == 0) {
    shifts <- names(params$Demands %||% list())
  }
  
  var_values <- list()
  if (is.list(res$variables)) {
    for (v in res$variables) {
      var_name <- get_variable_name(v)
      var_values[[var_name]] <- get_variable_value(v)
    }
  }
  
  assignments <- list()
  shift_counts <- sapply(shifts, function(s) 0)
  
  for (s_idx in seq_along(shifts)) {
    for (e_idx in seq_along(items)) {
      var_name <- sprintf("Assign_%d_%d", e_idx - 1, s_idx - 1)
      val <- safe_numeric(var_values[[var_name]], 0.0)
      if (val <= 0) {
        next
      }
      
      assignments[[length(assignments) + 1]] <- list(
        employee = items[[e_idx]],
        shift = shifts[[s_idx]],
        value = val
      )
      
      shift_counts[[s_idx]] <- shift_counts[[s_idx]] + round(val)
    }
  }
  
  list(
    mode = "scheduling",
    shift_coverage = as.list(shift_counts),
    assignments = assignments,
    report = sprintf(
      "Total Assignments: %d\nShifts Covered: %d",
      length(assignments), length(shifts)
    ),
    status = normalize_status(res$status)
  )
}

# NLP domain processor
process_nlp_results <- function(res, store) {
  params <- parameter_map(store)
  
  variables <- res$variables %||% list()
  constraints <- res$constraints %||% list()
  details <- res$details %||% list()
  
  active_vars <- list()
  for (v in variables) {
    value <- safe_numeric(v$Value %||% v$value, 0.0)
    if (abs(value) > 1e-9) {
      active_vars[[length(active_vars) + 1]] <- list(
        name = get_variable_name(v),
        value = value
      )
    }
  }
  
  list(
    mode = "nlp",
    status = tolower(res$status %||% "unknown"),
    objective_value = safe_numeric(res$objective, 0),
    variable_count = length(variables),
    constraint_count = length(constraints),
    active_variables = active_vars,
    ga_hotspot_count = as.integer(details$ga_hotspot_count %||% 0),
    report = sprintf(
      "Objective: %.2f, Variables: %d, Constraints: %d, GA Hotspots: %d",
      safe_numeric(res$objective, 0),
      length(variables),
      length(constraints),
      as.integer(details$ga_hotspot_count %||% 0)
    )
  )
}

# Generic domain processor (fallback)
process_generic_results <- function(res, store) {
  params <- parameter_map(store)
  variables <- res$variables %||% list()
  
  active_vars <- list()
  for (v in variables) {
    value <- safe_numeric(v$Value %||% v$value, 0.0)
    if (abs(value) > 1e-6) {
      active_vars[[length(active_vars) + 1]] <- list(
        name = get_variable_name(v),
        value = value
      )
    }
  }
  
  list(
    mode = "generic",
    status = normalize_status(res$status),
    objective_value = safe_numeric(res$objective, 0),
    variable_count = length(variables),
    constraint_count = length(res$constraints %||% list()),
    active_variables = active_vars,
    report = sprintf(
      "Status: %s, Objective: %.2f, Variables: %d",
      tolower(res$status %||% "unknown"),
      safe_numeric(res$objective, 0),
      length(variables)
    )
  )
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
