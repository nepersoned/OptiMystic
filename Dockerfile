FROM golang:1.22-bookworm AS go-builder
WORKDIR /src/server
COPY server/go.mod server/go.sum* ./
RUN go mod download
COPY server/ ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/optimystic-server ./cmd/server/main.go

FROM julia:1.11-bookworm AS base-runtime

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        r-base \
        r-base-dev \
        ca-certificates \
        curl \
        git \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
COPY --from=go-builder /out/optimystic-server /app/optimystic-server

# Python runtime for solvers + Jupyter + rpy2 bridge
RUN pip3 install --no-cache-dir -r /app/python_solvers/requirements.txt \
    && pip3 install --no-cache-dir \
        jupyterlab \
        notebook \
        jupyter-server \
        ipykernel \
        rpy2

# Julia runtime dependencies
RUN julia --project=/app/julia_solvers -e "using Pkg; Pkg.instantiate()"

# R runtime dependencies for r_solvers
RUN R -q -e "install.packages(c('jsonlite','ggplot2','dplyr','tidyr','IRkernel'), repos='https://cloud.r-project.org')" \
    && R -q -e "IRkernel::installspec(user = FALSE)"

ENV OPTIMYSTIC_PYTHON=python3
ENV OPTIMYSTIC_JULIA=julia
ENV OPTIMYSTIC_PYTHON_TIMEOUT_SECONDS=180
ENV OPTIMYSTIC_JULIA_TIMEOUT_SECONDS=180

# API image
FROM base-runtime AS api
ENV PORT=8000
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/optimystic-server"]

# JupyterLab image
FROM base-runtime AS jupyterlab
EXPOSE 8888
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--ServerApp.token=", "--ServerApp.password=", "--ServerApp.root_dir=/app"]
