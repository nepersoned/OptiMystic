# 🧙‍♂️ OptiMystic Solver
**웹 기반 최적화 모델링 & 시뮬레이션 플랫폼**

> **수학적 최적화의 대중화.** > 코딩 없이 클릭만으로 복잡한 의사결정 문제를 해결하세요.

---

## 💡 프로젝트 소개
수학적 최적화(LP/MIP)는 강력한 도구이지만, 코드를 직접 짜야 한다는 진입 장벽이 존재합니다. **OptiMystic Solver**는 복잡한 모델링 과정을 **질문형 마법사(Wizard) UI**로 변환하여, 누구나 쉽게 최적의 해답을 찾을 수 있도록 돕습니다.

우리의 목표는 중소기업(SME)과 연구자들이 산업 수준의 의사결정 모델을 웹에서 즉시 구축하고 실행할 수 있도록 지원하는 것입니다.

---

## 🚀 핵심 기능 (Key Features)

### 1. 🏛️ 7가지 템플릿 (Template Gallery)
현업에서 발생하는 문제의 95%를 커버하는 **6가지 정형화 모델**과 **자유 모드**를 제공합니다.
- **✂️ 자재 절단 (Cutting Stock):** 원자재 낭비(Loss) 최소화.
- **📦 화물 적재 (Bin Packing):** 트럭/컨테이너 적재 효율 극대화 (배낭 문제).
- **🧪 배합 최적화 (Blending):** 최소 비용으로 최상의 품질 레시피 도출.
- **🏭 생산 계획 (Product Mix):** 한정된 자원 내에서 이익 극대화.
- **📅 근무표 생성 (Scheduling):** 법적 제약을 준수하는 자동 인력 배치.
- **🚚 수송 최적화 (Transportation):** 물류비용을 최소화하는 최적 경로 산출.
- **🔮 자유 모델링 (Custom Mode):** 나만의 수식을 직접 정의하는 마법사 모드.

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

## 🗺️ 개발 로드맵 (Development Roadmap)

### Phase 1: 기반 구축 (✅ 완료)
- **Q 1-1:** Python, Dash, PuLP 개발 환경 세팅.
- **Q 1-2:** `UnitVariable` 객체 및 인덱스 처리 코어 설계.

### Phase 2: UI/UX & 진입점 (✅ 완료)
- **Q 2-1:** 탭(Tabs) 구조 도입 및 레이아웃 분리. (✅ 완료)
- **Q 2-2:** 동적 입력 폼(Pattern Matching Callback) 마법사 구현. (✅ 완료)
- **Q 2-3:** 스마트 유효성 검사(Input Guard) 구축. (✅ 완료)
- **Q 2-4:** **템플릿 갤러리:** 앱 접속 시 7가지 문제 유형 선택 화면 구현. (✅ 완료)

### Phase 3: 데이터 구조화 & 입력 (✅ 완료)
- **Q 3-1:** 마법사 데이터를 DataTable로 구조화. (✅ 완료)
- **Q 3-2:** **상세(행렬) 입력:** 수송/근무표용 엑셀 스타일 팝업 구현. (✅ 완료)
- **Q 3-3:** **상세(리스트) 입력:** 절단/적재용 행 추가(Add Row) 리스트 구현. (✅ 완료)

### Phase 4: 솔버 엔진 & 로직
- **Q 4-1:** **템플릿 로직 빌더:** 6대 템플릿 데이터 자동 수식화(PuLP 변환). 
- **Q 4-2:** **수식 파서:** 자유 모드용 텍스트 수식 해석기 구현.
- **Q 4-3:** 솔버 구동(Solve) 및 결과 반환 로직.

### Phase 5: 결과 시각화 & 배포
- **Q 5-1:** 최적 해(Optimal Solution) 결과 테이블 출력.
- **Q 5-2:** **템플릿별 맞춤 시각화:**
  - 적재율 게이지, 물류 생키(Sankey) 차트, 근무 간트(Gantt) 차트 등.
- **Q 6:** 디자인 고도화 (CSS/반응형).

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

### 1. 🏛️ Template Gallery (7 Industry Patterns)
Don't start from a blank page. We provide 7 pre-built templates that cover 95% of industrial optimization problems:
- **✂️ Cutting Stock:** Minimize material waste (1D packing).
- **📦 Bin Packing:** Maximize truck/container loading efficiency.
- **🧪 Blending:** Optimize recipes for minimum cost and quality.
- **🏭 Production Mix:** Maximize profit with limited resources and time.
- **📅 Shift Scheduling:** Automate workforce rostering while complying with laws.
- **🚚 Transportation:** Find the cheapest logistics routes.
- **🔮 Custom Mode:** Build any model from scratch using our Wizard.

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

## 🗺️ Development Roadmap

### Phase 1: Foundation (✅ Completed)
- **Q 1-1:** Setup Python, Dash, and PuLP environment.
- **Q 1-2:** Design `UnitVariable` core engine and index logic.

### Phase 2: UI & Entry Gate (✅ Completed)
- **Q 2-1:** Implement Tab structure (Data/Model separation). (✅ Completed)
- **Q 2-2:** Develop Dynamic Wizard with Pattern Matching Callbacks. (✅ Completed)
- **Q 2-3:** Implement Smart Input Guards. (✅ Completed)
- **Q 2-4:** **Template Gallery (Landing Page):** Entry point for 7 optimization patterns. (✅ Completed)

### Phase 3: Data Structure & Input (✅ Completed)
- **Q 3-1:** Structure Wizard data into DataTable. (✅ Completed)
- **Q 3-2:** **Matrix Input:** Spreadsheet-like popup for Transportation/Scheduling. (✅ Completed)
- **Q 3-3:** **List Input:** Dynamic row addition for Cutting Stock/Packing. (✅ Completed)

### Phase 4: Solver Engine & Logic
- **Q 4-1:** **Template Logic Builder:** Auto-generate PuLP formulations for 6 templates. (🆕)
- **Q 4-2:** **Formula Parser:** Text-to-Model conversion for Custom Mode.
- **Q 4-3:** Connect Solver (Run) and handle status/errors.

### Phase 5: Visualization & Deployment
- **Q 5-1:** Result Tables (Optimal values).
- **Q 5-2:** **Template Visualization:**
  - Gauge Charts (Packing)
  - Sankey Diagrams (Transportation)
  - Gantt Charts (Scheduling)
- **Q 6:** Design Refinement (CSS/Responsive).

---
