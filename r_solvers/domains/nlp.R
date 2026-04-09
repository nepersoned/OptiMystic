# NLP domain processing

process_nlp_results <- function(res, store) {
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
