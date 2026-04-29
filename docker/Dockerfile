# Local development build — dependencies + code in one stage.
# Production uses root/Dockerfile (code only) on top of the pre-built deps image.
FROM julia:1.11-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
ENV R_HOME=/usr/lib/R

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
        r-base \
        r-base-dev \
        ca-certificates \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv

WORKDIR /app

COPY python_solvers/requirements.txt /app/python_solvers/requirements.txt
COPY julia_solvers/Project.toml /app/julia_solvers/Project.toml
COPY julia_solvers/Manifest.toml /app/julia_solvers/Manifest.toml

RUN Rscript -e "install.packages(c('jsonlite','ggplot2','dplyr','tidyr'), repos='https://cloud.r-project.org')"

RUN /opt/venv/bin/python -m pip install --upgrade pip setuptools wheel \
    && /opt/venv/bin/python -m pip install -r /app/python_solvers/requirements.txt \
    && /opt/venv/bin/python -m pip install jupyterlab notebook jupyter-server ipykernel

RUN julia --project=/app/julia_solvers -e "using Pkg; Pkg.instantiate()"

ENV OPTIMYSTIC_PYTHON=python3
ENV OPTIMYSTIC_JULIA=julia
ENV OPTIMYSTIC_PYTHON_TIMEOUT_SECONDS=180
ENV OPTIMYSTIC_JULIA_TIMEOUT_SECONDS=180
ENV PORT=8000

COPY agent_core /app/agent_core
COPY julia_solvers /app/julia_solvers
COPY python_solvers /app/python_solvers
COPY r_solvers /app/r_solvers
COPY agent_loop.py /app/agent_loop.py

EXPOSE 8000 8888

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python3", "-m", "uvicorn", "python_solvers.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
