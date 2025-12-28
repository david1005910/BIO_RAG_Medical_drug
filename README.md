# 💊 Medical RAG System - 의약품 추천 시스템

증상을 입력하면 AI가 적합한 의약품과 관련 질병 정보를 추천해주는 **RAG(Retrieval-Augmented Generation)** 기반 풀스택 웹 애플리케이션입니다.

![Glassmorphism UI](https://img.shields.io/badge/UI-Glassmorphism-blueviolet)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![React](https://img.shields.io/badge/React-18-61dafb)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178c6)

## 주요 기능

### 🔍 Hybrid Search (Dense + Sparse)
- **Dense Search**: OpenAI 임베딩 + PGVector 벡터 유사도 검색
- **Sparse Search**: BM25 기반 키워드 매칭 (한국어 2-gram 토크나이저)
- **Hybrid Merge**: Dense(70%) + Sparse(30%) 가중치 결합

### 🎯 Cohere Reranking
- `rerank-multilingual-v3.0` 모델로 검색 결과 재정렬
- 쿼리-문서 관련성 기반 최종 순위 결정

### 🤖 AI 응답 생성
- GPT-4o-mini 기반 맞춤형 의약품 추천 설명
- 질병 정보 통합 분석

### 🏥 질병 정보 통합
- 증상 관련 질병 정보 함께 제공
- 원인, 증상, 치료법, 예방법 안내

### 🎨 Glassmorphism UI
- 모던한 유리 효과 디자인
- 애니메이션 그라데이션 배경
- 반응형 레이아웃

## 검색 파이프라인

```
사용자 쿼리
    ↓
┌─────────────────────────────────────────────────────┐
│  1. Query Embedding (OpenAI text-embedding-3-small) │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│  2. Parallel Search                                  │
│     ├── Dense Search (PGVector cosine similarity)   │
│     └── Sparse Search (BM25 with Korean tokenizer)  │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│  3. Hybrid Merge (Dense 70% + Sparse 30%)           │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│  4. Cohere Reranking (rerank-multilingual-v3.0)     │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│  5. LLM Response Generation (GPT-4o-mini)           │
└─────────────────────────────────────────────────────┘
    ↓
최종 결과 (의약품 + 질병 정보 + AI 설명)
```

## 기술 스택

### Backend
| 기술 | 설명 |
|------|------|
| Python 3.11+ | 런타임 |
| FastAPI | 웹 프레임워크 |
| PostgreSQL + PGVector | 벡터 데이터베이스 |
| SQLAlchemy 2.0 | 비동기 ORM |
| OpenAI API | 임베딩 + LLM |
| Cohere API | Reranking |
| rank-bm25 | BM25 검색 |

### Frontend
| 기술 | 설명 |
|------|------|
| React 18 | UI 라이브러리 |
| TypeScript | 타입 안전성 |
| Vite | 빌드 도구 |
| Tailwind CSS | 스타일링 |
| TanStack Query | 서버 상태 관리 |
| React Router | 라우팅 |

## 빠른 시작

### 1. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일 편집:
```env
# 필수
OPENAI_API_KEY=sk-...        # OpenAI API 키
DATA_GO_KR_API_KEY=...       # 공공데이터포털 API 키

# 선택 (Reranking 활성화)
COHERE_API_KEY=...           # Cohere API 키

# 검색 설정
ENABLE_HYBRID_SEARCH=true    # Hybrid Search 활성화
DENSE_WEIGHT=0.7             # Dense 가중치
SPARSE_WEIGHT=0.3            # Sparse 가중치
ENABLE_RERANKING=true        # Reranking 활성화
```

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
| API 문서 (Swagger) | http://localhost:8000/docs |

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
uvicorn app.main:app --reload --port 8000
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
| `POST` | `/api/v1/search` | 증상 기반 의약품 검색 (Hybrid + Reranking) |
| `POST` | `/api/v1/chat` | 대화형 RAG 상담 (질병 정보 포함) |
| `GET` | `/api/v1/drugs/{id}` | 의약품 상세 정보 |
| `GET` | `/api/v1/drugs` | 의약품 목록 (페이지네이션) |
| `POST` | `/api/v1/admin/sync` | 데이터 동기화 (관리자) |
| `GET` | `/health` | 헬스 체크 |

### 검색 요청 예시

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "두통이 심하고 열이 나요", "top_k": 5}'
```

### 응답 예시

```json
{
  "results": [
    {
      "drug_id": "123",
      "item_name": "타이레놀정",
      "efficacy": "두통, 치통, 발열...",
      "similarity": 0.85,
      "relevance_score": 0.92
    }
  ],
  "disease_results": [
    {
      "name": "감기",
      "symptoms": "두통, 발열, 콧물...",
      "treatment": "충분한 휴식과 수분 섭취..."
    }
  ],
  "ai_response": "증상을 보니 감기 초기 증상으로 보입니다..."
}
```

## 프로젝트 구조

```
medical-rag-system/
├── backend/
│   ├── app/
│   │   ├── api/v1/           # API 라우터
│   │   │   ├── search.py     # 검색 API
│   │   │   ├── chat.py       # 채팅 API
│   │   │   ├── drugs.py      # 의약품 API
│   │   │   └── admin.py      # 관리자 API
│   │   ├── core/
│   │   │   └── config.py     # 설정 (Hybrid Search 가중치 등)
│   │   ├── external/
│   │   │   ├── openai_client.py   # OpenAI 클라이언트
│   │   │   ├── cohere_client.py   # Cohere Reranker
│   │   │   └── data_go_kr.py      # 공공데이터 API
│   │   ├── models/
│   │   │   ├── drug.py       # 의약품 모델
│   │   │   └── disease.py    # 질병 모델
│   │   └── services/
│   │       ├── rag_engine.py      # RAG 엔진 (핵심)
│   │       ├── bm25_search.py     # BM25 + Hybrid Search
│   │       ├── vector_db.py       # 벡터 DB 서비스
│   │       ├── embedding.py       # 임베딩 서비스
│   │       └── llm_service.py     # LLM 서비스
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ai/           # AI 응답 컴포넌트
│   │   │   ├── drug/         # 의약품 카드/리스트
│   │   │   ├── search/       # 검색 폼
│   │   │   ├── layout/       # 레이아웃 (Header, Footer)
│   │   │   └── common/       # 공통 컴포넌트
│   │   ├── pages/            # 페이지 컴포넌트
│   │   ├── hooks/            # 커스텀 훅
│   │   ├── services/         # API 클라이언트
│   │   └── types/            # TypeScript 타입
│   └── index.css             # Glassmorphism 스타일
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
└── scripts/
    ├── sync_data.py          # 데이터 동기화
    └── build_index.py        # 인덱스 구축
