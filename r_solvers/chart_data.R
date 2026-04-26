# ECharts-compatible chart data builders
# Returns pure list structures serializable to JSON via jsonlite::toJSON
# Frontend (ECharts/Recharts) consumes these directly — no ggplot objects here.

source("utils.R")

# ── helpers ─────────────────────────────────────────────────────────────────

.pct <- function(num, denom, digits = 1) {
  if (is.null(denom) || is.na(denom) || abs(safe_numeric(denom, 0)) < 1e-12) return(NA_real_)
  round(safe_numeric(num, 0) / safe_numeric(denom, 1) * 100, digits)
}

.delta_pct <- function(current, previous, digits = 1) {
  c <- safe_numeric(current, NA_real_)
  p <- safe_numeric(previous, NA_real_)
  if (!is.finite(c) || !is.finite(p) || abs(p) < 1e-12) return(NA_real_)
  round((c - p) / abs(p) * 100, digits)
}

.bar <- function(categories, ...) {
  # ...: named series vectors, e.g. Distance = c(10, 20), Stops = c(2, 3)
  args <- list(...)
  series <- lapply(names(args), function(nm) list(name = nm, data = as.list(args[[nm]])))
  list(categories = as.list(categories), series = series)
}

.pie <- function(...) {
  # ...: named values, e.g. Served = 8, Unserved = 2
  args <- list(...)
  lapply(names(args), function(nm) list(name = nm, value = unname(args[[nm]])))
}

# ── sensitivity (common) ─────────────────────────────────────────────────────

sensitivity_chart_data <- function(sensitivity) {
  if (!is.list(sensitivity) || length(sensitivity$constraints %||% list()) == 0) {
    return(list(shadow_price_bar = NULL, top_bottleneck = NULL, insight = NULL))
  }
  consts <- sensitivity$constraints
  cats <- sapply(consts, function(c) as.character(c$Constraint %||% "Unknown"))
  shadows <- round(sapply(consts, function(c) safe_numeric(c$`Shadow Price`, 0)), 4)
  slacks  <- round(sapply(consts, function(c) safe_numeric(c$Slack, 0)), 4)
  list(
    shadow_price_bar = .bar(cats, `Shadow Price` = shadows, Slack = slacks),
    top_bottleneck   = sensitivity$top_bottleneck %||% NULL,
    insight          = sensitivity$insight %||% NULL
  )
}

# ── VRP ─────────────────────────────────────────────────────────────────────

chart_data_vrp <- function(pr) {
  routes   <- pr$routes %||% list()
  unserved <- pr$unserved %||% list()
  total_dist <- safe_numeric(pr$total_distance, 0)
  n_vehicles <- length(routes)

  route_labels <- character(0)
  distances    <- numeric(0)
  stops        <- integer(0)

  for (i in seq_along(routes)) {
    r <- routes[[i]]
    route_labels[i] <- sprintf("Route %d", i)
    distances[i]    <- safe_numeric(r$distance, 0)
    stops[i]        <- length(r$route %||% r$nodes %||% r$locations %||% list())
  }

  served <- sum(stops)
  total_nodes <- served + length(unserved)
  cov_pct <- .pct(served, total_nodes)

  list(
    domain = "vrp",
    kpi = list(
      total_distance       = round(total_dist, 2),
      vehicles_used        = n_vehicles,
      coverage_pct         = if (is.finite(cov_pct)) cov_pct else NULL,
      avg_distance_vehicle = if (n_vehicles > 0) round(total_dist / n_vehicles, 2) else NULL,
      unserved_count       = length(unserved)
    ),
    route_bar = if (length(route_labels) > 0)
      .bar(route_labels, Distance = round(distances, 2), Stops = as.integer(stops))
    else NULL,
    coverage_pie = .pie(Served = served, Unserved = length(unserved))
  )
}

# ── Packing ─────────────────────────────────────────────────────────────────

chart_data_packing <- function(pr) {
  items      <- pr$items %||% list()
  total_val  <- safe_numeric(pr$total_value, 0)
  used_cap   <- safe_numeric(pr$used_capacity, 0)
  capacity   <- safe_numeric(pr$capacity, 0)
  util_pct   <- .pct(used_cap, capacity)

  item_names <- character(0)
  item_vals  <- numeric(0)

  for (it in items) {
    item_names <- c(item_names, as.character(it$name %||% it$Name %||% "Item"))
    item_vals  <- c(item_vals,  safe_numeric(it$value %||% it$Value, 0))
  }

  list(
    domain = "packing",
    kpi = list(
      total_value    = round(total_val, 2),
      utilization_pct = if (is.finite(util_pct)) util_pct else NULL,
      used_capacity  = round(used_cap, 2),
      capacity       = round(capacity, 2),
      items_packed   = length(items)
    ),
    utilization_gauge = list(
      value = if (is.finite(util_pct)) util_pct else 0,
      max   = 100
    ),
    items_bar = if (length(item_names) > 0)
      .bar(item_names, Value = round(item_vals, 2))
    else NULL
  )
}

# ── Cutting ─────────────────────────────────────────────────────────────────

