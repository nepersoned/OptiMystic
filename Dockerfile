FROM golang:1.22-bookworm AS go-builder
WORKDIR /src/server
COPY server/go.mod server/go.sum* ./
RUN go mod download
COPY server/ ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/optimystic-server ./cmd/server/main.go

FROM julia:1.11-bookworm

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
COPY --from=go-builder /out/optimystic-server /app/optimystic-server

RUN pip3 install --no-cache-dir -r /app/python_solvers/requirements.txt
RUN julia --project=/app/julia_solvers -e "using Pkg; Pkg.instantiate()"

ENV PORT=8000
ENV OPTIMYSTIC_PYTHON=python3
ENV OPTIMYSTIC_JULIA=julia

EXPOSE 8000
CMD ["/app/optimystic-server"]
