# Legacy Backup (Archive)

Original code before migration from **Dash + PuLP** to **Django/Go + Pyomo**.  
Kept for reference and historical record.

레거시 백업 (기록용)

마이그레이션 전 **Dash + PuLP** 기반 원본 코드입니다.  
삭제하지 않고 기록·참고용으로 보관합니다.

## Files in This Folder

| File | Role | After Migration |
|------|------|-----------------|
| `analytics_cutting.py` | Dash UI + data parsing/result processing | `core/utils/services.py` (logic only), UI removed |
| `app.py` | Dash app entry, layout | Django `core/views` + API (separate app) |
| `bridge_logic.py` | Cutting-specific bridge | `core/utils/bridge_logic.py` (expanded for 4 industries) |
| `global_callbacks.py` | Dash callbacks | Handled in Django views |
| `logic_cutting.py` | Cutting MIP (PuLP) | `core/logic/logic_mip.py` (Pyomo) |
| `logic_cg.py` | Column generation (PuLP) | `core/logic/logic_cg.py` (Pyomo) |
| `solver_engine.py` | PuLP build/solve | `core/utils/solver_engine.py` (Pyomo + Auto-Selector) |
| `styles.py` | Dash CSS/styles | Implement in separate frontend |

## 이 폴더의 파일

| 파일 | 역할 | 마이그레이션 후 위치 |
|------|------|---------------------|
| `analytics_cutting.py` | Dash UI + 데이터 파싱/결과 처리 | `core/utils/services.py` (로직만), UI 제거 |
| `app.py` | Dash 앱 진입, 레이아웃 | Django `core/views` + API (별도 앱) |
| `bridge_logic.py` | Cutting 전용 브릿지 | `core/utils/bridge_logic.py` (4대 산업군 확장) |
| `global_callbacks.py` | Dash 콜백 | Django에서는 뷰에서 처리 |
| `logic_cutting.py` | Cutting MIP (PuLP) | `core/logic/logic_mip.py` (Pyomo) |
| `logic_cg.py` | 열생성 (PuLP) | `core/logic/logic_cg.py` (Pyomo) |
| `solver_engine.py` | PuLP 빌드/풀이 | `core/utils/solver_engine.py` (Pyomo + Auto-Selector) |
| `styles.py` | Dash용 CSS/스타일 | 프론트 별도 구현 시 참고 |

## Usage

**Reference & Source Verification**: Original formulas and algorithms are in this code.

**If you want to run Dash again**: Execute `app.py` and add this folder path to PYTHONPATH, or import from project root.

**Current service runs on `python_solvers/` + Go server. This folder does not need modification.**

## 사용

- **참고·출처 확인**: 원본 수식·알고리즘은 이 코드에 있음.
- **Dash 다시 켜고 싶을 때**: `app.py` 실행 시 `analytics_cutting`, `styles` 등 이 폴더 경로를 PYTHONPATH에 넣거나, 프로젝트 루트에서 이 폴더를 패키지로 두고 import 경로만 맞추면 됨.

**현재 서비스는 `python_solvers/` + Go 서버 기준으로 동작합니다. 이 폴더는 수정하지 않아도 됩니다.**
