# Scheduling domain processing

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
