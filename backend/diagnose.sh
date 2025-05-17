#!/bin/bash

echo "AI 뉴스 추천 시스템 진단 도구"
echo "============================"
echo

# 가상환경 활성화 시도
if [ -d "venv" ]; then
  source venv/bin/activate
  echo "가상환경 활성화 완료"
else
  echo "가상환경을 찾을 수 없습니다. 시스템 Python으로 진행합니다."
fi

# 진단 스크립트 실행
python run_diagnostics.py

# 결과 확인
if [ -f "diagnostics_results.json" ]; then
  echo
  echo "진단 결과가 저장되었습니다. 결과를 확인하고 문제를 해결하세요."
  echo "백엔드 실행 시 문제가 있는 경우 이 진단 결과를 참조하세요."
fi

echo
echo "진단 완료!"
