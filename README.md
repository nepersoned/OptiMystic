https://optimystic.onrender.com/
# 🧙‍♂️ OptiMystic Solver
**웹 기반 최적화 모델링 & 시뮬레이션 플랫폼**

> **수학적 최적화의 대중화.** > 코딩 없이 클릭만으로 복잡한 의사결정 문제를 해결하세요.

---

## 💡 프로젝트 소개
수학적 최적화(LP/MIP)는 강력한 도구이지만, 코드를 직접 짜야 한다는 진입 장벽이 존재합니다. **OptiMystic Solver**는 복잡한 모델링 과정을 **질문형 마법사(Wizard) UI**로 변환하여, 누구나 쉽게 최적의 해답을 찾을 수 있도록 돕습니다.

우리의 목표는 중소기업(SME)과 연구자들이 산업 수준의 의사결정 모델을 웹에서 즉시 구축하고 실행할 수 있도록 지원하는 것입니다.

---

## 🚀 핵심 기능 (Key Features)

### 🏛️ 8가지 전략적 최적화 템플릿 (8 Strategic Templates)

1. **✂️ 자재 절단 (Cutting Stock)**: 파이프, 철판, 목재 등 원자재의 자투리 낭비(Loss)를 최소화하는 절단 계획을 수립합니다.
2. **📦 화물 적재 (Bin Packing)**: 트럭이나 컨테이너의 공간을 빈틈없이 활용하여 적재 효율을 극대화합니다.
3. **🧪 배합 최적화 (Blending)**: 사료, 식품, 화학 제품 등의 품질 기준을 맞추면서 원료 비용을 최소화하는 레시피를 도출합니다.
4. **🏭 생산 계획 (Product Mix)**: 기계 시간, 노동력 등 한정된 자원 내에서 최대 이익을 낼 수 있는 제품별 생산량을 결정합니다.
5. **📅 근무표 생성 (Scheduling)**: 알바생 및 공장 조원의 근무 가능 시간과 법적 제약을 준수하는 자동 인력 배치표를 만듭니다.
6. **🚚 수송 최적화 (Transportation)**: 공장에서 대리점까지 물류 비용을 최소화하는 최적의 배송 경로와 물량을 산출합니다.
7. **📦 재고 최적화 (Inventory)**: **[신규]** 품절은 막고 과잉 재고 비용은 줄이는 적정 주문량과 시점을 제안합니다.
8. **💰 투자 우선순위 (Investment)**: **[신규]** 한정된 예산 내에서 가성비(ROI)가 가장 높은 설비 도입이나 프로젝트 조합을 선정합니다.

### 2. 🧙‍♂️ 스마트 데이터 마법사
- **질문형 인터페이스:** "어떤 데이터인가요?", "인덱스가 있나요?"와 같은 질문을 통해 데이터를 정의합니다.
- **입력 방어(Input Guard):** 변수 타입 오설정이나 필수 값 누락을 원천적으로 차단합니다.

### 3. ⚡ 단계별 워크플로우
- **STEP 1 (Data):** 템플릿을 선택하고 필요한 재료(데이터)를 입력합니다.
- **STEP 2 (Model):** 엔진이 자동으로 수학적 모델(수식)을 생성합니다.
- **STEP 3 (Solve):** 솔버를 구동하고 결과를 시각적으로 확인합니다.

---

## 🧱 기술 스택 (Tech Stack)
- **Frontend/App:** Python Dash (Interactive Web Interface)
- **Data Structure:** Pandas
- **Solver Core:** PuLP (Python Linear Programming API)
- **Visualization:** Plotly Graphing Libraries

---

# 🗺️ OptiMystic 개발 로드맵 (Updated)

## Phase 1: 기반 구축 (✅ 완료)
**기초 개발 환경 및 코어 설계**
* **Q 1-1:** Python, Dash, PuLP 개발 환경 세팅 완료.
* **Q 1-2:** UnitVariable 객체 및 인덱스 처리 코어 설계 완료.

