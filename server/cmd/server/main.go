package main

import (
	"net/http"
	"log"
	"os"
	// "github.com/optimystic/server/internal/router"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	// router := router.NewRouter()
	// http.Handle("/", router)

	log.Printf("Starting OptiMystic server on :%s", port)
	
	// TODO: Implement full server initialization
	err := http.ListenAndServe(":"+port, nil)
	if err != nil {
		log.Fatal(err)
	}
}
