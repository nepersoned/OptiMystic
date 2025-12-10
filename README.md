# 🧙‍♂️ OptiMystic Solver: 웹 기반 최적화 모델링 & 시뮬레이션 플랫폼

## 💡 프로젝트 소개 (Value Proposition)

> 수학적 최적화 모델링은 강력한 의사결정 도구이지만, 코드를 직접 작성해야 하는 진입 장벽이 존재합니다.
> **OptiMystic Solver**는 복잡한 최적화(LP/MIP) 모델 정의 과정을 **질문형 마법사(Wizard) UI**로 변환하여, 사용자에게 **직관적인 노코드(No-Code) 모델링 환경**을 제공합니다.

**최종 목표:** 사용자가 마법사를 통해 정의한 데이터를 `PuLP` 객체로 완벽하게 변환하고, **산업 및 연구 수준의 의사결정 모델**을 웹에서 즉시 구축 및 실행할 수 있도록 지원하는 것입니다.

---

## 🧱 시스템 아키텍처 및 기술 스택

OptiMystic Solver는 Python 생태계의 강력한 라이브러리들로 구성되어 있습니다.

* **Frontend/App**: `Python Dash`를 사용하여 반응형 웹 인터페이스 및 복잡한 콜백 로직을 관리합니다.
* **UX/UI Engine**: `Dash Core Components`와 `Pattern Matching Callbacks`를 활용한 **동적 마법사(Wizard) 폼**을 구현했습니다.
* **Data Structure**: 입력 데이터를 **변수(Variable)**와 **파라미터(Parameter)**로 명확히 분리하여 관리하며, `Pandas`를 통해 구조화합니다.
* **Solver Core**: `PuLP`를 사용하여 최적화 문제(LP/MIP)를 수식적으로 모델링하고, 오픈소스 솔버(CBC 등)와 연동합니다.

---

## ✅ 핵심 기능 상세 (Key Features)

### 1. 스마트 데이터 정의 마법사 (Data Definition Wizard)
* **질문형 인터페이스:** 엑셀처럼 막막한 그리드 대신, "어떤 데이터인가요?", "인덱스가 있나요?"와 같은 질문을 통해 데이터를 정의합니다.
* **자동 분류 시스템:** 사용자의 응답에 따라 데이터를 **'결정 변수(Variables)'** 탭과 **'파라미터(Parameters)'** 탭으로 자동 분류하여 저장합니다.
* **동적 입력 폼:** 인덱스 사용 여부($x$ vs $x_i$)에 따라 범위 입력창이 자동으로 생성되거나 숨겨집니다.

### 2. 지능형 유효성 검사 (Smart Input Guards)
* **문맥 인식 입력 제어:**
    * **변수(Variable)** 정의 시: 초기값 입력창을 숨겨 혼란을 방지합니다.
    * **파라미터(Parameter)** 정의 시: 변수 타입(Binary 등) 선택창을 숨깁니다.
* **실시간 방어:** 이름 누락, 단위 누락 등 필수 정보가 없을 경우 테이블 추가를 원천적으로 방지합니다.

### 3. 단계별 모델링 워크플로우 (Step-by-Step Modeling)
* **STEP 1 (Data):** 마법사를 통해 재료(변수/파라미터)를 준비합니다.
* **STEP 2 (Model):** 준비된 재료를 사용하여 목적 함수와 제약 조건을 수립하고 솔버를 가동합니다.

---

## 🗺️ OptiMystic Solver: 개발 로드맵 (Development Roadmap)

| Phase | 퀘스트 | 퀘스트 이름 | 상태 | 세부 구현 내용 |
| :---: | :---: | :---: | :---: | :--- |
| **Phase 1** | Q 1-1 | 개발 환경 세팅 | ✅ 완료 | Python, Dash, PuLP 라이브러리 설치 및 환경 구성. |
| (기반 구축) | Q 1-2 | 핵심 엔진 설계 | ✅ 완료 | `UnitVariable` 객체 구조화 및 인덱스 처리 로직 설계. |
| **Phase 2** | Q 2-1 | 연구실(UI) 배치 | ✅ 완료 | 탭(Tabs) 구조 도입 (Step 1: 데이터 / Step 2: 모델링) 및 레이아웃 분리. |
| (UI/UX) | Q 2-2 | **마법사(Wizard) 구현** | ✅ 완료 | 라디오 버튼과 질문 형태의 동적 입력 폼(Pattern Matching Callback) 완성. |
| | Q 2-3 | **스마트 유효성 검사** | ✅ 완료 | 변수/파라미터 자동 분류 및 상황에 따른 입력창 동적 제어(Input Guard) 구축. |
| **Phase 3** | Q 3-1 | **데이터 구조화** | ✅ 완료 | 마법사를 통해 입력된 데이터를 `DataTable`에 구조적으로 수집 및 저장. |
| (데이터 연결) | **Q 3-2** | **상세 데이터 입력** | 🚧 진행중 | **[Matrix Input]** 인덱스 파라미터($C_{i,j}$)의 구체적인 값을 입력받을 수 있는 팝업/행렬 테이블 구현. |
| | Q 3-3 | 엔진 동기화 | ⬜ 대기 | UI에 입력된 상세 데이터를 `unit_core` 엔진과 실시간 동기화. |
| **Phase 4** | Q 4-1 | 수식 마법사 | ⬜ 대기 | 목적 함수 및 제약식을 텍스트 파싱하여 PuLP 객체로 변환하는 로직 구현. |
| (솔버 가동) | **Q 4-2** | **솔버 연결 (Solve)** | ⬜ 대기 | `Run` 버튼 클릭 시 실제 최적화 엔진 구동 및 결과 도출. |
| **Phase 5** | Q 5-1 | 결과 대시보드 | ⬜ 대기 | 최적 해(Optimal Solution)와 변수 상태를 시각화된 테이블로 출력. |
| (분석/배포) | Q 6 | 디자인 고도화 | ⬜ 대기 | CSS 커스텀 및 반응형 레이아웃 적용 (Inter 폰트 적용 완료). |

