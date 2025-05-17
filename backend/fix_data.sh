#!/bin/bash

# 현재 디렉토리로 이동
cd "$(dirname "$0")"

# 환경변수 로드
source .env

# 스크립트 실행
echo "🔧 데이터 수정 스크립트 실행 중..."
python -m fix_data

echo "✅ 데이터 수정 완료!"
