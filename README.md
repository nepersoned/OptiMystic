# 🚀 OptiMystic Solver: 웹 기반 최적화 모델링 & 시뮬레이션 플랫폼
## 💡 프로젝트 소개 및 목표 (Value Proposition)

> 수학적 최적화 모델링은 강력한 의사결정 도구이지만, 코드를 직접 작성해야 하는 어려움이 있습니다. **OptiMystic Solver**는 복잡한 최적화(LP/MIP) 모델 정의 과정을 **직관적인 웹 UI**로 변환하여, 사용자에게 **코드 없는 모델링 환경**을 제공합니다.

**최종 목표:** 사용자가 입력한 데이터를 PuLP 객체로 완벽하게 변환하고, **산업 및 연구 수준의 의사결정 모델**을 웹에서 구축 및 실행할 수 있도록 하는 것입니다.

-----

## 🧱 시스템 아키텍처 및 기술 스택

OptiMystic Solver는 Python 기반의 강력한 스택으로 구성되어 있습니다.

  * **Frontend/App**: `Python Dash`를 사용하여 대화형 웹 인터페이스 및 콜백을 관리합니다.
  * **Styling**: `Dash Bootstrap Components (계획)`를 도입하여 현대적이고 반응형 UI/UX를 구축할 예정입니다.
  * **Parser/Validator**: `Python`과 `Pandas`를 사용하여 입력 데이터를 파싱하고 단위 변수를 객체화하며 유효성을 검사합니다.
  * **Solver Core**: `PuLP`를 사용하여 최적화 문제(LP/MIP)를 모델링하고 솔버와 연동합니다.

-----

## ✅ 핵심 기능 상세 (Key Features)

### 1\. 모델 요소 정의 및 단위 관리

  * **동적 인터페이스:** 연속형, 정수형, 이진형, 상수(Parameter) 등 다양한 변수 타입을 웹에서 쉽게 정의할 수 있습니다.
  * **단위 변수 객체화:** 변수 값, 분자 단위 (`unit_num`), 분모 단위 (`unit_denom`)를 구조화된 클래스 (`UnitVariable`)로 관리합니다.

### 2\. 고급 유효성 검사 (Validator Pipeline)

  * **기초 검사:** 빈 값 및 숫자 유효성 검사를 실시간으로 수행합니다.
  * **이진형 값 검사 (완료):** `Binary` 타입 변수에 대해 값이 $0$ 또는 $1$인지 확인하는 로직을 구현했습니다.
  * **심화 검사 (계획):** 중복 변수명, 단위 필드 누락, 인덱스 범위-개수 일치 등 모델 무결성 확보 로직을 추가할 예정입니다.

### 3\. 수식 기반 모델링 (Constraint Wizard)

  * 목적 함수 및 제약 조건을 수식(예: `SUM(X[i] * Cost[i])`) 형태로 입력하고, 이를 PuLP 모델 객체로 자동 변환하는 파싱 엔진을 구축할 예정입니다.

-----

## 🗺️ OptiMystic Solver: 최종 마스터 플랜 (Updated Final Master Plan)

| Phase | 퀘스트 번호 | 퀘스트 이름 | 진행 상태 | 세부 구현 내용 (Specs) |
| :---: | :---: | :---: | :---: | :--- |
| **Phase 1** | Q 1-1 | 개발 환경 세팅 | ✅ 완료 | Python 환경 및 Dash/PuLP 라이브러리 설치. |
| (기반 구축) | Q 1-2 | 핵심 엔진 설계 | ⚠️ 부분 완료 | `UnitVariable` 클래스 구현 완료. (인덱스 정보 구조화 미흡) |
| | Q 2-1 | 연구실 책상(UI) 배치 | ✅ 완료 | Dash app.layout 정의 및 목적 함수/제약 조건 입력 영역 마련. |
| | Q 2-2 | 동적 입력 테이블 구현 | ✅ 완료 | DataTable에 인덱스 컬럼 포함. 행 추가/제거 기능 구현. |
| | **Q 2-3** | **유효성 검사 기본 로직** | **✅ 완료** | **기본 숫자 유효성 검사 및 이진형 변수 ($0$/$1$) 값 검사 로직 구현 완료.** |
| | Q 3-1 | 데이터 수집가 (Parser) | ✅ 완료 | `unit_core.py`에 테이블 파싱 및 인덱스 정보 추출 로직 구현 완료. |
| **Phase 2** | **Q 3-2** | **에러 방어막 (Validator)** | ⬜ 대기 | **[P1, 최우선]** `unit_core`를 연결하여 1) 중복 변수명 2) 단위 필드 누락 3) 인덱스 범위-개수 일치 검증 구현. |
| (신경망 연결) | **Q 3-3** | **[심화] 동적 데이터 입력 UI** | ⬜ 대기 | **[P2]** 파싱 정보를 바탕으로, 인덱스 파라미터($C_{i,j}$)의 실제 값을 입력받을 행렬 형태의 DataTable을 동적으로 생성 및 표시. |
| **Phase 3** | Q 4-1 | 목적 함수 설정 (Objective) | ⬜ 대기 | objective-type Dropdown을 활용하여 MAX / MIN 상태를 솔버에 전달하는 로직 구현. |
| (솔버 탑재) | **Q 4-2** | **제약식 마법사 (Constraint Wizard)** | ⬜ 대기 | **[P3]** 수식 파싱(SUM(X[i] * Cost[i])) 로직을 활용하여 PuLP 수식 객체로 변환하는 핵심 파싱 엔진 구현. |
| | **Q 4-3** | **솔버 가동 (Solve)** | ⬜ 대기 | **[P3]** solve-btn 클릭 시, 반복문(Loop)을 사용하여 인덱스별 제약 조건을 효율적으로 구축하고 PuLP 모델 실행. |
| **Phase 4** | **Q 5-1** | **결과 대시보드** | ⬜ 대기 | **[P4]** PuLP 해답을 파싱하여 최적 해(Optimal Solution)와 변수 상태를 깔끔한 DataTable로 출력. |
| (시각화 및 분석) | Q 5-2 | 민감도 분석 (Sensitivity) | ⬜ 대기 | Shadow Price 및 Reduced Cost를 추출하여 결과의 안정성을 검증하는 분석 결과 시각화. |
| **Phase 6** | **Q 6-1~6-2** | **디자인 및 레이아웃 개선** | ⬜ 대기 | **[P1, 최우선]** Dash Bootstrap Components를 도입하여 UI의 가독성 및 전문성을 대폭 향상. |
| (디자인 강화) | Q 7 | 설명서(README) 작성 | ✅ 완료 | GitHub용 README 파일 작성. |

