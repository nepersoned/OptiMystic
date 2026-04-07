# Visualization functions for OptiMystic results
# Supports ggplot2 and plotly for interactive and publication-quality graphics

library(ggplot2)
library(dplyr)

# ============================================================================
# GENERIC PLOTTING UTILITIES
# ============================================================================

# Prepare data frame from processed results
prepare_df_generic <- function(result) {
  if (!is.list(result) || is.null(result$active_variables)) {
    return(data.frame())
  }
  
  vars <- result$active_variables
  if (length(vars) == 0) {
    return(data.frame())
  }
  
  do.call(rbind, lapply(vars, function(v) {
    data.frame(
      Variable = v$name,
      Value = v$value,
      stringsAsFactors = FALSE
    )
  }))
}

# ============================================================================
# SHARED PLOTTING FUNCTIONS
# ============================================================================

# Generic variable bar plot
plot_variables_bar <- function(result, top_n = 10, title = "Top Variables") {
  df <- prepare_df_generic(result)
  
  if (nrow(df) == 0) {
    warning("No active variables to plot")
    return(NULL)
  }
  
  df <- df %>%
    arrange(desc(abs(Value))) %>%
    slice(1:min(top_n, nrow(df)))
  
  ggplot(df, aes(x = reorder(Variable, Value), y = Value, fill = Value > 0)) +
    geom_bar(stat = "identity") +
    scale_fill_manual(values = c("TRUE" = "#2ecc71", "FALSE" = "#e74c3c"), guide = "none") +
    coord_flip() +
    labs(
      title = title,
      x = "Variable",
      y = "Value"
    ) +
    theme_minimal() +
    theme(
      plot.title = element_text(face = "bold", size = 14),
      axis.text.x = element_text(size = 10)
    )
}

# Objective value summary
plot_objective_summary <- function(result, title = "Objective Summary") {
  obj_value <- result$objective_value %||% 0
  status <- result$status %||% "Unknown"
  
  df <- data.frame(
    Metric = c("Objective", "Status"),
    Value = c(as.character(round(obj_value, 2)), status),
    stringsAsFactors = FALSE
  )
  
  # Return a text summary (for later enhancement with ggplot)
  list(
    objective = round(obj_value, 2),
    status = status,
    summary_text = sprintf("Status: %s\nObjective: %.2f", status, obj_value)
  )
}

# ============================================================================
# DOMAIN-SPECIFIC PLOT DISPATCHERS (stubs)
# ============================================================================

# These are called from domain-specific files
plot_cutting <- function(result, ...) {
  NULL  # Implemented in domains/cutting.R
}

plot_packing <- function(result, ...) {
  NULL  # Implemented in domains/packing.R
}

plot_vrp <- function(result, ...) {
  NULL  # Implemented in domains/vrp.R
}

plot_resourcing <- function(result, ...) {
  NULL  # Implemented in domains/resourcing.R
}

plot_scheduling <- function(result, ...) {
  NULL  # Implemented in domains/scheduling.R
}

plot_nlp <- function(result, ...) {
  NULL  # Implemented in domains/nlp.R
}
