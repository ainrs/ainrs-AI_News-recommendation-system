#!/bin/bash

echo "AI 뉴스 추천 시스템 테스트 도구"
echo "============================"
echo "이 스크립트는 RSS 크롤러, MongoDB 연결, OpenAI API 및 뉴스 검색 기능을 테스트합니다."
echo

# 가상환경 활성화 시도
if [ -d "venv" ]; then
  source venv/bin/activate
  echo "가상환경 활성화 완료"
else
  echo "가상환경을 찾을 수 없습니다. 시스템 Python으로 진행합니다."
fi

# Python 확인
python -V || python3 -V

# 테스트 스크립트 실행
echo "테스트 실행 중..."
python test_rss.py

# 실행 결과 확인
TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
  echo
  echo "✅ 모든 테스트가 통과했습니다."
  echo "이제 백엔드 서버를 시작할 수 있습니다."
  echo "실행 명령어: ./start.sh"
else
  echo
  echo "❌ 일부 테스트가 실패했습니다."
  echo "오류를 확인하고 문제를 해결한 후 다시 시도하세요."
fi

echo
echo "테스트 완료!"
