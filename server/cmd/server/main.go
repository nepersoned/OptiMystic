package main

import (
	"log"
	"net/http"
	"os"

	"github.com/optimystic/server/internal/router"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	newRouter := router.NewRouter()
	http.Handle("/", newRouter)

	log.Printf("Starting OptiMystic server on :%s", port)

	err := http.ListenAndServe(":"+port, newRouter)
	if err != nil {
		log.Fatal(err)
	}
}
