# 1. 파이썬 3.8 기반 이미지 사용
FROM python:3.8-slim

# 2. 시스템 패키지 업데이트 및 최적화 솔버(CBC) 설치
# 산업경영공학 프로젝트에는 솔버가 필수죠!
RUN apt-get update && apt-get install -y \
    coinor-cbc \
    && rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 필요한 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 내 코드 전체 복사
COPY . .

# 6. 포트 설정 (Azure 앱 서비스는 기본적으로 80이나 8080을 씁니다)
EXPOSE 8080

# 7. 실행 명령어 (Dash/Flask 앱 실행)
# 환경 변수로 포트를 지정해주는 것이 좋습니다.
# 반드시 소문자 'optimystic'인지 확인하세요!
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "optimystic.wsgi"]