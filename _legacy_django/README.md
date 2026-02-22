# Legacy Django 2.0

This folder contains all Django files before migration to Go.

Django에서 Go로 마이그레이션하기 전의 모든 Django 파일들을 보관합니다.

## Complete File List

### HTTP Handlers & Routing
| File | Original Path | Description |
|------|---------------|-------------|
| `views.py` | `core/views.py` | Django HTTP handlers (optimize_view, health_view) |
| `urls_core.py` | `core/urls.py` | API endpoint routing |
| `urls_root.py` | `optimystic/urls.py` | Root URL configuration |
| `wsgi.py` | `optimystic/wsgi.py` | WSGI application entry point |
| `asgi.py` | `optimystic/asgi.py` | ASGI application configuration |

### 전체 파일 목록

### HTTP 핸들러 & 라우팅
| 파일 | 원본 경로 | 설명 |
|------|---------|------|
| `views.py` | `core/views.py` | Django HTTP 핸들러 (optimize_view, health_view) |
| `urls_core.py` | `core/urls.py` | API 엔드포인트 라우팅 |
| `urls_root.py` | `optimystic/urls.py` | 루트 URL 설정 |
| `wsgi.py` | `optimystic/wsgi.py` | WSGI 애플리케이션 진입점 |
| `asgi.py` | `optimystic/asgi.py` | ASGI 애플리케이션 설정 |

### Utilities & Solver
| File | Original Path | Description |
|------|---------------|-------------|
| `bridge_logic.py` | `core/utils/bridge_logic.py` | Domain/solver routing logic |
| `ORIGINAL_services.py` | `core/utils/services.py` | Result processing, dashboard, sensitivity |
| `REFACTORED_solver_engine.py` | `python_solvers/solver_engine.py` | Refactored solver (pure calculator) |

### 유틸리티 & 솔버
| 파일 | 원본 경로 | 설명 |
|------|---------|------|
| `bridge_logic.py` | `core/utils/bridge_logic.py` | 도메인/솔버 라우팅 로직 |
| `ORIGINAL_services.py` | `core/utils/services.py` | 결과 처리, 대시보드, 민감도 분석 |
| `REFACTORED_solver_engine.py` | `python_solvers/solver_engine.py` | 리팩토링된 솔버 (순수 계산기) |

### Django Configuration
| File | Original Path | Description |
|------|---------------|-------------|
| `settings.py` | `optimystic/settings.py` | Django settings (DB, MIDDLEWARE, INSTALLED_APPS) |
| `models.py` | `core/models.py` | Django ORM models (OptimizationRun) |
| `apps.py` | `core/apps.py` | Django app configuration |

### Django 설정
| 파일 | 원본 경로 | 설명 |
|------|---------|------|
| `settings.py` | `optimystic/settings.py` | Django 설정 (DB, MIDDLEWARE, INSTALLED_APPS) |
| `models.py` | `core/models.py` | Django ORM 모델 (OptimizationRun) |
| `apps.py` | `core/apps.py` | Django 앱 설정 |

## Migration Status

- ✅ All Django files backed up to `_legacy_django/`
- ✅ Go file structure created
  - `cmd/server/main.go` (HTTP server)
  - `internal/router/router.go` (routing)
  - `internal/handlers/optimize.go` (request handling)
  - `internal/handlers/health.go` (health check)
  - `internal/solver/bridge.go` (domain routing)
- ✅ Python solver refactored to pure calculator

## 마이그레이션 상태

- ✅ 모든 Django 파일 → `_legacy_django/` 보관 완료
- ✅ Go 파일 구조 생성 완료
  - `cmd/server/main.go` (HTTP 서버)
  - `internal/router/router.go` (라우팅)
  - `internal/handlers/optimize.go` (요청 처리)
  - `internal/handlers/health.go` (헬스 체크)
  - `internal/solver/bridge.go` (도메인 라우팅)
- ✅ Python 솔버 순수 계산기로 리팩토링 완료

## Notes

- Django no longer used (reference files only)
- Python Pyomo models continue in `python_solvers/`
- Go handles HTTP layer, Python called via subprocess

## 참고

- Django는 더 이상 사용되지 않음 (참고용 파일만)
- Python Pyomo 모델들은 `python_solvers/`에서 계속 사용됨
- Go는 HTTP 계층 담당, Python은 subprocess로 호출
