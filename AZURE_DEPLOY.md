# OptiMystic - Azure 배포 가이드

## 📋 사전 준비

### 필수 도구
- Azure CLI (`az` command)
- Git
- Python 3.11+

### Azure 계정
```bash
# Azure CLI 로그인
az login

# 구독 확인
az account list --output table
```

---

## 🚀 빠른 배포 방법 (5분)

### 1️⃣ 리소스 그룹 생성
```bash
az group create \
  --name OptiMystic \
  --location "Korea Central"  # 또는 원하는 지역
```

### 2️⃣ App Service 플랜 생성
```bash
az appservice plan create \
  --name OptiMysticPlan \
  --resource-group OptiMystic \
  --sku B1 \
  --is-linux
```

### 3️⃣ App Service 생성
```bash
az webapp create \
  --resource-group OptiMystic \
  --plan OptiMysticPlan \
  --name optimystic-app \
  --runtime "PYTHON|3.11"
```

### 4️⃣ 환경 변수 설정
```bash
az webapp config appsettings set \
  --resource-group OptiMystic \
  --name optimystic-app \
  --settings \
    DJANGO_SECRET_KEY="your-secret-key-here" \
    DJANGO_DEBUG="0" \
    DJANGO_ALLOWED_HOSTS="optimystic-app.azurewebsites.net"
```

### 5️⃣ 배포
```bash
# GitHub 연결 또는 로컬 배포
az webapp up \
  --resource-group OptiMystic \
  --name optimystic-app \
  --runtime "PYTHON|3.11" \
  --sku B1
```

---

## 🔗 GitHub Actions를 통한 CI/CD 배포 (권장)

### 1️⃣ GitHub Secrets 추가
GitHub 저장소 Settings → Secrets and variables → Actions에 추가:
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_RESOURCE_GROUP`
- `AZURE_APP_NAME`
- `DJANGO_SECRET_KEY`

### 2️⃣ 워크플로우 파일 생성
`.github/workflows/azure-deploy.yml` 파일이 자동생성됨 (GitHub Actions 통합 시)

---

## 🔍 배포 후 확인

### 1️⃣ 앱 상태 확인
```bash
az webapp show \
  --resource-group OptiMystic \
  --name optimystic-app \
  --query state
```

### 2️⃣ 로그 확인
```bash
# 라이브 로그 보기
az webapp log tail \
  --resource-group OptiMystic \
  --name optimystic-app

# 또는 Azure Portal: App Service → Log stream
```

### 3️⃣ API 테스트
```bash
# Health check
curl https://optimystic-app.azurewebsites.net/api/health/

# Optimize 요청
curl -X POST https://optimystic-app.azurewebsites.net/api/optimize/ \
  -H "Content-Type: application/json" \
  -d '{
    "template_type": "cutting",
    "params": {
      "Items": ["A", "B"],
      "ItemLens": [4, 6],
      "Demands": {"A": 2, "B": 1},
      "Stocks": [{"Name": "S1", "Length": 10, "Cost": 5}],
      "Kerf": 0,
      "Sense": "minimize"
    }
  }'
```

---

## ⚠️ 주의사항

### CBC Solver 설치
- Pyomo는 Azure App Service에서 CBC solver를 자동 설치합니다.
- 만약 설치 실패 시, `startup.sh`가 자동 재시도합니다.

### 성능 & 비용
| SKU | vCPU | 메모리 | 월비용 |
|-----|------|--------|--------|
| **B1** | 1 | 1.75GB | ~$12 | ✅ 개발/테스트용
| **B2** | 2 | 3.5GB | ~$35 | 프로덕션
| **P1V2** | 1 | 3.5GB | ~$26 | 높은 성능

### 타임아웃 설정
- 큰 최적화 문제는 시간이 오래 걸릴 수 있습니다.
- `startup.sh`의 `--timeout 300`를 필요에 따라 조정하세요.

---

## 🛠️ 트러블슈팅

### 문제: "Python 모듈을 찾을 수 없음" (ModuleNotFoundError)
**해결**: 
```bash
az webapp restart \
  --resource-group OptiMystic \
  --name optimystic-app
```

### 문제: "CBC Solver 설치 실패"
**해결**: App Service에 Linux 런타임 사용 (Windows보다 호환성 좋음)
```bash
# 앱 삭제 후 Linux로 재생성
az webapp delete --resource-group OptiMystic --name optimystic-app
# 위의 3️⃣ 단계 반복 (--is-linux 플래그 유지)
```

### 문제: "502 Bad Gateway"
**확인 사항**:
- 로그 확인: `az webapp log tail ...`
- Gunicorn 프로세스 재시작: `az webapp restart ...`
- 메모리 부족 여부 확인: Azure Portal → Metrics

---

## 📊 모니터링 & 알림 설정

### Application Insights 활성화
```bash
az monitor app-insights component create \
  --resource-group OptiMystic \
  --app optimystic-insights
```

### 앱에 연결
```bash
az webapp config appsettings set \
  --resource-group OptiMystic \
  --name optimystic-app \
  --settings \
    APPLICATIONINSIGHTS_CONNECTION_STRING="your-connection-string"
```

---

## 🧹 정리 (삭제)

```bash
# 전체 리소스 그룹 삭제
az group delete \
  --name OptiMystic \
  --yes --no-wait
```

---

## 📞 도움말

더 많은 정보:
- [Azure App Service 공식 문서](https://docs.microsoft.com/ko-kr/azure/app-service/)
- [Django on Azure](https://docs.microsoft.com/ko-kr/azure/python/configure-python-web-app-on-app-service/)
- [Pyomo CBC Solver](https://pyomo.readthedocs.io/en/stable/)