## Phase 2: UI/UX & 진입점 (✅ 완료)
**사용자 인터페이스 및 경험 설계**
* **Q 2-1:** 탭(Tabs) 구조 도입 및 레이아웃 분리.
* **Q 2-2:** 동적 입력 폼(Pattern Matching Callback) 마법사 구현.
* **Q 2-3:** 스마트 유효성 검사(Input Guard) 구축.
* **Q 2-4:** 템플릿 갤러리 (7가지 문제 유형 선택 화면) 구현.

## Phase 3: 데이터 구조화 & 입력 (✅ 완료)
**데이터 관리 및 입력 시스템**
* **Q 3-1:** 마법사 데이터를 DataTable로 구조화.
* **Q 3-2:** 상세(행렬) 입력: 수송/근무표용 엑셀 스타일 팝업 구현.
* **Q 3-3:** 상세(리스트) 입력: 절단/적재용 행 추가(Add Row) 리스트 구현.

## Phase 4: 솔버 엔진 & 로직 (✅ 완료)
**수식 파싱 및 최적화 엔진 탑재**
* **Q 4-1:** (템플릿 로직은 Phase 6으로 통합)
* **Q 4-2:** 수식 파서: 스칼라, 행렬, 리스트 변수 및 Sum 함수 지원.
* **Q 4-3:** **민감도 분석(Sensitivity Analysis) 엔진:** Shadow Price 및 Slack 도출 로직 탑재.

## Phase 5: 결과 시각화 (✅ 완료)
**범용 대시보드 및 분석 리포트**
* **Q 5-1:** **커스텀 대시보드 UI:** KPI 카드(Status, Objective) 및 최적해 테이블.
* **Q 5-2:** **민감도 분석 테이블:** 제약조건별 Shadow Price, Slack 분석 표 구현.

---

## Phase 6: 템플릿 고도화 (🚧 현재 진행 중)
**문제 유형별 맞춤형 환경 구축**
* **Q 6-1: 전용 입력 UI (Template UI):** 수식 입력 없이 공급/수요/단가표 등 직관적 입력 폼 구현.
* **Q 6-2: 로직 브릿지 (Logic Bridge):** UI 데이터(Parameter)를 엔진용 수식으로 자동 변환하는 미들웨어 개발.
* **Q 6-3: 맞춤형 시각화 & 인사이트:**
    * **시각화:** 물류 네트워크(Sankey), 일정 차트(Gantt) 등 전용 그래프.
    * **인사이트:** 민감도 분석 데이터를 활용한 자연어 조언(Advice) 제공.

## Phase 7: 확장 & 폴리싱 (📅 예정)
**기능 확장 및 디자인 개선**
* **Q 7-1:** 엑셀 파일 업로드/다운로드 연동.
* **Q 7-2:** 디자인 고도화 (CSS, 반응형 웹).
---


# 🧙‍♂️ OptiMystic Solver
**Web-based Optimization Modeling & Simulation Platform**

> **Democratizing Mathematical Optimization.** > Solve complex LP/MIP problems without writing a single line of code.

---

## 💡 Introduction
Mathematical optimization is a powerful decision-making tool, but the barrier to entry—coding—is too high for many. **OptiMystic Solver** bridges this gap by transforming complex Linear Programming (LP) and Mixed-Integer Programming (MIP) processes into an intuitive **Wizard-based UI**.

Our goal is to empower SMEs (Small and Medium Enterprises) and researchers to build industrial-grade decision models instantly on the web.

---

## 🚀 Key Features

### 🏛️ 8 Strategic Optimization Templates

