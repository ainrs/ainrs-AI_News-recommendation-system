<div align="center">
  <h1>🎓 배재대학교 사이버보안학과</h1>
  <p><strong>2025학년도 1학기 창의자율과제</strong></p>
</div>

---

# 개인화된 AI 뉴스 추천 시스템

> **2025학년도 1학기 창의자율과제**
> **지도교수: 함형민 교수님**
> **개발팀: 정일근, 유민석, 오지윤, 한승연**

---

##  창의자율과제 소개

본 프로젝트는 2025학년도 1학기 배재대학교 창의자율과제의 일환으로 개발되었습니다.
디지털 정보의 홍수 속에서 개인의 관심사와 성향에 맞는 뉴스를 효과적으로 제공하는 AI 기반 추천 시스템을 구현했습니다.

### 연구 목표

- 사용자의 선호도와 행동 패턴을 분석하여 개인화된 뉴스 추천 서비스 개발
- 다양한 관점의 뉴스를 균형 있게 제공하여 정보 편향성 문제 해결
- 최신 AI 기술을 활용한 효율적인 콘텐츠 분석 및 추천 알고리즘 구현

### 연구 성과

- 하이브리드 추천 시스템 구현 (협업 필터링 + 콘텐츠 기반 필터링)
- 뉴스 콘텐츠의 자동 분류 및 요약 기능 개발
- 사용자 활동 데이터 기반 지속적인 추천 품질 개선
- 실시간 뉴스 크롤링 및 분석 파이프라인 구축

---

##  프로젝트 소개

사용자의 관심사와 활동 패턴을 분석하여 개인화된 뉴스 추천을 제공하는 AI 기반 뉴스 플랫폼입니다.
다양한 국내외 뉴스 소스로부터 콘텐츠를 수집하고, 최신 AI 기술을 활용하여 사용자에게 최적화된 뉴스를 추천합니다.

본 시스템은 협업 필터링(Collaborative Filtering), 콘텐츠 기반 필터링(Content-based Filtering),
그리고 최신 자연어 처리 모델을 활용한 하이브리드 추천 알고리즘을 구현하여 다양한 관점의 뉴스를 균형 있게 제공합니다.

---

##  주요 기능

###  개인화된 뉴스 추천

- 사용자의 과거 읽기 기록, 좋아요, 북마크 등 활동 데이터를 기반으로 관심사 프로필 구축
- 협업 필터링과 콘텐츠 기반 필터링을 결합한 하이브리드 추천 알고리즘 적용
- 신뢰도 높은 다양한 소스의 뉴스 제공

###  AI 기반 콘텐츠 분석

- OpenAI의 임베딩 모델을 활용한 뉴스 콘텐츠 벡터화
- 토픽 모델링을 통한 뉴스 기사 자동 분류
- 감성 분석 및 신뢰도 평가를 통한 양질의 콘텐츠 필터링

###  고급 검색 및 필터링

- 실시간 뉴스 검색 기능
- 카테고리, 출처, 날짜별 필터링
- 개인 맞춤형 검색 결과 제공

###  사용자 계정 관리

- 이메일 인증을 통한 안전한 계정 생성
- 사용자 활동 데이터 관리
- 개인화된 프로필 설정

###  반응형 웹 디자인

- 모바일, 태블릿, 데스크톱 등 다양한 디바이스에 최적화된 UI/UX
- 모던한 디자인과 직관적인 사용자 인터페이스

---

##  기술 스택

### 프론트엔드

- **Next.js**: React 기반 서버 사이드 렌더링 프레임워크
- **Tailwind CSS**: 유틸리티 우선 CSS 프레임워크
- **Shadcn/UI**: 컴포넌트 라이브러리
- **TypeScript**: 정적 타입 지원을 위한 JavaScript 확장

### 백엔드

- **FastAPI**: 고성능 Python 백엔드 프레임워크
- **Motor & PyMongo**: MongoDB 비동기/동기 드라이버
- **MongoDB Atlas**: 클라우드 데이터베이스
- **LangChain**: AI 모델 통합 프레임워크
- **OpenAI API**: 텍스트 임베딩 및 분석

### AI 및 ML