---
-----

*이 README는 프로젝트의 현재 진행 상태를 기반으로 작성되었으며, 지속적인 업데이트가 이루어질 예정입니다.*

# 🚀 OptiMystic Solver: Web-Based Optimization Modeling & Simulation Platform

## 💡 Project Overview and Value Proposition

> Mathematical optimization is a powerful decision-making tool, but often requires difficult coding. **OptiMystic Solver** transforms the complex process of defining optimization models (LP/MIP) into an **intuitive web UI**, providing users with a **code-free modeling environment**. 

**Ultimate Goal:** To fully convert user-input data into PuLP objects, allowing for the construction and execution of **industry and research-grade decision models** directly on the web.

---

## 🧱 System Architecture and Technology Stack

OptiMystic Solver is built on a robust Python-based stack. 

* **Frontend/App**: Uses `Python Dash` to manage the interactive web interface and callbacks.
* **Styling**: Plans to implement `Dash Bootstrap Components (planned)` for a modern and responsive UI/UX.
* **Parser/Validator**: Uses `Python` and `Pandas` to parse input data, instantiate unit variables, and perform data validation.
* **Solver Core**: Employs `PuLP` to model optimization problems (LP/MIP) and interface with the actual solver.

---

## ✅ Core Features (Key Features)

### 1. Model Element Definition and Unit Management

* **Dynamic Interface:** Allows easy definition of various variable types (Continuous, Integer, Binary, Parameter) directly in a web table.
* **Unit Variable Objectification:** Manages the variable value, numerator unit (`unit_num`), and denominator unit (`unit_denom`) within a structured class (`UnitVariable`).

### 2. Advanced Data Validation (Validator Pipeline)

* **Basic Check:** Performs real-time validation for missing values and numerical validity.
* **Binary Value Check (Completed):** Implemented logic to ensure `Binary` variables are set to $0$ or $1$.
* **Advanced Check (Planned):** Will include logic for validating unique variable names, checking for missing unit fields, and verifying index range consistency.

### 3. Formula-Based Modeling (Constraint Wizard)

* The objective function and constraints can be entered as formulas (e.g., `SUM(X[i] * Cost[i])`) which will be converted by a dedicated parsing engine into PuLP model objects.

---

## 🧭 Project Development Status

The project has completed **Phase 1: Foundation** and is about to begin **Phase 2: Core Logic Implementation**.

### Phase 1. Foundation (Baseline Completed)

* **Q 2-3 (Validation):** **Completed**. Basic numerical and binary ($0$/$1$) value validation logic is implemented.
* **Q 3-1 (Data Collector):** **Completed**. Logic for table parsing and index extraction (`parse_variable_name`) is implemented.

### Phase 2. Core Logic and UI (Next Steps)

* **Q 3-2 (Error Shield):** **Next Goal**. Implementation of **advanced validation** (duplicate variable names, unit field checks, etc.) is planned.
* **Q 3-3 (Dynamic Data UI):** **Next Goal**. Implementation of a **dynamic matrix UI** to input values for indexed parameters ($C_{i,j}$) is planned.

---
*This README is based on the current development status of the project and will be updated continuously.*