1. **✂️ Cutting Stock**: Develops cutting plans to minimize scrap waste (loss) for raw materials like pipes, steel plates, and timber.
2. **📦 Bin Packing**: Maximizes loading efficiency by utilizing every inch of space in trucks or containers.
3. **🧪 Blending Optimization**: Derives recipes that minimize ingredient costs while meeting quality standards for feed, food, or chemicals.
4. **🏭 Production Mix**: Determines the optimal production volume for each product to maximize profit within limited resources like machine time and labor.
5. **📅 Workforce Scheduling**: Automatically generates staff rosters that comply with labor laws and individual availability for part-timers or factory crews.
6. **🚚 Transportation**: Calculates the most cost-effective shipping routes and volumes from factories to distributors.
7. **📦 Inventory Optimization**: **[New]** Suggests optimal reorder points and quantities to prevent stockouts while reducing excess inventory costs.
8. **💰 Investment Priority**: **[New]** Selects the best combination of equipment upgrades or projects with the highest ROI within a fixed budget.

### 2. 🧙‍♂️ Smart Data Wizard
- **Question-Driven:** Instead of coding, answer simple questions like "What are your resources?".
- **Input Guards:** Prevents errors by automatically handling variable types and constraints.

### 3. ⚡ Step-by-Step Workflow
- **STEP 1 (Data):** Define variables and parameters via templates.
- **STEP 2 (Model):** The engine automatically builds mathematical formulations.
- **STEP 3 (Solve):** Run the solver (CBC/GLPK) and visualize results.

---

## 🧱 Tech Stack
- **Frontend:** Python Dash (React.js based)
- **Data:** Pandas
- **Solver Core:** PuLP (Python LP modeler)
- **Visualization:** Plotly, Dash Core Components

---

# 🗺️ OptiMystic Development Roadmap (Updated)

## Phase 1: Foundation Setup (✅ Completed)
**Core Architecture & Environment**
* **Q 1-1:** Python, Dash, and PuLP development environment setup.
* **Q 1-2:** Core architecture design for `UnitVariable` and index handling.

## Phase 2: UI/UX & Entry Point (✅ Completed)
**User Interface & Experience Design**
* **Q 2-1:** Implementation of Tab structure and layout separation.
* **Q 2-2:** Development of Dynamic Input Wizard (Pattern Matching Callback).
* **Q 2-3:** Implementation of Smart Input Guard & Validation.
* **Q 2-4:** Template Gallery implementation (Selection for 7 problem types).

## Phase 3: Data Structure & Input (✅ Completed)
**Data Management & Input Systems**
* **Q 3-1:** Structuring Wizard data into DataTables.
* **Q 3-2:** Matrix Input: Excel-style grid popup for Transportation/Shift problems.
* **Q 3-3:** List Input: Add-row style list for Cutting/Packing problems.

## Phase 4: Solver Engine & Logic (✅ Completed)
**Formula Parsing & Optimization Engine**
* **Q 4-1:** (Template logic integrated into Phase 6)
* **Q 4-2:** Formula Parser: Support for Scalar, Matrix, List variables, and Sum function.
* **Q 4-3:** **Sensitivity Analysis Engine:** Logic for extracting Shadow Prices and Slack values.

## Phase 5: Result Visualization (✅ Completed)
**Generic Dashboard & Analysis Reporting**
* **Q 5-1:** **Custom Dashboard UI:** KPI Cards (Status, Objective) and Optimal Solution Table.
* **Q 5-2:** **Sensitivity Analysis Table:** Breakdown of Constraints, Shadow Prices, and Slack.

---

## Phase 6: Template Specialization (🚧 Current Focus)
**Problem-Specific Customization**
* **Q 6-1: Dedicated Input UI (Template UI):** Intuitive forms (e.g., Supply/Demand/Cost) removing the need for formula entry.
* **Q 6-2: Logic Bridge:** Middleware to auto-convert UI parameters into engine-compatible formulas.
* **Q 6-3: Customized Visualization & Insights:**
    * **Visuals:** Domain-specific charts (e.g., Sankey for Logistics, Gantt for Scheduling).
    * **Insights:** Natural language advice derived from Sensitivity Analysis data.

## Phase 7: Polish & Expansion (📅 Planned)
**Feature Expansion & Design Refinement**
* **Q 7-1:** Integration of Excel file upload/download.
* **Q 7-2:** Design refinement (CSS, Responsive layout).