- **scikit-learn**: 머신러닝 알고리즘 구현
- **Sentence Transformers**: 텍스트 임베딩
- **ChromaDB & FAISS**: 벡터 데이터베이스
- **Retrieval-Augmented Generation (RAG)**: 지식 기반 콘텐츠 분석
- **BERT4Rec**: 시퀀스 기반 추천 알고리즘

### 임베딩 및 AI 모델

- **텍스트 임베딩 모델**:
  - **한국어 특화 모델**: `jhgan/ko-sroberta-multitask` - 한국어 텍스트에 최적화된 임베딩 생성
  - **다국어 모델**: `sentence-transformers/distiluse-base-multilingual-cased-v1` - 다양한 언어의 검색 및 추천 지원
  - **감정분석 특화 모델**: `sentence-transformers/all-mpnet-base-v2` - 정서 분석에 특화된 고성능 임베딩
  - **OpenAI 임베딩**: `text-embedding-3-small` - 고품질 범용 임베딩

- **자연어 처리 모델**:
  - **텍스트 생성**: `gpt-3.5-turbo` - 요약, 분류, QA 등 다양한 텍스트 생성 작업
  - **감정 분석**: `distilbert-base-uncased-finetuned-sst-2-english` - 텍스트 감정 분석
  - **신뢰도 분석**: `distilbert-base-uncased` 기반 커스텀 모델 - 뉴스 콘텐츠 신뢰도 평가

- **추천 시스템 모델**:
  - **협업 필터링**: Matrix Factorization 기반 사용자-아이템 추천
  - **콘텐츠 기반 필터링**: 코사인 유사도 기반 벡터 검색
  - **시퀀스 기반 추천**: BERT4Rec 기반 사용자 행동 시퀀스 모델링

---

##  설치 및 실행 방법

### 사전 요구사항

- Python 3.10+ (백엔드)
- Node.js 16+ 및 npm/bun (프론트엔드)
- MongoDB Atlas 계정
- OpenAI API 키 (뉴스 분석 및 추천 기능에 필요)
- SMTP 서버 계정 (이메일 인증 기능에 필요)

### 환경 설정

#### 1. MongoDB Atlas 설정

- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)에서 계정 생성 및 클러스터 설정
- IP 화이트리스트 추가 및 데이터베이스 사용자 생성
- 연결 문자열 복사하여 백엔드 `.env` 파일에 추가

#### 2. 백엔드 환경 변수 설정

백엔드 디렉토리의 `.env` 파일에 다음 정보를 설정합니다:

```
# MongoDB 연결 설정
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true&appName=<AppName>
MONGODB_DB_NAME=news_recommendation

# OpenAI API 키
OPENAI_API_KEY=your_openai_api_key

# 이메일 설정 (Naver SMTP 예시)
EMAIL_PROVIDER=naver
NAVER_MAIL_USERNAME=your_email@naver.com
NAVER_MAIL_PASSWORD=your_password
NAVER_MAIL_FROM="버라이어티.AI <your_email@naver.com>"
NAVER_MAIL_PORT=465
NAVER_MAIL_SERVER=smtp.naver.com
NAVER_MAIL_TLS=False
NAVER_MAIL_SSL=True
```

#### 3. 프론트엔드 환경 변수 설정

프론트엔드 디렉토리의 `.env.local` 파일에 다음 정보를 설정합니다:

```
# 백엔드 API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# 기타 설정
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

---

### 프론트엔드 실행 (variety-ai-news)

```bash
# 프론트엔드 디렉토리로 이동
cd frontend/frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

### 백엔드 실행

