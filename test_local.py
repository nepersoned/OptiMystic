#!/usr/bin/env python
"""
Local testing script - Azure 배포 전 로컬에서 앱 테스트
"""
import os
import django
import json

# Django 설정 초기화
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'optimystic.settings')
django.setup()

from django.test import Client
from django.http import JsonResponse

print("=" * 60)
print("🧪 OptiMystic - 배포 전 로컬 테스트")
print("=" * 60)

client = Client()

# ✅ Test 1: Health Check
print("\n1️⃣  Health Check 테스트...")
try:
    response = client.get('/api/health/')
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.content.decode()}")
    assert response.status_code == 200, "Health check 실패"
    print("   ✅ PASS")
except Exception as e:
    print(f"   ❌ FAIL: {e}")

# ✅ Test 2: Cutting 최적화
print("\n2️⃣  Cutting 최적화 테스트...")
try:
    payload = {
        "template_type": "cutting",
        "params": {
            "Items": ["A", "B"],
            "ItemLens": [4, 6],
            "Demands": {"A": 2, "B": 1},
            "Stocks": [{"Name": "S1", "Length": 10, "Cost": 5}],
            "Kerf": 0,
            "Sense": "minimize"
        }
    }
    response = client.post(
        '/api/optimize/',
        data=json.dumps(payload),
        content_type='application/json'
    )
    print(f"   Status: {response.status_code}")
    result = json.loads(response.content.decode())
    print(f"   Status: {result.get('status')}")
    assert response.status_code == 200, f"요청 실패: {response.status_code}"
    print("   ✅ PASS")
except Exception as e:
    print(f"   ❌ FAIL: {e}")

# ✅ Test 3: 잘못된 요청 처리
print("\n3️⃣  에러 처리 테스트...")
try:
    payload = {
        "template_type": "cutting",
        "params": {}  # 필수 파라미터 없음
    }
    response = client.post(
        '/api/optimize/',
        data=json.dumps(payload),
        content_type='application/json'
    )
    print(f"   Status: {response.status_code}")
    # 에러 응답 예상
    if response.status_code != 200:
        print("   ✅ PASS - 에러 처리 정상")
    else:
        print("   ⚠️  예상치 못한 성공 응답")
except Exception as e:
    print(f"   ❌ FAIL: {e}")

print("\n" + "=" * 60)
print("✅ 로컬 테스트 완료!")
print("=" * 60)
print("\n다음 단계:")
print("  1. Azure CLI 설치: https://docs.microsoft.com/cli/azure/install-azure-cli")
print("  2. 'az login' 명령 실행")
print("  3. AZURE_DEPLOY.md의 배포 단계 따르기")
print("=" * 60)
