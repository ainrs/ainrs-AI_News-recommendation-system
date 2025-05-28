#!/bin/bash

# MongoDB null ID 문제 수정 스크립트
echo "MongoDB null ID 문제 수정 스크립트 실행..."

# 필요한 경우 가상 환경 활성화
# source venv/bin/activate

# 스크립트 실행
python fix_null_ids.py

echo "데이터베이스 수정 완료. 이제 서버를 재시작하세요."
