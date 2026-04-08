# Legacy Go Server Archive

This directory stores the retired Go API server that was previously used as the main HTTP entry point.

## Why It Was Archived

- The active API path moved to FastAPI (`python_solvers/api/main.py`).
- Keeping the Go implementation in-place at repository root was causing confusion with active runtime docs and startup flow.
- The code is preserved for historical reference and possible migration comparison.

## What Is Archived Here

- `server/`
	- `cmd/server/main.go`: former API entry point.
	- `internal/handlers`: request handling layer.
	- `internal/solver`: bridge/orchestration logic.
	- `internal/services`: response shaping and service-level helpers.
	- `go.mod`, `go.sum`: Go module metadata.

## Repository Policy

- This folder is archive-only and excluded from active development tracking.
- New runtime/API work must be done in active folders:
	- `python_solvers/`
	- `julia_solvers/`
	- `r_solvers/`

## If You Need to Revisit the Old Go Path

1. Review this archive for historical behavior and contracts.
2. Port only required behavior into active Python API/runtime.
3. Avoid reviving root-level `server/` as an active service unless there is an explicit architecture decision.

## Notes

- `.gitignore` is configured to keep this archive out of normal source tracking except this README.
- If you need to track specific legacy files temporarily, adjust `.gitignore` intentionally and revert after analysis.
