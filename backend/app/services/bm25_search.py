"""BM25 검색 서비스 - Sparse Search 구현"""
import logging
import re
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

from rank_bm25 import BM25Okapi
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class KoreanTokenizer:
    """한국어 토크나이저 - 형태소 분석 없이 문자 기반 토큰화"""

    def __init__(self):
        # 불용어 리스트
        self.stopwords = {
            '이', '가', '을', '를', '의', '에', '에서', '으로', '로', '와', '과',
            '는', '은', '도', '만', '까지', '부터', '에게', '한테', '께',
            '하다', '있다', '되다', '없다', '않다', '이다', '아니다',
            '그', '저', '이것', '그것', '저것', '여기', '거기', '저기',
            '및', '등', '것', '수', '때', '중', '내', '위', '후', '전',
            '좀', '너무', '매우', '정말', '아주', '많이', '조금', '약간',
            '해요', '합니다', '해주세요', '주세요', '싶어요', '같아요',
        }

        # 증상 관련 키워드 (가중치 높게)
        self.symptom_keywords = {
            '두통', '열', '발열', '기침', '콧물', '재채기', '인후통', '목아픔',
            '복통', '설사', '변비', '구토', '소화불량', '속쓰림', '위통',
            '근육통', '관절통', '요통', '허리', '어깨', '무릎',
            '피로', '무기력', '권태', '졸음', '불면', '두드러기',
            '가려움', '발진', '염증', '통증', '붓기', '부종',
            '어지러움', '현기증', '메스꺼움', '구역질',
            '감기', '독감', '알레르기', '비염', '천식',
        }

    def tokenize(self, text: str) -> List[str]:
        """텍스트를 토큰으로 분리

        Args:
            text: 입력 텍스트

        Returns:
            토큰 리스트
        """
        if not text:
            return []

        # 소문자 변환 및 특수문자 제거
        text = text.lower()
        text = re.sub(r'[^\w\s가-힣]', ' ', text)

        # 공백으로 분리
        tokens = text.split()

        # 불용어 제거 및 짧은 토큰 제거
        tokens = [t for t in tokens if t not in self.stopwords and len(t) > 1]

        # N-gram 생성 (2-gram, 3-gram)
        ngrams = []
        for token in tokens:
            ngrams.append(token)

            # 한글인 경우 N-gram 생성
            if re.match(r'^[가-힣]+$', token) and len(token) >= 2:
                # 2-gram
                for i in range(len(token) - 1):
                    ngrams.append(token[i:i+2])
                # 3-gram (긴 단어의 경우)
                if len(token) >= 3:
                    for i in range(len(token) - 2):
                        ngrams.append(token[i:i+3])

            # 증상 키워드면 가중치 추가 (중복 추가)
            if token in self.symptom_keywords:
                ngrams.append(token)
                ngrams.append(token)

        return ngrams