chart_data_cutting <- function(pr) {
  bin_plans   <- pr$bin_plans %||% list()
  total_cost  <- safe_numeric(pr$total_cost, 0)
  total_waste <- safe_numeric(pr$total_waste, 0)
  num_bins    <- as.integer(pr$num_bins %||% length(bin_plans))

  bin_labels <- character(0)
  bin_used   <- numeric(0)
  bin_waste  <- numeric(0)

  for (i in seq_along(bin_plans)) {
    bp <- bin_plans[[i]]
    bin_labels[i] <- sprintf("Pattern %d", i)
    bin_used[i]   <- safe_numeric(bp$used %||% bp$length, 0)
    bin_waste[i]  <- safe_numeric(bp$waste, 0)
  }

  total_material <- total_waste + sum(bin_used)
  waste_pct <- .pct(total_waste, total_material)

  list(
    domain = "cutting",
    kpi = list(
      total_cost  = round(total_cost, 2),
      total_waste = round(total_waste, 2),
      waste_pct   = if (is.finite(waste_pct)) waste_pct else NULL,
      num_bins    = num_bins
    ),
    waste_bar = if (length(bin_labels) > 0)
      .bar(bin_labels, Used = round(bin_used, 2), Waste = round(bin_waste, 2))
    else NULL,
    cost_waste_pie = .pie(`Material Used` = round(total_material - total_waste, 2),
                          Waste = round(total_waste, 2))
  )
}

# ── Scheduling ───────────────────────────────────────────────────────────────

chart_data_scheduling <- function(pr) {
  assignments   <- pr$assignments %||% list()
  shift_coverage <- pr$shift_coverage %||% list()

  shift_names  <- names(shift_coverage)
  shift_counts <- sapply(shift_names, function(s) as.integer(shift_coverage[[s]] %||% 0))

  # Gantt-ready rows: {task, resource, start, end}
  gantt_rows <- list()
  for (a in assignments) {
    gantt_rows[[length(gantt_rows) + 1]] <- list(
      task     = as.character(a$shift    %||% "Shift"),
      resource = as.character(a$employee %||% "Worker"),
      value    = safe_numeric(a$value, 1)
    )
  }

  total_assignments <- length(assignments)
  shifts_with_staff <- sum(shift_counts > 0)

  list(
    domain = "scheduling",
    kpi = list(
      total_assignments  = total_assignments,
      shifts_covered     = shifts_with_staff,
      total_shifts       = length(shift_names),
      coverage_pct       = .pct(shifts_with_staff, length(shift_names))
    ),
    shift_coverage_bar = if (length(shift_names) > 0)
      .bar(shift_names, Assigned = as.integer(shift_counts))
    else NULL,
    gantt = gantt_rows
  )
}

# ── Resourcing ───────────────────────────────────────────────────────────────

chart_data_resourcing <- function(pr) {
  items    <- pr$items %||% list()
  used_cpu <- safe_numeric(pr$used_cpu, 0)
  used_ram <- safe_numeric(pr$used_ram, 0)
  cap_cpu  <- safe_numeric(pr$capacity_cpu, 0)
  cap_ram  <- safe_numeric(pr$capacity_ram, 0)

  item_names <- sapply(items, function(i) as.character(i$name %||% i$Name %||% "Item"))
  item_vals  <- sapply(items, function(i) safe_numeric(i$value %||% i$Value, 0))

  list(
    domain = "resourcing",
    kpi = list(
      total_value  = round(safe_numeric(pr$total_value, 0), 2),
      cpu_util_pct = .pct(used_cpu, cap_cpu),
      ram_util_pct = .pct(used_ram, cap_ram),
      items_placed = length(items)
    ),
    resource_bar = .bar(
      c("CPU", "RAM"),
      Used     = c(round(used_cpu, 2), round(used_ram, 2)),
      Capacity = c(round(cap_cpu, 2),  round(cap_ram, 2))
    ),
    items_bar = if (length(item_names) > 0)
      .bar(item_names, Value = round(item_vals, 2))
    else NULL
  )
}

# ── NLP / Generic ────────────────────────────────────────────────────────────

chart_data_nlp <- function(pr) {
  active_vars <- pr$active_variables %||% list()
  var_names   <- sapply(active_vars, function(v) as.character(v$name %||% "var"))
  var_vals    <- sapply(active_vars, function(v) safe_numeric(v$value, 0))

  list(
    domain = "nlp",
    kpi = list(
      objective_value      = safe_numeric(pr$objective_value, NA_real_),
      variable_count       = as.integer(pr$variable_count %||% 0),
      active_variable_count = length(active_vars),
      constraint_count     = as.integer(pr$constraint_count %||% 0)
    ),
    variables_bar = if (length(var_names) > 0)
      .bar(var_names, Value = round(var_vals, 4))
    else NULL
  )
}

chart_data_generic <- function(pr) {
  active_vars <- pr$active_variables %||% list()
  var_names   <- sapply(active_vars, function(v) as.character(v$name %||% "var"))
  var_vals    <- sapply(active_vars, function(v) safe_numeric(v$value, 0))

  list(
    domain = "generic",
    kpi = list(
      objective_value = safe_numeric(pr$objective_value, NA_real_),
      variable_count  = as.integer(pr$variable_count %||% 0),
      active_variable_count = length(active_vars)
    ),
    variables_bar = if (length(var_names) > 0)
      .bar(var_names, Value = round(var_vals, 4))
    else NULL
  )
}

