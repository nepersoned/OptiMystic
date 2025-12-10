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

## 🧭 프로젝트 진행 현황 (Development Status)

현재 프로젝트는 **Phase 1: 기반 구축**을 완료하고, **Phase 2: 핵심 로직 구현** 직전에 있습니다.

### Phase 1. 기반 구축 (Baseline Completed)

  * **Q 2-3 (유효성 검사):** **완료**. 기본 숫자 및 이진형 변수 ($0$/$1$) 값 검사 로직 구현 완료.
  * **Q 3-1 (데이터 수집가):** **완료**. 테이블 파싱 및 인덱스 추출 (`parse_variable_name`) 로직 구현 완료.

### Phase 2. 핵심 로직 및 UI (Next Steps)

  * **Q 3-2 (에러 방어막):** **다음 목표**. 중복 변수명, 단위 필드 누락 등 **심화 유효성 검사**를 구현할 예정입니다.
  * **Q 3-3 (동적 데이터 UI):** **다음 목표**. 인덱싱된 파라미터($C_{i,j}$)를 입력받는 **동적 행렬 UI**를 구현할 예정입니다.

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
