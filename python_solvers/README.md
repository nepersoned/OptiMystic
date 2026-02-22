# python_solvers/

Pure Python Pyomo optimization solver.

Go가 호출하는 독립 실행형 최적화 엔진입니다.

## Role

**Pure Calculator**: JSON in → Pyomo execution → JSON out

Go handles all routing, validation, and result processing.

**순수 계산기**: JSON in → Pyomo 실행 → JSON out

Go가 모든 라우팅, 검증, 결과 처리를 담당합니다.

## Structure

```
python_solvers/
├── solver_engine.py          Entry point (called by Go)
├── requirements.txt          Dependencies (Pyomo, Pandas)
│
├── domains/                  Input mapping (4 modules)
│   ├── cutting.py
│   ├── packing.py
│   ├── resourcing.py
│   └── scheduling.py
│
├── logic/                    Pyomo models (5 modules)
│   ├── logic_cg.py           ✅ Column Generation
│   ├── logic_mip.py          ✅ Mixed Integer
│   ├── logic_cp.py           ⏳ Constraint (stub)
│   ├── logic_st.py           ⏳ Stochastic (stub)
│   └── logic_nlp.py          ⏳ Non-Linear (stub)
│
└── utils/                    Internal utilities
    ├── bridge_logic.py       Domain + solver selection
    ├── services.py           Result processing (Go calls this)
    └── solver_engine.py      Pyomo execution engine
```

## 구조

```
python_solvers/
├── solver_engine.py          진입점 (Go가 호출)
├── requirements.txt          의존성 (Pyomo, Pandas)
│
├── domains/                  입력 매핑 (4개 모듈)
│   ├── cutting.py
│   ├── packing.py
│   ├── resourcing.py
│   └── scheduling.py
│
├── logic/                    Pyomo 모델 (5개 모듈)
│   ├── logic_cg.py           ✅ Column Generation
│   ├── logic_mip.py          ✅ Mixed Integer
│   ├── logic_cp.py           ⏳ Constraint (스텁)
│   ├── logic_st.py           ⏳ Stochastic (스텁)
│   └── logic_nlp.py          ⏳ Non-Linear (스텁)
│
└── utils/                    내부 유틸
    ├── bridge_logic.py       도메인 + 솔버 선택
    ├── services.py           결과 처리 (Go가 호출)
    └── solver_engine.py      Pyomo 실행 엔진
```

## Usage

Go server calls:

```bash
python python_solvers/solver_engine.py \
  --domain cutting \
  --solver mip \
  --params '{"Items": ["A"], ...}'
```

Output: JSON (raw result, no post-processing)

## 사용

Go 서버 호출:

```bash
python python_solvers/solver_engine.py \
  --domain cutting \
  --solver mip \
  --params '{"Items": ["A"], ...}'
```

출력: JSON (원본 결과, 후처리 없음)

## Notes

- Go handles routing, validation, result processing
- Python only performs pure calculation
- No Django dependency (pure Python)
- Reference original code: `_legacy_django/ORIGINAL_services.py`

## 주의

- Go가 라우팅, 검증, 결과 처리 담당
- Python은 순수 계산만 수행
- Django 의존성 없음 (순수 Python)
- 원본 코드 참조: `_legacy_django/ORIGINAL_services.py`
