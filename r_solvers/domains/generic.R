# Generic domain fallback processing

process_generic_results <- function(res, store) {
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
