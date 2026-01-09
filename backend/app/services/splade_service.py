"""BGE-M3 Sparse Embedding 서비스 - 다국어(한국어) 지원

기존 SPLADE 모델은 한국어를 자모로 분해하여 의미 없는 결과를 반환했습니다.
BGE-M3는 100+ 언어를 지원하며, 한국어 sparse embedding이 정상 작동합니다.

참고: https://huggingface.co/BAAI/bge-m3
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# 증상 동의어 매핑 (일상어 → 의학 용어)
# 쿼리 확장에 사용
SYMPTOM_SYNONYMS = {
    # 복부/소화 관련
    '배가 아': ['복통', '복부통증', '위통'],
    '배아파': ['복통', '위통', '장통'],
    '속이': ['소화불량', '속쓰림', '위장'],
    '속쓰려': ['속쓰림', '위염'],
    '체했': ['소화불량', '체기'],
    '더부룩': ['소화불량', '복부팽만'],
    # 두통/머리 관련
    '머리가 아': ['두통', '편두통'],
    '머리아파': ['두통', '편두통'],
    '지끈': ['두통', '편두통'],
    # 열/감기 관련
    '열나': ['발열', '고열'],
    '열이나': ['발열', '고열'],
    '으슬으슬': ['오한', '감기'],
    '콧물나': ['콧물', '비염'],
    '코막혀': ['코막힘', '비염'],
    '기침나': ['기침', '해소'],
    '목이 아': ['인후통', '인후염'],
    '목아파': ['인후통', '인후염'],
    # 근골격 관련
    '허리가 아': ['요통', '허리통증'],
    '허리아파': ['요통'],
    '어깨가 아': ['어깨통증', '견통'],
    '무릎이 아': ['무릎통증', '관절통'],
    # 피부 관련
    '가려워': ['가려움', '소양증'],
    '두드러기': ['두드러기', '발진'],
    # 기타 증상
    '어지러워': ['어지러움', '현기증'],
    '메스꺼워': ['메스꺼움', '구역'],
    '피곤': ['피로', '권태'],
    '잠이 안': ['불면', '수면장애'],
}


class SPLADEService:
    """BGE-M3 Sparse Embedding 서비스 (SPLADE 대체)

    BGE-M3 (BAAI/bge-m3)를 사용하여 텍스트를 Sparse 벡터로 변환합니다.
    - 100+ 언어 지원 (한국어 포함)
    - Dense + Sparse + ColBERT 임베딩 동시 지원
    - 최대 8192 토큰 처리 가능

    점수 체계:
    - BGE-M3 lexical weight: 토큰별 가중치
    - 정규화: max_score 기준으로 0~1 스케일로 정규화
    """

    def __init__(self, model_name: Optional[str] = None):
        # BGE-M3 모델 사용 (SPLADE_MODEL 설정 무시)
        self.model_name = "BAAI/bge-m3"
        self.model = None
        self._initialized = False
        self._load_failed = False  # 로딩 실패 플래그 (재시도 방지)
        self.max_score = settings.SPLADE_MAX_SCORE  # 정규화 기준

    async def initialize(self) -> bool:
        """BGE-M3 모델 초기화

        Returns:
            초기화 성공 여부
        """
        if self._initialized:
            return True

        # 이미 로딩 실패한 경우 재시도하지 않음
        if self._load_failed:
            return False

        try:
            logger.info(f"🔧 BGE-M3 모델 로딩 중: {self.model_name}")

            # 모델 로드 (비동기 실행)
            loop = asyncio.get_event_loop()

            def load_model():
                # use_fp16=True for faster inference (GPU only)
                # CPU에서는 use_fp16=False 사용
                import torch
                from FlagEmbedding import BGEM3FlagModel
                use_fp16 = torch.cuda.is_available()
                model = BGEM3FlagModel(
                    self.model_name,
                    use_fp16=use_fp16,
                )
                return model

            self.model = await loop.run_in_executor(None, load_model)

            self._initialized = True
            logger.info("✅ BGE-M3 모델 로딩 완료 (한국어 지원)")
            return True

        except Exception as e:
            logger.error(f"❌ BGE-M3 모델 로딩 실패: {e}")
            self._initialized = False
            self._load_failed = True  # 재시도 방지
            return False

    def expand_query(self, query: str) -> str:
        """쿼리를 의학 용어로 확장

        일상적인 증상 표현을 의학 용어로 확장하여
        sparse 검색의 매칭률을 높입니다.

        Args:
            query: 원본 쿼리

        Returns:
            확장된 쿼리 (원본 + 의학 용어)
        """
        expanded_terms = []

        # 동의어 사전에서 매칭되는 용어 찾기
        for pattern, synonyms in SYMPTOM_SYNONYMS.items():
            if pattern in query:
                expanded_terms.extend(synonyms)

        if expanded_terms:
            # 중복 제거
            unique_terms = list(set(expanded_terms))
            expanded_query = f"{query} {' '.join(unique_terms)}"
            logger.debug(f"📝 쿼리 확장: '{query}' → '{expanded_query}'")
            return expanded_query

        return query

    async def encode(self, text: str, expand: bool = True) -> Dict[str, Any]:
        """텍스트를 BGE-M3 Sparse 벡터로 인코딩

        Args:
            text: 인코딩할 텍스트
            expand: 쿼리 확장 여부 (기본 True)

        Returns:
            Sparse 벡터 딕셔너리 {"indices": [...], "values": [...]}
        """
        if not self._initialized:
            await self.initialize()

        if not self.model:
            logger.error("BGE-M3 모델이 초기화되지 않았습니다.")
            return {"indices": [], "values": []}

        # 쿼리 확장 적용
        if expand:
            text = self.expand_query(text)

        try:
            loop = asyncio.get_event_loop()

            def do_encode():
                # BGE-M3 인코딩 (sparse만 필요)
                output = self.model.encode(
                    [text],
                    return_dense=False,
                    return_sparse=True,
                    return_colbert_vecs=False,
                )
                return output

            output = await loop.run_in_executor(None, do_encode)

            # lexical_weights에서 sparse 벡터 추출
            # 형식: {token_id: weight, ...}
            lexical_weights = output.get("lexical_weights", [{}])[0]

            if not lexical_weights:
                return {"indices": [], "values": []}

            # 딕셔너리를 indices/values 형식으로 변환
            indices = list(lexical_weights.keys())
            values = list(lexical_weights.values())

            return {
                "indices": indices,
                "values": values,
            }

        except Exception as e:
            logger.error(f"❌ BGE-M3 인코딩 실패: {e}")
            return {"indices": [], "values": []}

    async def encode_batch(
        self,
        texts: List[str],
        batch_size: int = 8,
    ) -> List[Dict[str, Any]]:
        """텍스트 배치를 BGE-M3 Sparse 벡터로 인코딩

        Args:
            texts: 인코딩할 텍스트 리스트
            batch_size: 배치 크기 (메모리 제약으로 8 권장)

        Returns:
            Sparse 벡터 딕셔너리 리스트
        """
        if not self._initialized:
            await self.initialize()

        if not self.model:
            logger.error("BGE-M3 모델이 초기화되지 않았습니다.")
            return [{"indices": [], "values": []} for _ in texts]

        results = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            try:
                loop = asyncio.get_event_loop()

                def do_encode_batch(batch):
                    output = self.model.encode(
                        batch,
                        return_dense=False,
                        return_sparse=True,
                        return_colbert_vecs=False,
                    )
                    return output

                output = await loop.run_in_executor(
                    None, do_encode_batch, batch_texts
                )

                # 각 문서의 lexical_weights 처리
                lexical_weights_list = output.get("lexical_weights", [])

                for lexical_weights in lexical_weights_list:
                    if not lexical_weights:
                        results.append({"indices": [], "values": []})
                        continue

                    indices = list(lexical_weights.keys())
                    values = list(lexical_weights.values())

                    results.append({
                        "indices": indices,
                        "values": values,
                    })

                logger.info(
                    f"📝 BGE-M3 배치 인코딩: {i + len(batch_texts)}/{len(texts)} 완료"
                )

            except Exception as e:
                logger.error(f"❌ BGE-M3 배치 인코딩 실패: {e}")
                # 실패한 배치는 빈 벡터로 채움
                results.extend([{"indices": [], "values": []} for _ in batch_texts])

        logger.info(f"✅ BGE-M3 전체 인코딩 완료: {len(results)}개")
        return results

    def get_sparse_score(self, sparse_vector: Dict[str, Any]) -> float:
        """Sparse 벡터의 총 점수 계산

        Args:
            sparse_vector: sparse 벡터

        Returns:
            총 점수 (values 합계)
        """
        values = sparse_vector.get("values", [])
        return sum(values) if values else 0.0

    def normalize_score(self, score: float) -> float:
        """점수를 0~1 범위로 정규화

        Args:
            score: 원본 점수

        Returns:
            0~1 범위로 정규화된 점수
        """
        normalized = score / self.max_score
        return min(normalized, 1.0)

    async def create_document_text(
        self,
        item_name: str,
        efficacy: Optional[str] = None,
        use_method: Optional[str] = None,
        caution_info: Optional[str] = None,
    ) -> str:
        """인덱싱용 문서 텍스트 생성

        Args:
            item_name: 제품명
            efficacy: 효능효과
            use_method: 용법용량
            caution_info: 주의사항

        Returns:
            인코딩용 텍스트
        """
        parts = [item_name or ""]

        if efficacy:
            parts.append(efficacy)
        if use_method:
            parts.append(use_method[:300])  # 용법은 앞부분만
        if caution_info:
            parts.append(caution_info[:200])  # 주의사항도 앞부분만

        return " ".join(parts)


# 싱글톤 인스턴스
_splade_service: Optional[SPLADEService] = None


def get_splade_service() -> SPLADEService:
    """Sparse Embedding 서비스 싱글톤 반환"""
    global _splade_service
    if _splade_service is None:
        _splade_service = SPLADEService()
    return _splade_service


async def initialize_splade() -> bool:
    """Sparse Embedding 서비스 초기화"""
    if not settings.ENABLE_MILVUS:
        logger.info("⚠️ BGE-M3 비활성화됨 (ENABLE_MILVUS=false)")
        return False

    service = get_splade_service()
    return await service.initialize()
