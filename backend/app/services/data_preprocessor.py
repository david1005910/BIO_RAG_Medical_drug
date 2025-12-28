"""데이터 전처리기 - API 응답을 DB/RAG용 형식으로 변환"""
import hashlib
import logging
import re
from typing import Dict, List

from app.external.data_go_kr import DrugInfo

logger = logging.getLogger(__name__)


class DrugDataPreprocessor:
    """의약품 데이터 전처리기"""

    def preprocess(self, drug: DrugInfo) -> Dict:
        """단일 의약품 전처리

        Args:
            drug: API에서 받은 의약품 정보

        Returns:
            DB 저장용 딕셔너리
        """
        # 필드 정제
        item_name = drug.itemName or "알 수 없음"
        entp_name = drug.entpName or "알 수 없음"
        efficacy = self._clean_text(drug.efcyQesitm)
        use_method = self._clean_text(drug.useMethodQesitm)
        warning = self._clean_text(drug.atpnWarnQesitm)
        caution = self._clean_text(drug.atpnQesitm)
        interaction = self._clean_text(drug.intrcQesitm)
        side_effects = self._clean_text(drug.seQesitm)
        storage = self._clean_text(drug.depositMethodQesitm)

        # RAG용 문서 생성
        document = self._create_document(
            item_name,
            entp_name,
            efficacy,
            use_method,
            warning,
            caution,
            interaction,
            side_effects,
            storage,
        )

        return {
            "id": drug.itemSeq or self._generate_id(item_name),
            "item_name": item_name,
            "entp_name": entp_name,
            "efficacy": efficacy,
            "use_method": use_method,
            "warning_info": warning,
            "caution_info": caution,
            "interaction": interaction,
            "side_effects": side_effects,
            "storage_method": storage,
            "document": document,
        }

    def preprocess_batch(self, drugs: List[DrugInfo]) -> List[Dict]:
        """배치 전처리

        Args:
            drugs: 의약품 정보 리스트

        Returns:
            전처리된 딕셔너리 리스트
        """
        processed = []
        for drug in drugs:
            try:
                processed.append(self.preprocess(drug))
            except Exception as e:
                logger.warning(f"전처리 실패 (건너뜀): {drug.itemName} - {e}")
                continue

        logger.info(f"✅ {len(processed)}/{len(drugs)}개 전처리 완료")
        return processed

    def _clean_text(self, text: str) -> str:
        """텍스트 정제

        Args:
            text: 원본 텍스트

        Returns:
            정제된 텍스트
        """
        if not text:
            return ""

        # HTML 태그 제거
        text = re.sub(r"<[^>]+>", "", text)
        # 연속 공백 정리
        text = re.sub(r"\s+", " ", text)
        # 특수 문자 정리
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")

        return text.strip()

    def _create_document(
        self,
        name: str,
        company: str,
        efficacy: str,
        use_method: str,
        warning: str,
        caution: str,
        interaction: str,
        side_effects: str,
        storage: str,
    ) -> str:
        """RAG 검색에 최적화된 문서 생성

        Args:
            각 의약품 필드들

        Returns:
            포맷팅된 문서 문자열
        """
        sections = [
            f"【의약품명】 {name}",
            f"【제조사】 {company}",
        ]

        if efficacy:
            sections.append(f"【효능효과】 {efficacy}")
        if use_method:
            sections.append(f"【용법용량】 {use_method}")
        if warning:
            sections.append(f"【경고】 {warning}")
        if caution:
            sections.append(f"【주의사항】 {caution}")
        if interaction:
            sections.append(f"【상호작용】 {interaction}")
        if side_effects:
            sections.append(f"【부작용】 {side_effects}")
        if storage:
            sections.append(f"【보관법】 {storage}")

        return "\n\n".join(sections)

    def _generate_id(self, name: str) -> str:
        """의약품명으로 ID 생성 (itemSeq가 없을 경우)"""
        return hashlib.md5(name.encode()).hexdigest()[:20]