```

## 설정 옵션

### config.py 주요 설정

```python
# Hybrid Search
ENABLE_HYBRID_SEARCH = True   # Hybrid Search 활성화
DENSE_WEIGHT = 0.7            # Vector 검색 가중치
SPARSE_WEIGHT = 0.3           # BM25 검색 가중치

# Reranking
ENABLE_RERANKING = True       # Cohere Reranking 활성화
RERANK_MODEL = "rerank-multilingual-v3.0"
RERANK_TOP_N = 5              # Reranking 후 반환할 결과 수

# OpenAI
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
LLM_MODEL = "gpt-4o-mini"
```

## 성능

| 지표 | 값 |
|------|-----|
| BM25 인덱스 문서 수 | ~1,000개 |
| 평균 검색 응답 시간 | 1.5~3초 |
| AI 응답 포함 시 | 10~20초 |

## 면책 조항

⚠️ **주의사항**

이 시스템은 **참고 정보 제공**만을 목적으로 합니다.

- 의료 진단이나 처방을 대체하지 않습니다
- 실제 복약은 반드시 의사/약사와 상담 후 결정하세요
- 응급 상황에서는 즉시 119에 연락하거나 병원을 방문하세요

## 라이선스

MIT License

## 참고 자료

- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [Cohere Rerank](https://docs.cohere.com/reference/rerank)
- [PGVector](https://github.com/pgvector/pgvector)
- [BM25 (Okapi BM25)](https://en.wikipedia.org/wiki/Okapi_BM25)
- [공공데이터포털 e약은요 API](https://www.data.go.kr/data/15075057/openapi.do)