```bash
# 백엔드 디렉토리로 이동
cd backend/backend

# Windows에서 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate

# 또는 macOS/Linux에서 가상환경 활성화
# python -m venv venv
# source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 데이터 관리 스크립트 실행

백엔드에는 데이터 관리를 위한 여러 유틸리티 스크립트가 제공됩니다. 이 스크립트들을 사용하여 데이터를 효율적으로 관리하고 문제를 해결할 수 있습니다.

#### 데이터 수정 스크립트 (fix_data.py)

이 스크립트는 기존 데이터베이스의 뉴스 데이터 중 카테고리가 비어있거나 내용이 비어있는 데이터를 자동으로 보정하는 기능을 합니다.

```bash
# 백엔드 디렉토리에서 실행
cd backend/backend
python fix_data.py
```

또는 제공된 쉘 스크립트를 사용하여 실행할 수 있습니다:

```bash
# 백엔드 디렉토리에서 실행
cd backend/backend
chmod +x fix_data.sh  # 처음 실행 시 실행 권한 부여
./fix_data.sh
```

이 스크립트는 다음 작업을 수행합니다:
- 비어있는 카테고리 필드를 뉴스 제목 기반으로 추론하여 채웁니다
- 비어있는 내용(content) 필드를 요약 또는 제목으로 대체합니다
- 누락된 이미지 URL에 기본 이미지를 설정합니다

#### 진단 스크립트 (diagnose.sh)

시스템의 상태를 진단하고 문제를 식별하는 스크립트입니다.

```bash
# 백엔드 디렉토리에서 실행
cd backend/backend
chmod +x diagnose.sh  # 처음 실행 시 실행 권한 부여
./diagnose.sh
```

이 스크립트는 다음 항목을 확인합니다:
- MongoDB 연결 상태
- API 엔드포인트 정상 작동 여부
- 데이터 상태 및 무결성
- 임베딩 모델 및 벡터 저장소 상태

### 백엔드와 프론트엔드 연동

프론트엔드와 백엔드는 다음과 같이 연동됩니다:

1. 백엔드 서버는 `http://localhost:8000`에서 실행됩니다.
2. 프론트엔드 Next.js 애플리케이션은 `http://localhost:3000`에서 실행됩니다.
3. 프론트엔드는 백엔드 API를 호출하여 데이터를 가져오고 사용자 인터랙션을 처리합니다.
4. 동시에 두 서버를 실행해야 전체 기능을 사용할 수 있습니다.

#### CORS 설정

백엔드의 `app/core/config.py` 파일에서 CORS 설정을 확인하고 필요에 따라 수정합니다:

```python
BACKEND_CORS_ORIGINS = [
    "http://localhost:3000",  # 프론트엔드 개발 서버
    "http://localhost:8000",  # 백엔드 서버
    # 추가 오리진이 필요한 경우 여기에 추가
]
```

---

##  알려진 이슈 및 해결 방법

### MongoDB 연결 문제 해결

SSL 핸드셰이크 오류가 발생하는 경우 다음과 같이 해결할 수 있습니다:

1. `.env` 파일의 MongoDB URI에 `tlsAllowInvalidCertificates=true` 파라미터를 추가합니다:

```
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true&appName=<AppName>
```

2. `app/db/mongodb.py` 파일에서 MongoDB 클라이언트 연결 설정에 SSL 옵션을 추가합니다:

```python
client = MongoClient(
    settings.MONGODB_URI,
    serverSelectionTimeoutMS=5000,
    ssl=True,
    ssl_cert_reqs='CERT_NONE',
    tlsAllowInvalidCertificates=True
)
```

3. 비동기 Motor 클라이언트에도 동일한 설정을 적용합니다:

```python
_async_client = motor.motor_asyncio.AsyncIOMotorClient(
    settings.MONGODB_URI,
    serverSelectionTimeoutMS=5000,
    ssl=True,
    ssl_cert_reqs='CERT_NONE',
    tlsAllowInvalidCertificates=True
)
```

이러한 설정은 SSL 인증서 검증 관련 문제를 해결하여 MongoDB Atlas에 성공적으로 연결할 수 있게 해줍니다.

---

##  프로젝트 구조

### 백엔드 구조

```
backend/
├── app/
│   ├── core/              # 설정 및 코어 기능
│   ├── db/                # 데이터베이스 연결 및 모델
│   ├── models/            # 데이터 모델
│   ├── routers/           # API 엔드포인트
│   ├── services/          # 비즈니스 로직 서비스
│   └── utils/             # 유틸리티 함수
├── data/                  # 데이터 저장소 (벡터 DB 등)
├── .env                   # 환경 변수
└── requirements.txt       # 의존성 목록
```

### 프론트엔드 구조