# ── Main dispatcher ──────────────────────────────────────────────────────────

build_chart_data <- function(processed_result, sensitivity = NULL, mode = NULL) {
  mode <- normalize_mode(mode %||% as.character(processed_result$mode %||% "generic"))

  domain_data <- switch(mode,
    "vrp"        = chart_data_vrp(processed_result),
    "packing"    = chart_data_packing(processed_result),
    "cutting"    = chart_data_cutting(processed_result),
    "scheduling" = chart_data_scheduling(processed_result),
    "resourcing" = chart_data_resourcing(processed_result),
    "nlp"        = chart_data_nlp(processed_result),
    chart_data_generic(processed_result)
  )

  domain_data$sensitivity = sensitivity_chart_data(sensitivity)
  domain_data
}

# ── Structured executive summary ─────────────────────────────────────────────

build_executive_summary_structured <- function(processed_result = NULL,
                                               sensitivity = NULL,
                                               decision_analytics = NULL) {
  mode      <- "generic"
  status    <- "unknown"
  objective <- NA_real_

  if (is.list(processed_result)) {
    mode      <- as.character(processed_result$mode %||% "generic")
    status    <- as.character(processed_result$status %||% "unknown")
    objective <- safe_numeric(
      processed_result$objective_value %||%
      processed_result$total_value %||%
      processed_result$total_distance %||%
      processed_result$objective,
      NA_real_
    )
  }

  feasible <- tolower(status) %in% c("ok", "optimal", "feasible")

  # KPI delta from run history
  kpi_deltas <- list()
  delta_pct  <- NA_real_
  run_table  <- NULL

  if (is.list(decision_analytics)) {
    run_table <- decision_analytics$run_table
  }

  if (is.data.frame(run_table) && nrow(run_table) >= 2 && is.finite(objective)) {
    prev_obj <- safe_numeric(run_table$objective[[nrow(run_table) - 1]], NA_real_)
    delta_pct <- .delta_pct(objective, prev_obj)
    if (is.finite(delta_pct)) {
      kpi_deltas[[1]] <- list(
        metric    = "Objective",
        current   = round(objective, 4),
        previous  = round(prev_obj, 4),
        delta_pct = delta_pct
      )
    }
  }

  # Domain-specific KPI line
  domain_kpi_line <- ""
  if (is.list(processed_result)) {
    if (mode == "vrp") {
      domain_kpi_line <- sprintf("Total distance: %.2f | Vehicles: %d",
        safe_numeric(processed_result$total_distance, 0),
        length(processed_result$routes %||% list()))
    } else if (mode == "packing") {
      domain_kpi_line <- sprintf("Total value: %.2f | Items packed: %d",
        safe_numeric(processed_result$total_value, 0),
        length(processed_result$items %||% list()))
    } else if (mode == "cutting") {
      domain_kpi_line <- sprintf("Cost: %.2f | Waste: %.2f | Bins: %d",
        safe_numeric(processed_result$total_cost, 0),
        safe_numeric(processed_result$total_waste, 0),
        as.integer(processed_result$num_bins %||% 0))
    } else if (mode == "scheduling") {
      domain_kpi_line <- sprintf("Assignments: %d | Shifts: %d",
        length(processed_result$assignments %||% list()),
        length(processed_result$shift_coverage %||% list()))
    }
  }

  # Headline
  headline <- sprintf("[%s] %s | Objective: %s",
    toupper(mode),
    toupper(status),
    if (is.finite(objective)) sprintf("%.4f", objective) else "N/A"
  )
  if (is.finite(delta_pct)) {
    dir_word <- if (delta_pct < 0) "improved" else "worsened"
    headline <- sprintf("%s | %.1f%% %s vs previous run", headline, abs(delta_pct), dir_word)
  }

  bottleneck   <- sensitivity$top_bottleneck %||% NULL
  insight      <- sensitivity$insight %||% NULL
  feasible_rate <- NA_real_
  run_count     <- 0L
  recommendation <- NULL

  if (is.list(decision_analytics)) {
    feasible_rate  <- safe_numeric(decision_analytics$feasible_rate, NA_real_)
    run_count      <- as.integer(decision_analytics$run_count %||% 0L)
    recommendation <- as.character(decision_analytics$recommendation %||% "")
  }

  list(
    headline       = headline,
    mode           = mode,
    status         = status,
    feasible       = feasible,
    objective      = if (is.finite(objective)) round(objective, 4) else NULL,
    delta_pct      = if (is.finite(delta_pct)) delta_pct else NULL,
    domain_kpi_line = domain_kpi_line,
    kpi_deltas     = kpi_deltas,
    bottleneck     = bottleneck,
    insight        = insight,
    feasible_rate  = if (is.finite(feasible_rate)) round(feasible_rate, 4) else NULL,
    run_count      = run_count,
    recommendation = recommendation
  )
}
