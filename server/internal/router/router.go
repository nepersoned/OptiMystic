package router

import (
	"net/http"
	// "github.com/optimystic/server/internal/handlers"

	"github.com/optimystic/server/internal/handlers"
)

type Router struct {
	mux *http.ServeMux
}

func NewRouter() *Router {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/health", handlers.HandleHealth)
	mux.HandleFunc("/api/optimize", handlers.HandleOptimize)

	return &Router{mux: mux}
}

func (r *Router) ServeHTTP(w http.ResponseWriter, req *http.Request) {
	r.mux.ServeHTTP(w, req)
}
