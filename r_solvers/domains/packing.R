# Packing domain specialized processing and visualization
# Handles bin packing, capacity utilization, and item selection

source("plotting.R")

# ============================================================================
# PACKING-SPECIFIC RESULT PROCESSING
# ============================================================================

process_packing_extended <- function(result, store) {
  # Enhance process_packing_results with domain-specific analysis
  
  params <- parameter_map(store)
  
  items <- params$Items %||% c()
  weights <- params$Weights %||% c()
  values <- params$Values %||% c()
  capacity <- safe_numeric(params$Capacity, 0)
  
  # Parse selected items
  selected <- parse_packing_items(result, items, weights, values, capacity)
  
  # Calculate metrics
  metrics <- calculate_packing_metrics(selected, capacity)
  
  result$items_detail <- selected
  result$metrics <- metrics
  result$utilization <- list(
    capacity_used = metrics$used_capacity,
    capacity_total = capacity,
    usage_pct = metrics$usage_pct,
    value_per_unit = metrics$value_per_unit
  )
  
  result
}

# Parse selected items from variables
parse_packing_items <- function(result, items, weights, values, capacity) {
  selected <- list()
  
  if (!is.list(result$variables) || length(result$variables) == 0) {
    return(selected)
  }
  
  for (v in result$variables) {
    var_name <- get_variable_name(v)
    qty <- get_variable_value(v)
    
    if (qty <= 0.001) next
    
    # Extract item index from variable name (X_i pattern)
    match <- regexpr("X_([0-9]+)", var_name)
    if (match > -1) {
      item_idx <- as.integer(strsplit(substring(var_name, match + 2), "[^0-9]")[[1]][1]) + 1
      
      if (item_idx > 0 && item_idx <= length(items)) {
        weight <- safe_numeric(if (item_idx <= length(weights)) weights[item_idx] else 0, 0)
        value <- safe_numeric(if (item_idx <= length(values)) values[item_idx] else 0, 0)
        
        selected[[length(selected) + 1]] <- list(
          item = items[item_idx],
          quantity = qty,
          weight = weight,
          value = value,
          total_weight = weight * qty,
          total_value = value * qty
        )
      }
    }
  }
  
  selected
}

# Calculate packing metrics
calculate_packing_metrics <- function(selected, capacity) {
  total_weight <- 0
  total_value <- 0
  item_count <- 0
  
  if (length(selected) > 0) {
    for (item in selected) {
      total_weight <- total_weight + safe_numeric(item$total_weight, 0)
      total_value <- total_value + safe_numeric(item$total_value, 0)
      item_count <- item_count + safe_numeric(item$quantity, 0)
    }
  }
  
  usage_pct <- if (capacity > 0) (total_weight / capacity * 100) else 0
  value_per_unit <- if (total_weight > 0) (total_value / total_weight) else 0
  
  list(
    used_capacity = round(total_weight, 2),
    total_capacity = round(capacity, 2),
    usage_pct = round(usage_pct, 2),
    total_value = round(total_value, 2),
    item_count = item_count,
    value_per_unit = round(value_per_unit, 4),
    items_selected = length(selected)
  )
}

# ============================================================================
# PACKING-SPECIFIC VISUALIZATIONS
# ============================================================================

plot_packing_utilization <- function(result, title = "Capacity Utilization") {
  util <- result$utilization %||% list()
  
  if (is.null(util$usage_pct)) {
    warning("No utilization data available")
    return(NULL)
  }
  
  used_pct <- util$usage_pct %||% 0
  unused_pct <- 100 - used_pct
  
  df <- data.frame(
    Category = c("Used", "Available"),
    Percentage = c(used_pct, unused_pct),
    stringsAsFactors = FALSE
  )
  
  ggplot(df, aes(x = "", y = Percentage, fill = Category)) +
    geom_bar(stat = "identity", width = 1) +
    coord_polar("y", start = 0) +
    scale_fill_manual(values = c("Used" = "#3498db", "Available" = "#ecf0f1")) +
    labs(
      title = title,
      subtitle = sprintf("Used: %.1f%%  |  Capacity: %.2f / %.2f",
        used_pct, util$capacity_used, util$capacity_total)
    ) +
    theme_minimal() +
    theme(
      plot.title = element_text(face = "bold", size = 14),
      axis.text = element_blank(),
      axis.ticks = element_blank(),
      panel.grid = element_blank()
    )
}

plot_packing_items <- function(result, top_n = 10, title = "selected Items by Value") {
  items_detail <- result$items_detail %||% list()
  
  if (length(items_detail) == 0) {
    warning("No item data available")
    return(NULL)
  }
  
  df <- do.call(rbind, lapply(items_detail, function(item) {
    data.frame(
      Item = item$item,
      Quantity = item$quantity,
      Value = item$total_value,
      stringsAsFactors = FALSE
    )
  }))
  
  df <- df %>%
    arrange(desc(Value)) %>%
    slice(1:min(top_n, nrow(df)))
  
  ggplot(df, aes(x = reorder(Item, Value), y = Value, fill = Item)) +
    geom_bar(stat = "identity") +
    coord_flip() +
    labs(
      title = title,
      x = "Item",
      y = "Total Value ($)",
      subtitle = sprintf("Total: $%.2f from %d items", sum(df$Value), sum(df$Quantity))
    ) +
    theme_minimal() +
    theme(
      plot.title = element_text(face = "bold", size = 14),
      legend.position = "none"
    )
}

# Main dispatcher for packing plots
plot_packing <- function(result, plot_type = "utilization") {
  switch(plot_type,
    "utilization" = plot_packing_utilization(result),
    "items" = plot_packing_items(result),
    "all" = list(
      utilization = plot_packing_utilization(result),
      items = plot_packing_items(result)
    ),
    NULL
  )
}
