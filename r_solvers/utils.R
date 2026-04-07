# R utilities for OptiMystic result processing
# Migrated from python_solvers/utils/services.py

library(jsonlite)

`%||%` <- function(lhs, rhs) {
  if (is.null(lhs) || (length(lhs) == 0)) {
    return(rhs)
  }
  lhs
}

# Safe numeric conversion with default fallback
safe_numeric <- function(x, default = 0.0) {
  if (is.null(x) || is.na(x)) {
    return(default)
  }
  tryCatch(
    {
      as.numeric(x)
    },
    error = function(e) {
      default
    }
  )
}

# Mode/domain normalization
MODE_ALIASES <- list(
  "manufacturing" = "cutting",
  "cutting" = "cutting",
  "logistics" = "packing",
  "packing" = "packing",
  "vrp" = "vrp",
  "routing" = "vrp",
  "vehicle_routing" = "vrp",
  "resource" = "resourcing",
  "it" = "resourcing",
  "cloud" = "resourcing",
  "resource_allocation" = "resourcing",
  "resourcing" = "resourcing",
  "hr" = "scheduling",
  "nsp" = "scheduling",
  "scheduling" = "scheduling",
  "generic" = "generic",
  "formula" = "generic",
  "custom" = "generic",
  "nlp" = "nlp"
)

normalize_mode <- function(mode = NULL) {
  if (is.null(mode) || mode == "") {
    mode <- "cutting"
  } else {
    mode <- tolower(trimws(as.character(mode)))
  }
  return(MODE_ALIASES[[mode]] %||% mode)
}

# Parameter map helper
parameter_map <- function(store) {
  if (!is.list(store)) {
    return(list())
  }
  
  params <- store$parameters %||% list()
  
  # If params is already a list of named fields
  if (is.list(params) && !is.null(names(params))) {
    return(params)
  }
  
  # If params is a list of objects with "name" field, convert to named list
  if (is.list(params) && length(params) > 0) {
    mapped <- list()
    for (item in params) {
      if (is.list(item) && !is.null(item$name)) {
        mapped[[item$name]] <- item$data
      }
    }
    if (length(mapped) > 0) {
      return(mapped)
    }
  }
  
  return(list())
}

# Clean variable names (replace special chars with underscore)
clean_name <- function(name) {
  gsub("[^a-zA-Z0-9]", "_", as.character(name))
}

# Get variable name from parsed variable
get_variable_name <- function(variable) {
  if (!is.list(variable)) {
    return("")
  }
  return(as.character(variable$Variable %||% variable$name %||% ""))
}

# Get variable value from parsed variable
get_variable_value <- function(variable) {
  if (!is.list(variable)) {
    return(0.0)
  }
  return(safe_numeric(variable$Value %||% variable$value %||% 0.0, 0.0))
}
