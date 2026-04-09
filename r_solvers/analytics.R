# Advanced statistical diagnostics for OptiMystic solver outputs
# This module makes R a decision analytics layer, not just a plotting layer.

source("utils.R")

extract_run_row <- function(res, mode = "generic") {
  vars <- res$variables %||% list()
  active_count <- 0
  for (v in vars) {
    if (abs(get_variable_value(v)) > 1e-9) {
      active_count <- active_count + 1
    }
  }

  routes <- res$routes %||% list()
  unserved <- res$unserved %||% list()

  list(
    mode = normalize_mode(mode),
    status = tolower(as.character(res$status %||% "unknown")),
    objective = safe_numeric(res$objective, NA_real_),
    solve_time = safe_numeric(res$solve_time, NA_real_),
    variable_count = length(vars),
    active_variable_count = active_count,
    route_count = length(routes),
    unserved_count = length(unserved),
    feasible = tolower(as.character(res$status %||% "")) %in% c("optimal", "feasible", "ok")
  )
}

extract_run_table <- function(run_results, mode = "generic") {
  if (!is.list(run_results) || length(run_results) == 0) {
    return(data.frame())
  }

  rows <- list()
  for (i in seq_along(run_results)) {
    res <- run_results[[i]]
    if (!is.list(res)) {
      next
    }
    row <- extract_run_row(res, mode)
    rows[[length(rows) + 1]] <- data.frame(
      run_id = i,
      mode = as.character(row$mode),
      status = as.character(row$status),
      objective = as.numeric(row$objective),
      solve_time = as.numeric(row$solve_time),
      variable_count = as.integer(row$variable_count),
      active_variable_count = as.integer(row$active_variable_count),
      route_count = as.integer(row$route_count),
      unserved_count = as.integer(row$unserved_count),
      feasible = as.logical(row$feasible),
      stringsAsFactors = FALSE
    )
  }

  if (length(rows) == 0) {
    return(data.frame())
  }

  do.call(rbind, rows)
}

bootstrap_ci <- function(values, confidence = 0.95, n_boot = 1000, seed = 42) {
  x <- values[is.finite(values)]
  if (length(x) == 0) {
    return(list(mean = NA_real_, lower = NA_real_, upper = NA_real_, confidence = confidence))
  }
  if (length(x) == 1) {
    return(list(mean = x[[1]], lower = x[[1]], upper = x[[1]], confidence = confidence))
  }

  set.seed(seed)
  boot_means <- numeric(n_boot)
  n <- length(x)
  for (b in seq_len(n_boot)) {
    idx <- sample.int(n, size = n, replace = TRUE)
    boot_means[[b]] <- mean(x[[idx]], na.rm = TRUE)
  }

  alpha <- (1.0 - confidence) / 2.0
  q <- as.numeric(stats::quantile(boot_means, probs = c(alpha, 1.0 - alpha), na.rm = TRUE))
  list(
    mean = mean(x, na.rm = TRUE),
    lower = q[[1]],
    upper = q[[2]],
    confidence = confidence
  )
}

normalize_objective_sense <- function(value) {
  if (is.null(value)) {
    return(NULL)
  }
  s <- tolower(trimws(as.character(value)))
  if (s %in% c("max", "maximize", "maximise", "profit", "utility")) {
    return("maximize")
  }
  if (s %in% c("min", "minimize", "minimise", "cost", "distance", "time")) {
    return("minimize")
  }
  NULL
}

infer_objective_direction <- function(run_results = NULL,
                                      mode = "generic",
                                      objective_sense = NULL) {
  explicit <- normalize_objective_sense(objective_sense)
  if (!is.null(explicit)) {
    return(explicit)
  }

  mode <- normalize_mode(mode)

  if (is.list(run_results) && length(run_results) > 0) {
    for (res in run_results) {
      if (!is.list(res)) {
        next
      }

      candidates <- list(
        res$sense,
        res$Sense,
        res$objective_sense,
        (res$details %||% list())$sense,
        (res$details %||% list())$objective_sense,
        (res$meta %||% list())$sense,
        (res$meta %||% list())$objective_sense
      )

      for (candidate in candidates) {
        inferred <- normalize_objective_sense(candidate)
        if (!is.null(inferred)) {
          return(inferred)
        }
      }
    }
  }

  # Conservative fallback when explicit sense metadata is unavailable.
  if (mode %in% c("packing", "resourcing", "scheduling")) {
    return("maximize")
  }
  "minimize"
}

