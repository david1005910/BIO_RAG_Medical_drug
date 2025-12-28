# 💊 의약품 추천 RAG 시스템

증상을 입력하면 AI가 적합한 의약품을 추천해주는 RAG(Retrieval-Augmented Generation) 기반 풀스택 웹 애플리케이션입니다.

## 주요 기능

- **자연어 검색**: "두통이 심해요", "소화가 안돼요" 등 일상 언어로 의약품 검색
- **AI 맞춤 설명**: GPT-4가 검색 결과를 친절하게 설명
- **신뢰할 수 있는 데이터**: 공공데이터포털(data.go.kr) e약은요 API 기반

## 기술 스택

### Backend
- **Python 3.11+** + **FastAPI**
- **PostgreSQL** + **PGVector** (벡터 검색)
- **OpenAI API** (임베딩 + LLM)

### Frontend
- **React 18** + **TypeScript**
- **Tailwind CSS**
- **TanStack Query**

## 빠른 시작

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 API 키 입력
```

필수 API 키:
- `OPENAI_API_KEY`: [OpenAI Platform](https://platform.openai.com/api-keys)에서 발급
- `DATA_GO_KR_API_KEY`: [공공데이터포털](https://www.data.go.kr/data/15075057/openapi.do)에서 발급

### 2. Docker로 실행

```bash
# 서비스 시작
docker-compose -f docker/docker-compose.yml up -d

# 데이터 동기화 (최초 1회)
docker exec -it medical-rag-backend python scripts/sync_data.py --pages 10

# 로그 확인
docker-compose -f docker/docker-compose.yml logs -f
```

### 3. 접속

| 서비스 | URL |
|--------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API 문서 | http://localhost:8000/docs |

## 로컬 개발

### Backend

```bash
cd backend

# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -e ".[dev]"

# 개발 서버 실행
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

## API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/search` | 증상 기반 의약품 검색 |
| GET | `/api/v1/drugs/{id}` | 의약품 상세 정보 |
| GET | `/api/v1/drugs` | 의약품 목록 (페이지네이션) |
| POST | `/api/v1/chat` | 대화형 RAG 상담 |
| POST | `/api/v1/admin/sync` | 데이터 동기화 |
| GET | `/api/v1/health` | 헬스 체크 |

## 프로젝트 구조

```
medical-rag-system/
├── backend/                  # FastAPI 백엔드
│   ├── app/
│   │   ├── api/v1/          # API 라우터
│   │   ├── core/            # 설정
│   │   ├── db/              # 데이터베이스
│   │   ├── external/        # 외부 API 클라이언트
│   │   ├── models/          # SQLAlchemy 모델
│   │   ├── schemas/         # Pydantic 스키마
│   │   └── services/        # 비즈니스 로직 (RAG 엔진)
│   └── tests/
├── frontend/                 # React 프론트엔드
│   ├── src/
│   │   ├── components/      # UI 컴포넌트
│   │   ├── pages/           # 페이지
│   │   ├── hooks/           # 커스텀 훅
│   │   ├── services/        # API 클라이언트
│   │   └── types/           # TypeScript 타입
├── docker/                   # Docker 설정
├── scripts/                  # 유틸리티 스크립트
└── docs/                     # 문서
```

## 면책 조항

⚠️ **주의사항**

이 시스템은 **참고 정보 제공**만을 목적으로 합니다.

- 의료 진단이나 처방을 대체하지 않습니다
- 실제 복약은 반드시 의사/약사와 상담 후 결정하세요
- 응급 상황에서는 즉시 119에 연락하거나 병원을 방문하세요

## 라이선스

MIT License
