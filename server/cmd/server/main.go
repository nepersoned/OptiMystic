package main

import (
	"context"
	"log"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/optimystic/server/internal/router"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
	slog.SetDefault(logger)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}
	readTimeout := readDurationFromEnv("READ_TIMEOUT_SECONDS", 10*time.Second)
	writeTimeout := readDurationFromEnv("WRITE_TIMEOUT_SECONDS", 20*time.Second)
	idleTimeout := readDurationFromEnv("IDLE_TIMEOUT_SECONDS", 60*time.Second)

	newRouter := router.NewRouter()
	server := &http.Server{
		Addr:         ":" + port,
		Handler:      newRouter,
		ReadTimeout:  readTimeout,
		WriteTimeout: writeTimeout,
		IdleTimeout:  idleTimeout,
	}

	slog.Info("server_started", "port", port, "read_timeout", readTimeout.String(), "write_timeout", writeTimeout.String(), "idle_timeout", idleTimeout.String())

	errCh := make(chan error, 1)
	go func() {
		err := server.ListenAndServe()
		if err != nil && err != http.ErrServerClosed {
			errCh <- err
		}
		close(errCh)
	}()

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	select {
	case <-ctx.Done():
		slog.Info("shutdown_signal_received")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
		defer cancel()
		if err := server.Shutdown(shutdownCtx); err != nil {
			slog.Error("graceful_shutdown_failed", "error", err.Error())
			log.Fatal(err)
		}
		slog.Info("server_stopped")
	case err := <-errCh:
		if err != nil {
			slog.Error("server_failed", "error", err.Error())
			log.Fatal(err)
		}
	}
}

func readDurationFromEnv(key string, fallback time.Duration) time.Duration {
	raw := os.Getenv(key)
	if raw == "" {
		return fallback
	}
	seconds, err := strconv.Atoi(raw)
	if err != nil || seconds <= 0 {
		return fallback
	}
	return time.Duration(seconds) * time.Second
}