mad_zscore_flags <- function(values, threshold = 3.5) {
  x <- as.numeric(values)
  if (length(x) < 3 || all(!is.finite(x))) {
    return(rep(FALSE, length(x)))
  }

  med <- stats::median(x, na.rm = TRUE)
  mad_val <- stats::mad(x, center = med, constant = 1.4826, na.rm = TRUE)
  if (!is.finite(mad_val) || mad_val <= 1e-12) {
    return(rep(FALSE, length(x)))
  }

  z <- abs((x - med) / mad_val)
  z > threshold
}

objective_direction <- function(mode = "generic") {
  infer_objective_direction(run_results = NULL, mode = mode, objective_sense = NULL)
}

objective_score <- function(values, direction = "minimize") {
  x <- as.numeric(values)
  if (direction == "maximize") {
    return(x)
  }
  -x
}

summarize_objective_quality <- function(objective_values,
                                        mode = "generic",
                                        direction = NULL) {
  x <- objective_values[is.finite(objective_values)]
  if (is.null(direction)) {
    direction <- objective_direction(mode)
  }
  if (length(x) == 0) {
    return(list(best = NA_real_, worst = NA_real_, spread = NA_real_, direction = direction))
  }

  if (direction == "maximize") {
    best <- max(x)
    worst <- min(x)
  } else {
    best <- min(x)
    worst <- max(x)
  }

  list(
    best = best,
    worst = worst,
    spread = worst - best,
    direction = direction
  )
}

analyze_run_history <- function(run_results,
                                mode = "generic",
                                objective_sense = NULL,
                                confidence = 0.95,
                                n_boot = 1000,
                                seed = 42) {
  run_df <- extract_run_table(run_results, mode)
  direction <- infer_objective_direction(
    run_results = run_results,
    mode = mode,
    objective_sense = objective_sense
  )
  if (nrow(run_df) == 0) {
    return(list(
      mode = normalize_mode(mode),
      direction = direction,
      run_count = 0,
      feasible_rate = NA_real_,
      objective_ci = bootstrap_ci(numeric(0), confidence = confidence, n_boot = n_boot, seed = seed),
      solve_time_ci = bootstrap_ci(numeric(0), confidence = confidence, n_boot = n_boot, seed = seed),
      objective_quality = summarize_objective_quality(numeric(0), mode, direction = direction),
      status_mix = data.frame(),
      anomalies = data.frame(),
      recommendation = "No runs provided; cannot evaluate stability."
    ))
  }

  obj_ci <- bootstrap_ci(run_df$objective, confidence = confidence, n_boot = n_boot, seed = seed)
  time_ci <- bootstrap_ci(run_df$solve_time, confidence = confidence, n_boot = n_boot, seed = seed)
  objective_quality <- summarize_objective_quality(run_df$objective, mode, direction = direction)

  objective_anomaly <- mad_zscore_flags(run_df$objective)
  solve_time_anomaly <- mad_zscore_flags(run_df$solve_time)
  run_df$objective_anomaly <- objective_anomaly
  run_df$solve_time_anomaly <- solve_time_anomaly
  run_df$is_anomaly <- objective_anomaly | solve_time_anomaly

  status_mix <- as.data.frame(table(run_df$status), stringsAsFactors = FALSE)
  names(status_mix) <- c("status", "count")
  status_mix$rate <- status_mix$count / max(1, nrow(run_df))

  feasible_rate <- mean(run_df$feasible, na.rm = TRUE)
  anomaly_count <- sum(run_df$is_anomaly, na.rm = TRUE)

  recommendation <- "Stable enough for production traffic."
  if (is.finite(feasible_rate) && feasible_rate < 0.95) {
    recommendation <- "Feasibility is below target; investigate model formulation and solver options."
  } else if (anomaly_count > 0) {
    recommendation <- "Runs are feasible but unstable outliers exist; inspect seeds, time limits, and scenario mix."
  }

  list(
    mode = normalize_mode(mode),
    direction = direction,
    run_count = nrow(run_df),
    feasible_rate = feasible_rate,
    objective_ci = obj_ci,
    solve_time_ci = time_ci,
    objective_quality = objective_quality,
    status_mix = status_mix,
    anomalies = run_df[run_df$is_anomaly, , drop = FALSE],
    recommendation = recommendation,
    run_table = run_df
  )
}

