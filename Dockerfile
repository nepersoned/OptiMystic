ARG BASE_IMAGE=gcr.io/optimystic-493605/github.com/nepersoned/optimystic-deps:latest
FROM ${BASE_IMAGE} AS runtime

WORKDIR /app

COPY agent_core /app/agent_core
COPY julia_solvers /app/julia_solvers
COPY python_solvers /app/python_solvers
COPY r_solvers /app/r_solvers
COPY agent_loop.py /app/agent_loop.py

EXPOSE 8080
EXPOSE 8888

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python3", "-m", "uvicorn", "python_solvers.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
