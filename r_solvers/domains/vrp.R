# VRP (Vehicle Routing Problem) domain specialized processing and visualization
# Handles route optimization, distance analysis, and node coverage

source("plotting.R")

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

# ============================================================================
# VRP-SPECIFIC RESULT PROCESSING
# ============================================================================

process_vrp_extended <- function(result, store) {
  # Enhance process_vrp_results with domain-specific analysis
  
  params <- parameter_map(store)
  
  routes <- result$routes %||% list()
  unserved <- result$unserved %||% list()
  total_distance <- safe_numeric(result$total_distance %||% result$objective, 0)
  
  # Parse route details
  route_stats <- calculate_route_statistics(routes)
  
  # Calculate coverage
  coverage <- calculate_vrp_coverage(routes, unserved, params)
  
  result$route_stats <- route_stats
  result$coverage <- coverage
  result$summary <- list(
    total_distance = round(total_distance, 2),
    num_vehicles = length(routes),
    avg_distance_per_vehicle = if (length(routes) > 0) round(total_distance / length(routes), 2) else 0,
    coverage_pct = coverage$coverage_pct,
    unserved_count = length(unserved)
  )
  
  result
}

# Calculate route statistics
calculate_route_statistics <- function(routes) {
  if (!is.list(routes) || length(routes) == 0) {
    return(list(
      total_routes = 0,
      avg_stops = 0,
      avg_distance = 0
    ))
  }
  
  stats <- list()
  total_stops <- 0
  total_distance <- 0
  
  for (i in seq_along(routes)) {
    route <- routes[[i]]
    num_stops <- length(route$nodes %||% route$locations %||% c())
    distance <- safe_numeric(route$distance, 0)
    
    total_stops <- total_stops + num_stops
    total_distance <- total_distance + distance
    
    stats[[i]] <- list(
      route_id = i,
      num_stops = num_stops,
      distance = round(distance, 2),
      avg_distance_per_stop = if (num_stops > 0) round(distance / num_stops, 2) else 0
    )
  }
  
  list(
    routes_detail = stats,
    total_routes = length(routes),
    total_stops = total_stops,
    avg_stops_per_route = if (length(routes) > 0) round(total_stops / length(routes), 2) else 0,
    total_distance = round(total_distance, 2),
    avg_distance = if (length(routes) > 0) round(total_distance / length(routes), 2) else 0
  )
}

# Calculate VRP coverage metrics
calculate_vrp_coverage <- function(routes, unserved, params) {
  total_nodes <- params$num_nodes %||% params$Nodes %||% 0
  served <- 0
  
  if (is.list(routes) && length(routes) > 0) {
    for (route in routes) {
      nodes <- route$nodes %||% route$locations %||% c()
      served <- served + length(nodes)
    }
  }
  
  total_to_serve <- served + length(unserved)
  coverage_pct <- if (total_to_serve > 0) (served / total_to_serve * 100) else 0
  
  list(
    served_nodes = served,
    unserved_nodes = length(unserved),
    total_nodes = total_to_serve,
    coverage_pct = round(coverage_pct, 2)
  )
}

# ============================================================================
# VRP-SPECIFIC VISUALIZATIONS
# ============================================================================

plot_vrp_distance <- function(result, title = "Route Distance Analysis") {
  route_stats <- result$route_stats %||% list()
  routes_detail <- route_stats$routes_detail %||% list()
  
  if (length(routes_detail) == 0) {
    warning("No route data available")
    return(NULL)
  }
  
  df <- do.call(rbind, lapply(routes_detail, function(r) {
    data.frame(
      Route = sprintf("Route %d", r$route_id),
      Distance = r$distance,
      Stops = r$num_stops,
      stringsAsFactors = FALSE
    )
  }))
  
  ggplot(df, aes(x = reorder(Route, Distance), y = Distance, fill = Stops)) +
    geom_bar(stat = "identity") +
    scale_fill_gradient(low = "#3498db", high = "#e74c3c") +
    coord_flip() +
    labs(
      title = title,
      x = "Route",
      y = "Distance (km)",
      fill = "Stops",
      subtitle = sprintf("Total Distance: %.2f km", sum(df$Distance))
    ) +
    theme_minimal() +
    theme(
      plot.title = element_text(face = "bold", size = 14),
      legend.position = "right"
    )
}

plot_vrp_coverage <- function(result, title = "Node Coverage") {
  coverage <- result$coverage %||% list()
  
  if (is.null(coverage$coverage_pct)) {
    warning("No coverage data available")
    return(NULL)
  }
  
  served <- coverage$served_nodes %||% 0
  unserved <- coverage$unserved_nodes %||% 0
  
  df <- data.frame(
    Status = c("Served", "Unserved"),
    Count = c(served, unserved),
    stringsAsFactors = FALSE
  )
  
  ggplot(df, aes(x = Status, y = Count, fill = Status)) +
    geom_bar(stat = "identity") +
    scale_fill_manual(values = c("Served" = "#27ae60", "Unserved" = "#e74c3c"), guide = "none") +
    labs(
      title = title,
      x = "",
      y = "Number of Nodes",
      subtitle = sprintf("Coverage: %.1f%%", coverage$coverage_pct)
    ) +
    geom_text(aes(label = Count), vjust = -0.5, size = 4) +
    theme_minimal() +
    theme(
      plot.title = element_text(face = "bold", size = 14),
      axis.text.x = element_text(size = 11, face = "bold")
    )
}

plot_vrp_routes_summary <- function(result, title = "Routes Overview") {
  summary <- result$summary %||% list()
  
  if (is.null(summary$num_vehicles)) {
    warning("No summary data available")
    return(NULL)
  }
  
  df <- data.frame(
    Metric = c("Vehicles", "Total Distance", "Avg Distance/Vehicle"),
    Value = c(
      summary$num_vehicles,
      summary$total_distance,
      summary$avg_distance_per_vehicle
    ),
    stringsAsFactors = FALSE
  )
  
  ggplot(df, aes(x = Metric, y = Value, fill = Metric)) +
    geom_bar(stat = "identity") +
    coord_flip() +
    labs(
      title = title,
      x = "",
      y = "Value",
      subtitle = sprintf("Unserved: %d", summary$unserved_count)
    ) +
    theme_minimal() +
    theme(
      plot.title = element_text(face = "bold", size = 14),
      legend.position = "none"
    )
}

# Main dispatcher for VRP plots
plot_vrp <- function(result, plot_type = "distance") {
  switch(plot_type,
    "distance" = plot_vrp_distance(result),
    "coverage" = plot_vrp_coverage(result),
    "summary" = plot_vrp_routes_summary(result),
    "all" = list(
      distance = plot_vrp_distance(result),
      coverage = plot_vrp_coverage(result),
      summary = plot_vrp_routes_summary(result)
    ),
    NULL
  )
}
