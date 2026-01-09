"""문서 처리 API 엔드포인트

특정 디렉토리의 문서를 파싱하고 검색 인덱스에 추가합니다.
"""
import json
import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.models.drug import DocumentVector
from app.services.document_service import get_document_service
from app.services.embedding import get_embedding_service

logger = logging.getLogger(__name__)

router = APIRouter()


class DocumentInfo(BaseModel):
    """문서 정보"""
    filename: str
    filepath: str
    file_type: str
    page_count: int
    content_length: int


class DocumentListResponse(BaseModel):
    """문서 목록 응답"""
    documents: List[DocumentInfo]
    total: int
    directory: str


class ParseResponse(BaseModel):
    """파싱 응답"""
    success: bool
    message: str
    parsed_count: int
    documents: List[DocumentInfo]


class IndexResponse(BaseModel):
    """인덱싱 응답"""
    success: bool
    message: str
    indexed_count: int
    chunk_count: int


class DocumentSearchResult(BaseModel):
    """문서 검색 결과"""
    chunk_id: str
    document_id: str
    content: str
    similarity: float


class SearchResponse(BaseModel):
    """검색 응답"""
    results: List[DocumentSearchResult]
    query: str


@router.get("/list", response_model=DocumentListResponse)
async def list_documents():
    """문서 디렉토리의 모든 문서 목록 조회

    지원 형식: PDF, DOCX, HTML, TXT, MD
    """
    try:
        doc_service = get_document_service()
        documents = doc_service.list_documents()

        doc_infos = []
        for filepath in documents:
            import os
            from pathlib import Path

            filename = Path(filepath).name
            file_ext = Path(filepath).suffix.lower()

            doc_infos.append(DocumentInfo(
                filename=filename,
                filepath=filepath,
                file_type=file_ext[1:] if file_ext else "unknown",
                page_count=0,  # 아직 파싱 전
                content_length=os.path.getsize(filepath)
            ))

        return DocumentListResponse(
            documents=doc_infos,
            total=len(doc_infos),
            directory=settings.DOCUMENTS_DIR
        )

    except Exception as e:
        logger.error(f"문서 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse", response_model=ParseResponse)
async def parse_documents():
    """디렉토리의 모든 문서 파싱

    문서를 파싱하여 텍스트를 추출합니다.
    인덱싱은 별도 엔드포인트를 사용하세요.
    """
    try:
        doc_service = get_document_service()
        parsed_docs = await doc_service.parse_all_documents()

        doc_infos = [
            DocumentInfo(
                filename=doc.filename,
                filepath=doc.filepath,
                file_type=doc.file_type,
                page_count=doc.page_count,
                content_length=len(doc.content)
            )
            for doc in parsed_docs
        ]

        return ParseResponse(
            success=True,
            message=f"{len(parsed_docs)}개 문서 파싱 완료",
            parsed_count=len(parsed_docs),
            documents=doc_infos
        )

    except Exception as e:
        logger.error(f"문서 파싱 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index", response_model=IndexResponse)
