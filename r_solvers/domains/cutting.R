# Cutting domain specialized processing and visualization
# Handles bin packing, scrap optimization, and cutting patterns

source("plotting.R")

# ============================================================================
# CUTTING-SPECIFIC RESULT PROCESSING
# ============================================================================

process_cutting_extended <- function(result, store) {
  # This function enhances process_cutting_results with domain-specific analysis
  
  params <- parameter_map(store)
  
  # Extract items and stocks
  items <- params$Items %||% c()
  lens <- params$ItemLens %||% c()
  stocks <- params$Stocks %||% list()
  kerf <- safe_numeric(params$Kerf, 0)
  
  # Parse bins from result
  bins <- parse_cutting_bins(result, items, lens)
  
  # Calculate metrics
  metrics <- calculate_cutting_metrics(bins, stocks, kerf)
  
  # Build extended result
  result$bins_detail <- bins
  result$metrics <- metrics
  result$efficiency <- list(
    material_efficiency = metrics$material_efficiency,
    total_waste_pct = metrics$waste_pct
  )
  
  result
}

# Parse cutting bins from variables
parse_cutting_bins <- function(result, items, lens) {
  bins <- list()
  
  if (!is.list(result$variables) || length(result$variables) == 0) {
    return(bins)
  }
  
  # Simple parsing: extract bin IDs and item assignments
  for (v in result$variables) {
    var_name <- get_variable_name(v)
    value <- get_variable_value(v)
    
    if (value <= 0.001) next
    
    # Pattern: Cut_Item_BinID or A_IT_*_STx
    if (grepl("^Cut_", var_name)) {
      parts <- strsplit(var_name, "_")[[1]]
      if (length(parts) >= 2) {
        bin_id <- tail(parts, 1)
        item_name <- paste(parts[-c(1, length(parts))], collapse = "_")
        
        if (!(bin_id %in% names(bins))) {
          bins[[bin_id]] <- list(items = c(), total_length = 0)
        }
        
        item_idx <- which(items == item_name)
        if (length(item_idx) > 0 && item_idx <= length(lens)) {
          bins[[bin_id]]$items <- c(bins[[bin_id]]$items, item_name)
          bins[[bin_id]]$total_length <- bins[[bin_id]]$total_length + lens[item_idx] * value
        }
      }
    }
  }
  
  bins
}

# Calculate cutting metrics
calculate_cutting_metrics <- function(bins, stocks, kerf = 0) {
  if (length(bins) == 0) {
    return(list(
      total_material_cost = 0,
      total_waste = 0,
      material_efficiency = 0,
      waste_pct = 100,
      avg_bin_usage = 0
    ))
  }
  
  total_cost <- 0
  total_waste <- 0
  total_usage <- 0
  total_capacity <- 0
  
  for (i in seq_along(bins)) {
    stock_idx <- min(i, length(stocks))
    if (stock_idx > 0 && stock_idx <= length(stocks)) {
      stock <- stocks[[stock_idx]]
      stock_length <- safe_numeric(stock$Length %||% stock$length, 0)
      stock_cost <- safe_numeric(stock$Cost %||% stock$cost, 0)
      
      bin_usage <- safe_numeric(bins[[i]]$total_length, 0)
      bin_waste <- max(0, stock_length - bin_usage)
      
      total_cost <- total_cost + stock_cost
      total_waste <- total_waste + bin_waste
      total_usage <- total_usage + bin_usage
      total_capacity <- total_capacity + stock_length
    }
  }
  
  efficiency <- if (total_capacity > 0) (total_usage / total_capacity) else 0
  waste_pct <- if (total_capacity > 0) (total_waste / total_capacity * 100) else 100
  
  list(
    total_material_cost = round(total_cost, 2),
    total_waste = round(total_waste, 2),
    material_efficiency = round(efficiency * 100, 2),
    waste_pct = round(waste_pct, 2),
    avg_bin_usage = if (length(bins) > 0) round(total_usage / length(bins), 2) else 0,
    num_bins = length(bins)
  )
}

# ============================================================================
# CUTTING-SPECIFIC VISUALIZATIONS
# ============================================================================

plot_cutting_efficiency <- function(result, title = "Cutting Efficiency") {
  if (is.null(result$efficiency)) {
    warning("No efficiency data available")
    return(NULL)
  }
  
  efficiency <- result$efficiency$material_efficiency %||% 0
  waste <- result$efficiency$total_waste_pct %||% 100
  
  df <- data.frame(
    Category = c("Material Used", "Waste/Scrap"),
    Percentage = c(efficiency, waste),
    stringsAsFactors = FALSE
  )
  
  ggplot(df, aes(x = Category, y = Percentage, fill = Category)) +
    geom_bar(stat = "identity") +
    scale_fill_manual(values = c("Material Used" = "#3498db", "Waste/Scrap" = "#e74c3c"), guide = "none") +
    labs(
      title = title,
      x = "",
      y = "Percentage (%)",
      subtitle = sprintf("Efficiency: %.1f%%", efficiency)
    ) +
    ylim(0, 100) +
    theme_minimal() +
    theme(
      plot.title = element_text(face = "bold", size = 14),
      axis.text.x = element_text(size = 11, face = "bold")
    )
}

plot_cutting_cost <- function(result, title = "Material Cost Breakdown") {
  metrics <- result$metrics %||% list()
  
  if (is.null(metrics$total_material_cost)) {
    warning("No cost data available")
    return(NULL)
  }
  
  cost <- metrics$total_material_cost %||% 0
  waste <- metrics$total_waste %||% 0
  
  df <- data.frame(
    Item = c("Material Cost", "Waste Value"),
    Amount = c(cost, waste * 0.1),  # Assume 10% waste value
    stringsAsFactors = FALSE
  )
  
  ggplot(df, aes(x = reorder(Item, Amount), y = Amount, fill = Item)) +
    geom_bar(stat = "identity") +
    scale_fill_manual(values = c("Material Cost" = "#27ae60", "Waste Value" = "#f39c12"), guide = "none") +
    coord_flip() +
    labs(
      title = title,
      x = "",
      y = "Cost / Value ($)",
      subtitle = sprintf("Total Cost: $%.2f", cost)
    ) +
    theme_minimal() +
    theme(
      plot.title = element_text(face = "bold", size = 14),
      axis.text.x = element_text(size = 10)
    )
}

# Main dispatcher for cutting plots
plot_cutting <- function(result, plot_type = "efficiency") {
  switch(plot_type,
    "efficiency" = plot_cutting_efficiency(result),
    "cost" = plot_cutting_cost(result),
    "all" = list(
      efficiency = plot_cutting_efficiency(result),
      cost = plot_cutting_cost(result)
    ),
    NULL
  )
}
