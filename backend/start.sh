#!/bin/bash

# 가상환경 설정
echo "파이썬 가상환경 설정 중..."
python3 -m venv venv || python -m venv venv || echo "가상환경 생성 실패, 시스템 파이썬 사용 계속합니다."

# 가상환경 활성화 시도
if [ -d "venv" ]; then
  source venv/bin/activate
  echo "가상환경 활성화 완료"
else
  echo "가상환경 없이 계속합니다."
fi

# 환경 변수 설정 확인
if [ ! -f ".env" ]; then
  echo "환경 변수 설정 파일이 없습니다. .env.example을 복사합니다."
  cp .env.example .env
fi

# pip 업그레이드
pip install --upgrade pip || pip3 install --upgrade pip || echo "pip 업그레이드 실패"

# requirements.txt 의존성 버전 충돌 자동 수정
# OpenAI 버전 업데이트
if grep -q "openai==" requirements.txt; then
  sed -i 's/openai==.*/openai>=1.77.0/g' requirements.txt || sed -i '' 's/openai==.*/openai>=1.77.0/g' requirements.txt
  echo "OpenAI 라이브러리 버전 업데이트 됨"
fi

# python-multipart 버전 업데이트
if grep -q "python-multipart==0.0.6" requirements.txt; then
  sed -i 's/python-multipart==0.0.6/python-multipart>=0.0.7/g' requirements.txt || sed -i '' 's/python-multipart==0.0.6/python-multipart>=0.0.7/g' requirements.txt
  echo "python-multipart 라이브러리 버전 업데이트 됨"
fi

# 의존성 설치
echo "의존성 설치 중..."
pip install -r requirements.txt || pip3 install -r requirements.txt

# MongoDB 상태 확인
echo "MongoDB 연결 상태 확인..."
# MongoDB URI가 .env 파일에 설정되어 있는지 확인
if grep -q "MONGODB_URI" .env; then
  echo "MongoDB URI가 .env 파일에 설정되어 있습니다."
else
  echo "경고: MongoDB URI가 .env 파일에 설정되어 있지 않습니다."
  echo "기본값인 mongodb://localhost:27017을 사용합니다."
  echo "MongoDB가 설치되어 있고 실행 중인지 확인하세요."
  echo "MONGODB_URI=mongodb://localhost:27017" >> .env
fi

# OpenAI API 키 설정 확인
if grep -q "OPENAI_API_KEY" .env && grep -q "OPENAI_API_KEY=sk-" .env; then
  echo "OpenAI API 키가 설정되어 있습니다."
else
  echo "경고: OpenAI API 키가 설정되어 있지 않거나 올바르지 않습니다."
  echo "일부 AI 기능이 작동하지 않을 수 있습니다."
fi

# 서버 실행
echo "백엔드 서버 시작 중..."
# 로그 레벨을 INFO로 설정하여 자세한 로그 출력
export LOG_LEVEL=INFO
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload || python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload || python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 에러 시 도움말
if [ $? -ne 0 ]; then
  echo "서버 시작 실패!"
  echo "다음 문제를 확인해보세요:"
  echo "1. MongoDB가 설치되어 있고 실행 중인지 확인"
  echo "2. 필요한 Python 패키지가 모두 설치되어 있는지 확인"
  echo "3. Python 3.6+ 버전인지 확인"
  echo "4. .env 파일에 올바른 환경 변수가 설정되어 있는지 확인"
fi
