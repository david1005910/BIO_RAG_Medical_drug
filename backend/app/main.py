"""FastAPI 애플리케이션 메인 엔트리포인트"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import search, drugs, chat, admin, graph
from app.core.config import settings
from app.services.qdrant_service import initialize_qdrant
from app.services.splade_service import initialize_splade
from app.external.neo4j_client import initialize_neo4j, close_neo4j

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시
    logger.info("🚀 Medical RAG API 시작...")
    logger.info(f"📊 LLM 모델: {settings.LLM_MODEL}")
    logger.info(f"📊 임베딩 모델: {settings.EMBEDDING_MODEL}")

    # Qdrant + SPLADE 초기화 (활성화된 경우)
    if settings.ENABLE_QDRANT:
        logger.info("🔧 Qdrant + SPLADE 서비스 초기화 중...")
        qdrant_ok = await initialize_qdrant()
        splade_ok = await initialize_splade()
        if qdrant_ok and splade_ok:
            logger.info("✅ Qdrant + SPLADE 서비스 초기화 완료")
        else:
            logger.warning("⚠️ Qdrant/SPLADE 초기화 실패, PGVector + BM25로 폴백")
    else:
        logger.info("📊 PGVector + BM25 모드 사용")

    # Neo4j 그래프 DB 초기화 (활성화된 경우)
    if settings.ENABLE_NEO4J:
        logger.info("🔧 Neo4j 그래프 DB 초기화 중...")
        neo4j_ok = await initialize_neo4j()
        if neo4j_ok:
            logger.info("✅ Neo4j 그래프 DB 초기화 완료")
        else:
            logger.warning("⚠️ Neo4j 초기화 실패, 그래프 기능 비활성화")

    yield
    # 종료 시
    logger.info("👋 Medical RAG API 종료...")
    await close_neo4j()


def create_app() -> FastAPI:
    """FastAPI 앱 팩토리"""
    app = FastAPI(
        title="Medical RAG API",
        description="""
## 💊 의약품 추천 RAG 시스템 API

사용자의 증상을 분석하여 적합한 의약품을 추천하는 AI 기반 시스템입니다.

### 주요 기능

- **증상 기반 검색**: 자연어로 증상을 입력하면 관련 의약품 추천
- **AI 설명**: LLM이 검색 결과를 친절하게 설명
- **의약품 상세 정보**: 효능, 용법, 주의사항 등 상세 정보 제공

### ⚠️ 면책 조항

이 시스템은 **참고 정보 제공**만을 목적으로 합니다.
실제 복약은 반드시 의사/약사와 상담 후 결정하세요.
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    app.include_router(search.router, prefix="/api/v1", tags=["검색"])
    app.include_router(drugs.router, prefix="/api/v1", tags=["의약품"])
    app.include_router(chat.router, prefix="/api/v1", tags=["대화"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["관리자"])
    app.include_router(graph.router, prefix="/api/v1", tags=["그래프"])

    @app.get("/", tags=["Root"])
    async def root():
        """API 루트"""
        return {
            "message": "💊 Medical RAG API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/v1/admin/health",
        }

    @app.get("/api/v1/health", tags=["Health"])
    async def health():
        """헬스 체크 (v1)"""
        return {"status": "healthy"}

    return app


# 앱 인스턴스 생성
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
