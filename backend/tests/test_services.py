"""Service layer tests"""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.data_preprocessor import DrugDataPreprocessor
from app.external.data_go_kr import DrugInfo


class TestDrugDataPreprocessor:
    """데이터 전처리기 테스트"""

    def test_clean_text_removes_html(self):
        """HTML 태그 제거 테스트"""
        preprocessor = DrugDataPreprocessor()
        result = preprocessor._clean_text("<p>테스트 <b>텍스트</b></p>")
        assert result == "테스트 텍스트"

    def test_clean_text_handles_none(self):
        """None 값 처리 테스트"""
        preprocessor = DrugDataPreprocessor()
        result = preprocessor._clean_text(None)
        assert result == ""

    def test_clean_text_normalizes_whitespace(self):
        """공백 정규화 테스트"""
        preprocessor = DrugDataPreprocessor()
        result = preprocessor._clean_text("테스트    여러   공백")
        assert result == "테스트 여러 공백"

    def test_preprocess_creates_document(self):
        """전처리 결과에 document 필드 생성 테스트"""
        preprocessor = DrugDataPreprocessor()
        drug = DrugInfo(
            itemSeq="12345",
            itemName="테스트약",
            entpName="테스트제약",
            efcyQesitm="두통에 효과적",
        )

        result = preprocessor.preprocess(drug)

        assert result["id"] == "12345"
        assert result["item_name"] == "테스트약"
        assert result["entp_name"] == "테스트제약"
        assert result["efficacy"] == "두통에 효과적"
        assert "【의약품명】 테스트약" in result["document"]
        assert "【효능효과】 두통에 효과적" in result["document"]

    def test_create_document_format(self):
        """문서 포맷 테스트"""
        preprocessor = DrugDataPreprocessor()
        document = preprocessor._create_document(
            name="타이레놀",
            company="존슨앤드존슨",
            efficacy="두통, 발열",
            use_method="1일 3회",
            warning="",
            caution="과량 복용 금지",
            interaction="",
            side_effects="졸음",
            storage="서늘한 곳",
        )

        assert "【의약품명】 타이레놀" in document
        assert "【제조사】 존슨앤드존슨" in document
        assert "【효능효과】 두통, 발열" in document
        assert "【주의사항】 과량 복용 금지" in document
        # 빈 필드는 포함되지 않아야 함
        assert "【경고】" not in document
