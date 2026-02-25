# Legacy Django 2.0

This folder contains all Django files before migration to Go.

## Complete File List

### HTTP Handlers & Routing
| File | Original Path | Description |
|------|---------------|-------------|
| `views.py` | `core/views.py` | Django HTTP handlers (optimize_view, health_view) |
| `urls_core.py` | `core/urls.py` | API endpoint routing |
| `urls_root.py` | `optimystic/urls.py` | Root URL configuration |
| `wsgi.py` | `optimystic/wsgi.py` | WSGI application entry point |
| `asgi.py` | `optimystic/asgi.py` | ASGI application configuration |

### Utilities & Solver
| File | Original Path | Description |
|------|---------------|-------------|
| `bridge_logic.py` | `core/utils/bridge_logic.py` | Domain/solver routing logic |
| `ORIGINAL_services.py` | `core/utils/services.py` | Result processing, dashboard, sensitivity |
| `REFACTORED_solver_engine.py` | `python_solvers/cli_solver.py` | Refactored solver (pure calculator) |

### Django Configuration
| File | Original Path | Description |
|------|---------------|-------------|
| `settings.py` | `optimystic/settings.py` | Django settings (DB, MIDDLEWARE, INSTALLED_APPS) |
| `models.py` | `core/models.py` | Django ORM models (OptimizationRun) |
| `apps.py` | `core/apps.py` | Django app configuration |

## Migration Status

- ✅ All Django files backed up to `_legacy_django/`
- ✅ Go file structure created
  - `cmd/server/main.go` (HTTP server)
  - `internal/router/router.go` (routing)
  - `internal/handlers/optimize.go` (request handling)
  - `internal/handlers/health.go` (health check)
  - `internal/solver/bridge.go` (domain routing)
- ✅ Python solver refactored to pure calculator

## Notes

- Django is no longer used (reference files only)
- Python Pyomo models continue in `python_solvers/`
- Go handles HTTP layer, Python is called via subprocess