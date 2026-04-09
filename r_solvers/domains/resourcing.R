# Resourcing domain processing

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