class BM25SearchService:
    """BM25 기반 Sparse 검색 서비스"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.tokenizer = KoreanTokenizer()
        self.bm25: Optional[BM25Okapi] = None
        self.documents: List[Dict] = []
        self.corpus: List[List[str]] = []
        self._initialized = False

    async def initialize(self) -> None:
        """BM25 인덱스 초기화 - 모든 의약품 문서 로드"""
        if self._initialized:
            return

        logger.info("🔧 BM25 인덱스 초기화 중...")

        # 모든 의약품 문서 로드
        query = text("""
            SELECT
                id as drug_id,
                item_name,
                entp_name,
                efficacy,
                use_method,
                caution_info,
                side_effects
            FROM drugs
            WHERE efficacy IS NOT NULL
        """)

        result = await self.session.execute(query)
        rows = result.fetchall()

        self.documents = []
        self.corpus = []

        for row in rows:
            # 문서 생성 (검색 대상 텍스트)
            doc_text = self._create_document_text(
                item_name=row.item_name,
                efficacy=row.efficacy,
                use_method=row.use_method,
                caution_info=row.caution_info,
            )

            # 토큰화
            tokens = self.tokenizer.tokenize(doc_text)

            if tokens:
                self.documents.append({
                    "drug_id": row.drug_id,
                    "item_name": row.item_name,
                    "entp_name": row.entp_name,
                    "efficacy": row.efficacy,
                    "use_method": row.use_method,
                    "caution_info": row.caution_info,
                    "side_effects": row.side_effects,
                })
                self.corpus.append(tokens)

        # BM25 인덱스 생성
        if self.corpus:
            self.bm25 = BM25Okapi(self.corpus)
            self._initialized = True
            logger.info(f"✅ BM25 인덱스 생성 완료: {len(self.documents)}개 문서")
        else:
            logger.warning("⚠️ BM25 인덱스 생성 실패: 문서 없음")

    def _create_document_text(
        self,
        item_name: str,
        efficacy: Optional[str],
        use_method: Optional[str],
        caution_info: Optional[str],
    ) -> str:
        """검색용 문서 텍스트 생성"""
        parts = [item_name or ""]

        if efficacy:
            parts.append(efficacy)
        if use_method:
            parts.append(use_method[:200])  # 용법은 앞부분만
        if caution_info:
            parts.append(caution_info[:200])  # 주의사항도 앞부분만

        return " ".join(parts)

    async def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[Dict]:
        """BM25 검색 수행

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수

        Returns:
            BM25 점수 순으로 정렬된 결과 리스트
        """
        # 인덱스 초기화 확인
        if not self._initialized:
            await self.initialize()

        if not self.bm25 or not self.documents:
            logger.warning("BM25 인덱스가 없습니다.")
            return []

        # 쿼리 토큰화
        query_tokens = self.tokenizer.tokenize(query)

        if not query_tokens:
            return []

        # BM25 점수 계산
        scores = self.bm25.get_scores(query_tokens)

        # 상위 k개 결과 추출
        scored_docs = list(zip(range(len(scores)), scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scored_docs[:top_k]:
            if score > 0:  # 점수가 0보다 큰 것만
                doc = self.documents[idx].copy()
                doc["bm25_score"] = float(score)
                results.append(doc)

        logger.info(f"🔍 BM25 검색 완료: {len(results)}개 결과 (쿼리: {query[:30]}...)")
        return results

    async def refresh_index(self) -> None:
        """인덱스 새로고침"""
        self._initialized = False
        self.bm25 = None
        self.documents = []
        self.corpus = []
        await self.initialize()


class HybridSearchService:
    """Hybrid Search - Dense (Vector) + Sparse (BM25) 결합

    점수 체계:
    - Dense Score: 0~1 (코사인 유사도)
    - Sparse Score: 0~50 기준으로 0~1로 정규화 (50으로 나눔, 최대 1)
    - Hybrid Score: dense * 0.7 + sparse * 0.3
    """

    # BM25 점수 정규화 기준 (최대 점수)
    # 실제 테스트 결과 raw BM25 점수가 32-35 범위이므로 50으로 설정
    BM25_MAX_SCORE = 50.0

    def __init__(
        self,
        session: AsyncSession,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
    ):
        self.session = session
        self.bm25_service = BM25SearchService(session)
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight

    async def initialize(self) -> None:
        """BM25 인덱스 초기화"""
        await self.bm25_service.initialize()

    def _normalize_bm25_score(self, score: float) -> float:
        """BM25 점수를 0-1 범위로 정규화 (50점 기준)

        Args:
            score: 원본 BM25 점수 (일반적으로 0~50 범위)

        Returns:
            0~1 범위로 정규화된 점수
        """
        normalized = score / self.BM25_MAX_SCORE
        return min(normalized, 1.0)  # 최대 1.0으로 제한

    async def search(
        self,
        query: str,
        dense_results: List[Dict],
        top_k: int = 5,
    ) -> List[Dict]:
        """Hybrid 검색 수행

        Args:
            query: 검색 쿼리
            dense_results: Vector search 결과 (similarity 포함)
            top_k: 반환할 결과 수

        Returns:
            Hybrid 점수 순으로 정렬된 결과 리스트
        """
        # BM25 검색 수행
        bm25_results = await self.bm25_service.search(query, top_k=top_k * 3)

        # 결과를 drug_id로 매핑
        dense_map: Dict[str, Dict] = {r["drug_id"]: r for r in dense_results}
        bm25_map: Dict[str, Dict] = {r["drug_id"]: r for r in bm25_results}

        # 모든 drug_id 수집
        all_drug_ids = set(dense_map.keys()) | set(bm25_map.keys())

        logger.info(f"📊 Hybrid 가중치: Dense={self.dense_weight}, Sparse={self.sparse_weight}")

        # Hybrid 점수 계산
        hybrid_results = []
        for drug_id in all_drug_ids:
            # Dense score: 원본 코사인 유사도 (0~1)
            if drug_id in dense_map:
                dense_score = dense_map[drug_id].get("similarity", 0)
            else:
                dense_score = 0

            # Sparse score: BM25 점수를 30점 기준으로 0~1 정규화
            if drug_id in bm25_map:
                raw_bm25 = bm25_map[drug_id].get("bm25_score", 0)
                sparse_score = self._normalize_bm25_score(raw_bm25)
            else:
                sparse_score = 0

            # Hybrid score: sparse * 0.7 + dense * 0.3
            hybrid_score = (
                self.sparse_weight * sparse_score +
                self.dense_weight * dense_score
            )

            # 문서 정보 가져오기 (dense 우선, 없으면 bm25)
            doc = dense_map.get(drug_id) or bm25_map.get(drug_id)
            if doc:
                result = doc.copy()
                result["dense_score"] = dense_score
                result["bm25_score"] = sparse_score  # 정규화된 점수 (0~1)
                result["hybrid_score"] = hybrid_score

                # similarity는 원래 값 유지 (dense가 있으면 그 값, 없으면 hybrid)
                if drug_id in dense_map:
                    result["similarity"] = dense_map[drug_id].get("similarity", 0)
                else:
                    result["similarity"] = hybrid_score

                hybrid_results.append(result)

        # Hybrid 점수로 정렬
        hybrid_results.sort(key=lambda x: x["hybrid_score"], reverse=True)

        logger.info(
            f"🔀 Hybrid 검색 완료: Dense={len(dense_results)}, "
            f"BM25={len(bm25_results)}, Merged={len(hybrid_results[:top_k])}"
        )

        return hybrid_results[:top_k]


# 싱글톤 인스턴스 (세션별로 생성되므로 실제로는 팩토리 패턴 사용)
_bm25_service: Optional[BM25SearchService] = None


def get_bm25_service(session: AsyncSession) -> BM25SearchService:
    """BM25 서비스 인스턴스 반환"""
    return BM25SearchService(session)


def get_hybrid_service(
    session: AsyncSession,
    dense_weight: float = 0.7,
    sparse_weight: float = 0.3,
) -> HybridSearchService:
    """Hybrid Search 서비스 인스턴스 반환

    Args:
        session: DB 세션
        dense_weight: Dense(벡터) 검색 가중치 (기본 0.7)
        sparse_weight: Sparse(BM25) 검색 가중치 (기본 0.3)

    Returns:
        HybridSearchService 인스턴스
    """
    return HybridSearchService(session, dense_weight, sparse_weight)
