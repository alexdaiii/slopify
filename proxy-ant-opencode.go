package main

import (
	"crypto/tls"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"time"
)

func main() {

	log.Println("[Info] Starting proxy for opencode.ai")

	target, _ := url.Parse("https://opencode.ai")
	proxy := httputil.NewSingleHostReverseProxy(target)

	// Optimize connections to opencode.ai and bound how long a hung upstream
	// can stall us. Without ResponseHeaderTimeout, a wedged opencode.ai would
	// hold proxy connections open forever and eventually fill the pool.
	proxy.Transport = &http.Transport{
		MaxIdleConnsPerHost: 100,
		TLSClientConfig:     &tls.Config{InsecureSkipVerify: false},
		DialContext: (&net.Dialer{
			Timeout:   5 * time.Second,
			KeepAlive: 30 * time.Second,
		}).DialContext,
		ResponseHeaderTimeout: 30 * time.Second,
		IdleConnTimeout:       90 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
	}

	// This runs AFTER sbx has already swapped "proxy-managed" for your real key.
	// ReadHeaderTimeout caps how long a client can take to send request headers —
	// defends against slowloris-style stalls. Headers from a healthy client arrive
	// in <100ms; 10s gives headroom for transient network blips. Body and response
	// timing are intentionally not capped (long-running chat completions can take
	// minutes; that's the upstream's concern, not ours).
	srv := &http.Server{
		Addr: "127.0.0.1:11434",
		Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {

			log.Printf("[Info] Received request for path: %s", r.URL.Path)

			// Allowlist upstream paths to the OpenCode Go endpoints documented at
			// https://opencode.ai/docs/go/#endpoints — i.e. /zen/go/v1/{messages,
			// chat/completions, models}. Anything else is rejected before we
			// touch headers or forward.
			if !strings.HasPrefix(r.URL.Path, "/zen/go/v1/") {
				http.Error(w, "forbidden: path outside /zen/go/v1/", http.StatusForbidden)
				return
			}

			r.Host = target.Host // Fix TLS SNI

			authHeader := r.Header.Get("Authorization")

			// If it's a messages route, extract the real key and mirror it to X-API-KEY
			if strings.HasPrefix(r.URL.Path, "/zen/go/v1/messages") && authHeader != "" {
				realKey := strings.TrimPrefix(authHeader, "Bearer ")

				// If sbx missed it entirely and it's still masked, log a warning
				if realKey == "proxy-managed" {
					log.Println("[CRITICAL] sbx failed to inject the key before it hit the host proxy!")
				} else {
					r.Header.Set("X-API-Key", realKey)
					log.Printf("[Success] Cloned real key to X-API-Key for path: %s", r.URL.Path)
				}
			}

			proxy.ServeHTTP(w, r)
		}),
		ReadHeaderTimeout: 10 * time.Second,
	}

	log.Fatal(srv.ListenAndServe())

	log.Println("[Info] Proxy for opencode.ai is now running on port 11434")
}