```
variety-ai-news/
├── src/
│   ├── app/               # 페이지 컴포넌트
│   ├── components/        # UI 컴포넌트
│   ├── contexts/          # React 컨텍스트
│   ├── hooks/             # 커스텀 훅
│   ├── lib/               # 유틸리티 함수
│   ├── services/          # API 서비스
│   └── styles/            # 스타일 파일
├── public/                # 정적 파일
└── package.json           # 의존성 목록
```

---

##  추천 시스템 아키텍처

본 프로젝트의 추천 시스템은 다음과 같은 아키텍처로 구현되었습니다:

1. **데이터 수집 파이프라인**
   - RSS 피드 크롤링을 통한 뉴스 데이터 수집
   - 콘텐츠 정제 및 메타데이터 추출

2. **AI 분석 파이프라인**
   - OpenAI 임베딩 모델을 통한 콘텐츠 벡터화
   - 토픽 모델링을 통한 카테고리 분류
   - 감성 분석 및 신뢰도 평가

3. **추천 엔진**
   - 사용자-아이템 협업 필터링 (유사한 사용자 기반)
   - 콘텐츠 기반 필터링 (뉴스 콘텐츠 유사도 기반)
   - 하이브리드 앙상블 방법론 (가중치 기반 결합)

4. **추천 최적화**
   - 다양성 및 신선도 고려
   - 인기도와 관련성의 균형
   - 콜드 스타트 문제 해결을 위한 전략

### 콜드 스타트 문제 해결 전략

본 시스템은 새로운 사용자나 새로운 뉴스 콘텐츠에 대한 "콜드 스타트" 문제를 해결하기 위해 다양한 전략을 구현했습니다:

1. **새로운 사용자를 위한 전략**:
   - **다양성 기반 초기 추천**: 다양한 카테고리의 인기 있는 뉴스를 제공하여 사용자의 관심사를 빠르게 탐색
   - **BERT4Rec 모델 활용**: 짧은 상호작용 시퀀스에서도 효과적인 추천 생성
   - **단계적 개인화**: 최소한의 상호작용 데이터로부터 점진적으로 추천 정확도 향상

2. **새로운 뉴스 콘텐츠 처리**:
   - **실시간 콘텐츠 임베딩**: 신규 기사 수집 즉시 임베딩 생성 및 벡터 저장소에 인덱싱
   - **콘텐츠 기반 유사도 계산**: 기존 뉴스와의 유사도를 통해 신규 뉴스 추천 가능성 판단
   - **하이브리드 가중치 조정**: 신규 콘텐츠에 대한 가중치를 높여 노출 기회 확대

3. **하이브리드 접근법**:
   - 협업 필터링 결과가 부족할 경우 콘텐츠 기반 필터링 비중 증가
   - 트렌딩 뉴스와 개인화된 추천의 균형 있는 조합
   - 능동적 학습 전략을 통한 사용자 피드백 수집 최적화

이러한 전략들은 `BERT4RecService` 및 `RecommendationService` 클래스에 구현되어 있으며, 사용자 경험을 저해하지 않으면서 효과적인 추천을 제공합니다.

---

##  기여 방법

1. 본 레포지토리를 포크합니다.
2. 새로운 기능 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`).
3. 변경사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`).
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`).
5. Pull Request를 생성합니다.

---

##  라이센스

본 프로젝트는 MIT 라이센스 하에 배포됩니다.
자세한 내용은 `LICENSE` 파일을 참조하세요.

---

##  연락처

프로젝트 관련 문의는 이슈 트래커를 통해 남겨주세요.

---

##  발전 계획 및 미래 방향성

본 프로젝트는 다음과 같은 방향으로 발전시킬 계획입니다:

1. **멀티모달 콘텐츠 지원**: 텍스트뿐만 아니라 이미지, 비디오 등 다양한 형식의 뉴스 콘텐츠를 분석하고 추천할 수 있는 기능 추가
2. **개인화 수준 향상**: 사용자 피드백을 더 효과적으로 활용한 추천 알고리즘 개선
3. **다국어 지원**: 다양한 언어의 뉴스를 번역하고 추천할 수 있는 기능 구현
4. **모바일 애플리케이션**: 네이티브 모바일 앱 개발을 통한 접근성 향상
5. **커뮤니티 기능**: 사용자 간 뉴스 공유 및 토론 기능 추가

---

© 2025 배재대학교 창의자율과제 프로젝트
