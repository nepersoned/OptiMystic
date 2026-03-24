module github.com/optimystic/server

go 1.22

require github.com/mitchellh/mapstructure v1.5.0

// Go dependencies for OptiMystic server
// HTTP routing: standard library (net/http)
// JSON encoding: standard library (encoding/json)
// Subprocess: standard library (os/exec)

// Optional dependencies (comment out if not using):
// github.com/gorilla/mux v1.8.1  # Advanced routing
// github.com/go-chi/chi/v5 v5.0.10  # Router framework
// go.uber.org/zap v1.26.0  # Structured logging
// github.com/rs/cors v1.10.1  # CORS middleware