safe_wilcox_test <- function(x, y, alternative = "two.sided") {
  x <- as.numeric(x)
  y <- as.numeric(y)
  x <- x[is.finite(x)]
  y <- y[is.finite(y)]

  if (length(x) < 2 || length(y) < 2) {
    return(list(
      p_value = NA_real_,
      statistic = NA_real_,
      sample_x = length(x),
      sample_y = length(y),
      note = "Not enough finite samples for Wilcoxon test"
    ))
  }

  test <- tryCatch(
    {
      stats::wilcox.test(x, y, alternative = alternative, exact = FALSE)
    },
    error = function(e) {
      NULL
    }
  )

  if (is.null(test)) {
    return(list(
      p_value = NA_real_,
      statistic = NA_real_,
      sample_x = length(x),
      sample_y = length(y),
      note = "Wilcoxon test failed"
    ))
  }

  list(
    p_value = safe_numeric(test$p.value, NA_real_),
    statistic = safe_numeric(test$statistic, NA_real_),
    sample_x = length(x),
    sample_y = length(y),
    note = "ok"
  )
}

pairwise_significance <- function(run_df,
                                  direction = "minimize",
                                  alpha = 0.05,
                                  p_adjust = "holm") {
  if (!is.data.frame(run_df) || nrow(run_df) == 0 || !all(c("solver", "objective") %in% names(run_df))) {
    return(data.frame())
  }

  groups <- unique(as.character(run_df$solver))
  if (length(groups) < 2) {
    return(data.frame())
  }

  pairs <- combn(groups, 2, simplify = FALSE)
  rows <- list()

  for (pair in pairs) {
    a <- pair[[1]]
    b <- pair[[2]]

    a_obj <- run_df$objective[run_df$solver == a]
    b_obj <- run_df$objective[run_df$solver == b]

    a_score <- objective_score(a_obj, direction = direction)
    b_score <- objective_score(b_obj, direction = direction)

    test <- safe_wilcox_test(a_score, b_score, alternative = "two.sided")
    effect <- stats::median(a_score, na.rm = TRUE) - stats::median(b_score, na.rm = TRUE)

    rows[[length(rows) + 1]] <- data.frame(
      solver_a = as.character(a),
      solver_b = as.character(b),
      n_a = as.integer(test$sample_x),
      n_b = as.integer(test$sample_y),
      p_value = safe_numeric(test$p_value, NA_real_),
      statistic = safe_numeric(test$statistic, NA_real_),
      effect_median_score = safe_numeric(effect, NA_real_),
      preferred_solver = ifelse(is.finite(effect) && effect >= 0, a, b),
      note = as.character(test$note),
      stringsAsFactors = FALSE
    )
  }

  out <- do.call(rbind, rows)
  if (nrow(out) == 0) {
    return(out)
  }

  out$p_adjusted <- stats::p.adjust(out$p_value, method = p_adjust)
  out$significant <- is.finite(out$p_adjusted) & (out$p_adjusted < alpha)
  out
}

global_significance <- function(run_df,
                                direction = "minimize",
                                alpha = 0.05) {
  if (!is.data.frame(run_df) || nrow(run_df) == 0 || !all(c("solver", "objective") %in% names(run_df))) {
    return(list(method = "kruskal.test", p_value = NA_real_, significant = FALSE, note = "No data"))
  }

  df <- run_df[is.finite(run_df$objective), , drop = FALSE]
  if (nrow(df) < 3 || length(unique(as.character(df$solver))) < 2) {
    return(list(method = "kruskal.test", p_value = NA_real_, significant = FALSE, note = "Insufficient data"))
  }

  df$score <- objective_score(df$objective, direction = direction)
  test <- tryCatch(
    {
      stats::kruskal.test(score ~ solver, data = df)
    },
    error = function(e) {
      NULL
    }
  )

  if (is.null(test)) {
    return(list(method = "kruskal.test", p_value = NA_real_, significant = FALSE, note = "Kruskal test failed"))
  }

  p <- safe_numeric(test$p.value, NA_real_)
  list(
    method = "kruskal.test",
    p_value = p,
    significant = is.finite(p) && p < alpha,
    note = "ok"
  )
}