async def index_documents(
    session: AsyncSession = Depends(get_db),
    chunk_size: int = settings.DOC_CHUNK_SIZE,
    overlap: int = settings.DOC_CHUNK_OVERLAP,
):
    """문서를 파싱하고 벡터 인덱스에 추가

    Args:
        chunk_size: 청크 크기 (문자 수)
        overlap: 청크 간 오버랩

    문서를 청크로 분할하고 임베딩을 생성하여
    벡터 DB에 저장합니다.
    """
    try:
        doc_service = get_document_service()
        embedding_service = get_embedding_service()

        # 1. 문서 파싱
        logger.info("📄 문서 파싱 시작...")
        parsed_docs = await doc_service.parse_all_documents()

        if not parsed_docs:
            return IndexResponse(
                success=False,
                message="파싱할 문서가 없습니다",
                indexed_count=0,
                chunk_count=0
            )

        # 2. 청크 분할
        all_chunks = []
        for doc in parsed_docs:
            chunks = doc_service.chunk_document(
                doc,
                chunk_size=chunk_size,
                overlap=overlap
            )
            all_chunks.extend(chunks)
            logger.info(f"📝 {doc.filename}: {len(chunks)}개 청크 생성")

        if not all_chunks:
            return IndexResponse(
                success=False,
                message="생성된 청크가 없습니다",
                indexed_count=len(parsed_docs),
                chunk_count=0
            )

        # 3. 임베딩 생성
        logger.info(f"🧠 {len(all_chunks)}개 청크 임베딩 생성 중...")
        texts = [chunk["content"] for chunk in all_chunks]
        embeddings = await embedding_service.embed_batch(texts)

        # 4. DocumentVector 테이블에 저장
        logger.info("💾 문서 벡터 DB에 저장 중...")

        # 기존 문서 벡터 삭제 (재인덱싱 시)
        await session.execute(
            DocumentVector.__table__.delete()
        )

        # 새 벡터 추가
        count = 0
        for chunk, embedding in zip(all_chunks, embeddings):
            doc_vector = DocumentVector(
                id=uuid.uuid4(),
                document_id=chunk["document_id"],
                chunk_id=chunk["chunk_id"],
                embedding=embedding,
                content=chunk["content"],
                chunk_index=chunk["metadata"].get("chunk_index", 0),
                extra_data=json.dumps(chunk["metadata"]),
            )
            session.add(doc_vector)
            count += 1

        await session.commit()
        logger.info(f"✅ {count}개 문서 청크 인덱싱 완료")

        return IndexResponse(
            success=True,
            message=f"{len(parsed_docs)}개 문서, {count}개 청크 인덱싱 완료",
            indexed_count=len(parsed_docs),
            chunk_count=count
        )

    except Exception as e:
        logger.error(f"문서 인덱싱 실패: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
):
    """문서 파일 업로드

    업로드된 파일을 문서 디렉토리에 저장합니다.
    인덱싱은 별도로 수행해야 합니다.
    """
    try:
        import os
        from pathlib import Path

        # 파일 확장자 검증
        filename = file.filename
        file_ext = Path(filename).suffix.lower()
        supported = {'.pdf', '.docx', '.html', '.htm', '.txt', '.md'}

        if file_ext not in supported:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 파일 형식: {file_ext}. 지원: {supported}"
            )

        # 파일 저장
        filepath = os.path.join(settings.DOCUMENTS_DIR, filename)

        with open(filepath, 'wb') as f:
            content = await file.read()
            f.write(content)

        logger.info(f"✅ 파일 업로드 완료: {filename} ({len(content)} bytes)")

        return {
            "success": True,
            "message": f"파일 업로드 완료: {filename}",
            "filepath": filepath,
            "size": len(content)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=SearchResponse)
async def search_documents(
    query: str,
    top_k: int = 5,
    session: AsyncSession = Depends(get_db),
):
    """문서 내 검색

    Args:
        query: 검색 쿼리
        top_k: 반환할 결과 수

    Returns:
        유사한 문서 청크 목록
    """
    try:
        embedding_service = get_embedding_service()

        # 쿼리 임베딩
        query_embedding = await embedding_service.embed_text(query)

        # DocumentVector 테이블에서 유사도 검색

        result = await session.execute(
            select(
                DocumentVector.chunk_id,
                DocumentVector.document_id,
                DocumentVector.content,
                DocumentVector.embedding.cosine_distance(query_embedding).label("distance")
            )
            .order_by("distance")
            .limit(top_k)
        )

        rows = result.all()

        search_results = [
            DocumentSearchResult(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                content=row.content[:500] if row.content else "",  # 미리보기 500자
                similarity=round(1 - row.distance, 4)  # cosine distance to similarity
            )
            for row in rows
        ]

        logger.info(f"🔍 문서 검색 완료: '{query}' -> {len(search_results)}개 결과")

        return SearchResponse(
            results=search_results,
            query=query
        )

    except Exception as e:
        logger.error(f"문서 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