---

<br>

***

# 🧙‍♂️ OptiMystic Solver: Web-Based Optimization Modeling Platform

## 💡 Project Overview

> Mathematical optimization is a powerful tool, but coding it from scratch is a barrier for many.
> **OptiMystic Solver** replaces complex coding with an **intuitive Wizard UI**, providing a **No-Code environment** for defining Linear Programming (LP) and Mixed-Integer Programming (MIP) models.

**Goal:** To seamlessly convert user-defined data from the Wizard into `PuLP` objects, enabling the construction and execution of **decision-making models** directly on the web.

---

## 🧱 Tech Stack & Architecture

* **Frontend:** `Python Dash` for reactive web interfaces.
* **UX Engine:** Utilizes `Dash Pattern Matching Callbacks` to build a **Dynamic Wizard Form**.
* **Data Logic:** Structurally separates **Variables** and **Parameters** using `Pandas`.
* **Solver Core:** `PuLP` for mathematical modeling, interfacing with open-source solvers (e.g., CBC).

---

## ✅ Key Features

### 1. Smart Data Definition Wizard
* **Question-Driven Interface:** Instead of complex grids, users answer simple questions (e.g., "Is this a variable?", "Does it have indices?").
* **Auto-Classification:** Automatically routes data to the **'Variables'** or **'Parameters'** tab based on user input.
* **Dynamic Forms:** Input fields for index ranges appear or disappear dynamically based on the dimension settings.

### 2. Intelligent Input Guards
* **Context-Aware:**
    * For **Variables**: Hides initial value inputs (preventing confusion).
    * For **Parameters**: Hides variable type selectors (e.g., Binary/Integer).
* **Real-time Protection:** Prevents submission if essential fields (Name, Unit) are missing.

### 3. Step-by-Step Workflow
* **STEP 1 (Define Data):** Prepare ingredients (Variables/Parameters) using the Wizard.
* **STEP 2 (Model & Solve):** Build objective functions/constraints and run the solver.

---

## 🗺️ Development Roadmap

| Phase | Quest | Quest Name | Status | Details |
| :---: | :---: | :---: | :---: | :--- |
| **Phase 1** | Q 1-1 | Env Setup | ✅ Done | Python, Dash, PuLP installation. |
| (Foundation) | Q 1-2 | Engine Design | ✅ Done | `UnitVariable` class structure & index logic. |
| **Phase 2** | Q 2-1 | Layout Setup | ✅ Done | Implemented Step-by-Step Tabs (Data vs. Model). |
| (UI/UX) | Q 2-2 | **Wizard UI** | ✅ Done | Dynamic form with Radio buttons & Question flow. |
| | Q 2-3 | **Smart Validation** | ✅ Done | Auto-classification & Dynamic Input Guards. |
| **Phase 3** | Q 3-1 | **Data Structuring** | ✅ Done | Collecting Wizard inputs into structured DataTables. |
| (Data) | **Q 3-2** | **Matrix Input** | 🚧 In Progress | UI for inputting specific values for indexed parameters ($C_{i,j}$). |
| | Q 3-3 | Engine Sync | ⬜ Pending | Syncing UI data with `unit_core` engine. |
| **Phase 4** | Q 4-1 | Formula Wizard | ⬜ Pending | Parsing text formulas into PuLP objects. |
| (Solver) | **Q 4-2** | **Solve** | ⬜ Pending | Triggering the actual optimization engine. |
| **Phase 5** | Q 5-1 | Dashboard | ⬜ Pending | Visualizing Optimal Solutions. |
| (Polish) | Q 6 | Design | ⬜ Pending | Advanced CSS & Responsive Layout (Inter font applied). |

---
*This README reflects the "Wizard Edition" update.*