best_vs_second_significance <- function(summary_df,
                                        run_df,
                                        direction = "minimize",
                                        alpha = 0.05) {
  if (!is.data.frame(summary_df) || nrow(summary_df) < 2 || !"solver" %in% names(summary_df)) {
    return(list(note = "Need at least two solver groups for best-vs-second significance"))
  }

  best <- as.character(summary_df$solver[[1]])
  second <- as.character(summary_df$solver[[2]])
  best_scores <- objective_score(run_df$objective[run_df$solver == best], direction = direction)
  second_scores <- objective_score(run_df$objective[run_df$solver == second], direction = direction)

  test <- safe_wilcox_test(best_scores, second_scores, alternative = "two.sided")
  effect <- stats::median(best_scores, na.rm = TRUE) - stats::median(second_scores, na.rm = TRUE)

  list(
    solver_best = best,
    solver_second = second,
    p_value = safe_numeric(test$p_value, NA_real_),
    significant = is.finite(test$p_value) && test$p_value < alpha,
    effect_median_score = safe_numeric(effect, NA_real_),
    note = as.character(test$note)
  )
}

compare_solver_variants <- function(run_results,
                                    solver_labels,
                                    mode = "generic",
                                    objective_sense = NULL,
                                    confidence = 0.95,
                                    n_boot = 1000,
                                    seed = 42,
                                    alpha = 0.05,
                                    p_adjust = "holm") {
  if (!is.list(run_results) || length(run_results) == 0) {
    return(list(error = "No runs provided"))
  }
  if (length(solver_labels) != length(run_results)) {
    return(list(error = "solver_labels length must match run_results length"))
  }

  direction <- infer_objective_direction(
    run_results = run_results,
    mode = mode,
    objective_sense = objective_sense
  )

  run_df <- extract_run_table(run_results, mode)
  if (nrow(run_df) == 0) {
    return(list(error = "No valid run rows were extracted"))
  }
  run_df$solver <- as.character(solver_labels)

  groups <- unique(as.character(solver_labels))
  rows <- list()

  for (g in groups) {
    idx <- which(as.character(solver_labels) == g)
    group_runs <- run_results[idx]
    stats <- analyze_run_history(
      group_runs,
      mode = mode,
      objective_sense = direction,
      confidence = confidence,
      n_boot = n_boot,
      seed = seed
    )

    rows[[length(rows) + 1]] <- data.frame(
      solver = g,
      run_count = stats$run_count,
      feasible_rate = round(stats$feasible_rate, 4),
      objective_mean = round(safe_numeric(stats$objective_ci$mean, NA_real_), 6),
      objective_ci_lower = round(safe_numeric(stats$objective_ci$lower, NA_real_), 6),
      objective_ci_upper = round(safe_numeric(stats$objective_ci$upper, NA_real_), 6),
      solve_time_mean = round(safe_numeric(stats$solve_time_ci$mean, NA_real_), 6),
      solve_time_ci_lower = round(safe_numeric(stats$solve_time_ci$lower, NA_real_), 6),
      solve_time_ci_upper = round(safe_numeric(stats$solve_time_ci$upper, NA_real_), 6),
      recommendation = as.character(stats$recommendation),
      stringsAsFactors = FALSE
    )
  }

  summary_df <- do.call(rbind, rows)

  # Rank by feasibility first, then objective, then solve time.
  if (direction == "maximize") {
    summary_df <- summary_df[order(-summary_df$feasible_rate, -summary_df$objective_mean, summary_df$solve_time_mean), ]
  } else {
    summary_df <- summary_df[order(-summary_df$feasible_rate, summary_df$objective_mean, summary_df$solve_time_mean), ]
  }

  rownames(summary_df) <- NULL
  best_solver <- if (nrow(summary_df) > 0) as.character(summary_df$solver[[1]]) else NA_character_
  global_test <- global_significance(run_df, direction = direction, alpha = alpha)
  pairwise <- pairwise_significance(run_df, direction = direction, alpha = alpha, p_adjust = p_adjust)
  best_vs_second <- best_vs_second_significance(
    summary_df = summary_df,
    run_df = run_df,
    direction = direction,
    alpha = alpha
  )

  list(
    mode = normalize_mode(mode),
    direction = direction,
    summary = summary_df,
    best_solver = best_solver,
    significance = list(
      alpha = alpha,
      p_adjust = p_adjust,
      global = global_test,
      pairwise = pairwise,
      best_vs_second = best_vs_second
    )
  )
}
