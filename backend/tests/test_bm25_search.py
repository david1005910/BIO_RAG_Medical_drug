"""BM25 Search Service tests"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.bm25_search import (
    BM25IndexCache,
    BM25SearchService,
    HybridSearchService,
    KoreanTokenizer,
    _bm25_cache,
    get_bm25_service,
    get_hybrid_service,
    initialize_bm25,
)


class TestKoreanTokenizer:
    """한국어 토크나이저 테스트"""

    def setup_method(self):
        self.tokenizer = KoreanTokenizer()

    def test_tokenize_empty_text(self):
        """빈 텍스트 처리"""
        assert self.tokenizer.tokenize("") == []
        assert self.tokenizer.tokenize(None) == []

    def test_tokenize_removes_stopwords(self):
        """불용어 제거 테스트"""
        # 불용어만 포함된 텍스트
        result = self.tokenizer.tokenize("이 가 을 를")
        # 불용어는 제거되어야 함
        for stopword in ["이", "가", "을", "를"]:
            assert stopword not in result

    def test_tokenize_removes_short_tokens(self):
        """짧은 토큰 제거 테스트 (1자 이하)"""
        result = self.tokenizer.tokenize("a b c 약")
        # 1자 토큰은 제거됨
        assert "a" not in result
        assert "b" not in result
        assert "c" not in result
        assert "약" not in result

    def test_tokenize_generates_ngrams(self):
        """N-gram 생성 테스트"""
        result = self.tokenizer.tokenize("두통약", expand_synonyms=False)
        # 원본 토큰
        assert "두통약" in result
        # 2-gram
        assert "두통" in result
        assert "통약" in result
        # 3-gram
        assert "두통약" in result

    def test_tokenize_synonym_expansion(self):
        """동의어 확장 테스트"""
        # "머리가"는 동의어 사전에 있음
        result = self.tokenizer.tokenize("머리가 아파요", expand_synonyms=True)
        # 동의어가 확장되어야 함
        assert "두통" in result or "편두통" in result

    def test_tokenize_no_synonym_expansion(self):
        """동의어 확장 비활성화 테스트"""
        result_with = self.tokenizer.tokenize("배가 아파요", expand_synonyms=True)
        result_without = self.tokenizer.tokenize("배가 아파요", expand_synonyms=False)
        # 동의어 확장 시 더 많은 토큰
        assert len(result_with) >= len(result_without)

    def test_tokenize_symptom_keyword_weight(self):
        """증상 키워드 가중치 테스트"""
        result = self.tokenizer.tokenize("두통", expand_synonyms=False)
        # 증상 키워드는 중복 추가됨 (가중치)
        count = result.count("두통")
        assert count >= 2  # 원본 + 가중치

    def test_tokenize_removes_special_characters(self):
        """특수문자 제거 테스트"""
        result = self.tokenizer.tokenize("두통!@#$%약")
        # 특수문자는 제거되고 공백으로 분리
        assert "두통" in result
        assert "!@#$%" not in "".join(result)

    def test_tokenize_lowercase_conversion(self):
        """소문자 변환 테스트"""
        result = self.tokenizer.tokenize("ASPIRIN aspirin")
        # 대소문자 통일
        assert "aspirin" in result

    def test_tokenize_partial_synonym_matching(self):
        """부분 매칭 동의어 테스트"""
        # "열나"는 동의어 사전에 있음
        result = self.tokenizer.tokenize("열나요", expand_synonyms=True)
        # 부분 매칭으로 동의어 확장
        assert "발열" in result or "고열" in result


class TestBM25IndexCache:
    """BM25 인덱스 캐시 테스트"""

    def setup_method(self):
        # 테스트 전 캐시 초기화
        self.cache = BM25IndexCache()
        self.cache.clear()

    def teardown_method(self):
        # 테스트 후 캐시 정리
        self.cache.clear()

    def test_singleton_pattern(self):
        """싱글톤 패턴 테스트"""
        cache1 = BM25IndexCache()
        cache2 = BM25IndexCache()
        assert cache1 is cache2

    def test_initial_state(self):
        """초기 상태 테스트"""
        self.cache.clear()
        assert self.cache.bm25 is None
        assert self.cache.documents == []
        assert self.cache.corpus == []
        assert not self.cache.is_initialized

    def test_set_data(self):
        """데이터 설정 테스트"""
        mock_bm25 = MagicMock()
        documents = [{"drug_id": "1", "item_name": "Test"}]
        corpus = [["test", "tokens"]]

        self.cache.set_data(mock_bm25, documents, corpus)

        assert self.cache.bm25 is mock_bm25
        assert self.cache.documents == documents
        assert self.cache.corpus == corpus
        assert self.cache.is_initialized

    def test_clear(self):
        """캐시 초기화 테스트"""
        mock_bm25 = MagicMock()
        self.cache.set_data(mock_bm25, [{"id": 1}], [["token"]])
        self.cache.clear()

        assert self.cache.bm25 is None
        assert self.cache.documents == []
        assert self.cache.corpus == []
        assert not self.cache.is_initialized


class TestBM25SearchService:
    """BM25 검색 서비스 테스트"""

    def setup_method(self):
        # 캐시 초기화
        cache = BM25IndexCache()
        cache.clear()

    def teardown_method(self):
        # 테스트 후 캐시 정리
        cache = BM25IndexCache()
        cache.clear()

    @pytest.fixture
    def mock_session(self):
        """Mock DB 세션"""
        return AsyncMock()

    async def test_search_without_initialization(self, mock_session):
        """초기화 없이 검색 시 자동 초기화"""
        service = BM25SearchService(mock_session)

        # Mock DB 결과 설정
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        results = await service.search("두통")
        assert results == []

    async def test_search_returns_results(self, mock_session):
        """검색 결과 반환 테스트"""
        service = BM25SearchService(mock_session)

        # Mock 데이터로 캐시 직접 설정
        from rank_bm25 import BM25Okapi

        # BM25는 최소 3개 이상의 문서가 필요함 (IDF 계산을 위해)
        tokenizer = service.tokenizer
        doc1_tokens = tokenizer.tokenize("두통약 두통 완화", expand_synonyms=False)
        doc2_tokens = tokenizer.tokenize("감기약 감기 증상 완화", expand_synonyms=False)
        doc3_tokens = tokenizer.tokenize("소화제 위장약 소화", expand_synonyms=False)

        documents = [
            {"drug_id": "1", "item_name": "두통약", "efficacy": "두통 완화"},
            {"drug_id": "2", "item_name": "감기약", "efficacy": "감기 증상 완화"},
            {"drug_id": "3", "item_name": "소화제", "efficacy": "소화 촉진"},
        ]
        corpus = [doc1_tokens, doc2_tokens, doc3_tokens]

        bm25 = BM25Okapi(corpus)
        service.cache.set_data(bm25, documents, corpus)

        results = await service.search("두통", top_k=5)

        assert len(results) > 0
        assert results[0]["item_name"] == "두통약"
        assert "bm25_score" in results[0]

    async def test_search_empty_query_tokens(self, mock_session):
        """빈 쿼리 토큰 처리"""
        service = BM25SearchService(mock_session)

        # 캐시 설정
        from rank_bm25 import BM25Okapi

        documents = [{"drug_id": "1", "item_name": "Test"}]
        corpus = [["test"]]
        bm25 = BM25Okapi(corpus)
        service.cache.set_data(bm25, documents, corpus)

        # 불용어만으로 구성된 쿼리
        results = await service.search("이 가 을 를")
        assert results == []

    async def test_search_top_k_limit(self, mock_session):
        """top_k 제한 테스트"""
        service = BM25SearchService(mock_session)

        from rank_bm25 import BM25Okapi

        # 여러 문서 생성
        documents = [
            {"drug_id": str(i), "item_name": f"약품{i}", "efficacy": "두통 완화"}
            for i in range(10)
        ]
        corpus = [["두통", "완화", f"약품{i}"] for i in range(10)]
        bm25 = BM25Okapi(corpus)
        service.cache.set_data(bm25, documents, corpus)

        results = await service.search("두통", top_k=3)
        assert len(results) <= 3

    def test_create_document_text(self, mock_session):
        """문서 텍스트 생성 테스트"""
        service = BM25SearchService(mock_session)

        text = service._create_document_text(
            item_name="타이레놀",
            efficacy="두통, 발열 완화",
            use_method="1일 3회 복용",
            caution_info="과량 복용 금지",
        )

        assert "타이레놀" in text
        assert "두통, 발열 완화" in text
        assert "1일 3회 복용" in text
        assert "과량 복용 금지" in text

    def test_create_document_text_truncates_long_fields(self, mock_session):
        """긴 필드 자르기 테스트"""
        service = BM25SearchService(mock_session)

        long_text = "a" * 500
        text = service._create_document_text(
            item_name="Test",
            efficacy="효과",
            use_method=long_text,
            caution_info=long_text,
        )

        # 200자로 잘림
        assert text.count("a") <= 400  # use_method + caution_info 각각 200자


class TestHybridSearchService:
    """Hybrid 검색 서비스 테스트"""

    def setup_method(self):
        cache = BM25IndexCache()
        cache.clear()

    def teardown_method(self):
        cache = BM25IndexCache()
        cache.clear()

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    def test_normalize_bm25_score(self, mock_session):
        """BM25 점수 정규화 테스트"""
        service = HybridSearchService(mock_session)

        # 0점
        assert service._normalize_bm25_score(0) == 0.0
        # 15점 -> 0.5
        assert service._normalize_bm25_score(15) == 0.5
        # 30점 -> 1.0
        assert service._normalize_bm25_score(30) == 1.0
        # 60점 -> 1.0 (최대 제한)
        assert service._normalize_bm25_score(60) == 1.0

    async def test_hybrid_search_merges_results(self, mock_session):
        """Hybrid 검색 결과 병합 테스트"""
        service = HybridSearchService(mock_session, dense_weight=0.7, sparse_weight=0.3)

        # BM25 캐시 설정
        from rank_bm25 import BM25Okapi

        documents = [
            {"drug_id": "1", "item_name": "약품A", "efficacy": "두통"},
            {"drug_id": "2", "item_name": "약품B", "efficacy": "두통 완화"},
        ]
        corpus = [["두통"], ["두통", "완화"]]
        bm25 = BM25Okapi(corpus)
        service.bm25_service.cache.set_data(bm25, documents, corpus)

        # Dense 결과
        dense_results = [
            {"drug_id": "1", "item_name": "약품A", "similarity": 0.9},
            {"drug_id": "3", "item_name": "약품C", "similarity": 0.8},
        ]

        results = await service.search("두통", dense_results, top_k=5)

        assert len(results) > 0
        # 모든 결과에 hybrid_score 포함
        for r in results:
            assert "hybrid_score" in r
            assert "dense_score" in r
            assert "bm25_score" in r

    async def test_hybrid_search_weights(self, mock_session):
        """Hybrid 검색 가중치 적용 테스트"""
        service = HybridSearchService(mock_session, dense_weight=0.7, sparse_weight=0.3)

        from rank_bm25 import BM25Okapi

        documents = [{"drug_id": "1", "item_name": "Test", "efficacy": "두통"}]
        corpus = [["두통"]]
        bm25 = BM25Okapi(corpus)
        service.bm25_service.cache.set_data(bm25, documents, corpus)

        dense_results = [{"drug_id": "1", "item_name": "Test", "similarity": 1.0}]

        results = await service.search("두통", dense_results, top_k=5)

        assert len(results) == 1
        # dense_score = 1.0, bm25_score는 정규화됨
        result = results[0]
        assert result["dense_score"] == 1.0
        # hybrid = sparse * 0.3 + dense * 0.7
        expected_hybrid = 0.3 * result["bm25_score"] + 0.7 * result["dense_score"]
        assert abs(result["hybrid_score"] - expected_hybrid) < 0.001

    async def test_hybrid_search_only_bm25_results(self, mock_session):
        """BM25만 결과 있을 때 테스트"""
        service = HybridSearchService(mock_session)

        from rank_bm25 import BM25Okapi

        # BM25는 최소 3개 이상의 문서가 필요함 (IDF 계산을 위해)
        tokenizer = service.bm25_service.tokenizer
        doc1_tokens = tokenizer.tokenize("두통약 두통 완화", expand_synonyms=False)
        doc2_tokens = tokenizer.tokenize("감기약 감기 증상 완화", expand_synonyms=False)
        doc3_tokens = tokenizer.tokenize("소화제 위장약 소화", expand_synonyms=False)

        documents = [
            {"drug_id": "1", "item_name": "두통약", "efficacy": "두통 완화"},
            {"drug_id": "2", "item_name": "감기약", "efficacy": "감기 증상 완화"},
            {"drug_id": "3", "item_name": "소화제", "efficacy": "소화 촉진"},
        ]
        corpus = [doc1_tokens, doc2_tokens, doc3_tokens]
        bm25 = BM25Okapi(corpus)
        service.bm25_service.cache.set_data(bm25, documents, corpus)

        # Dense 결과 없음
        dense_results = []

        results = await service.search("두통", dense_results, top_k=5)

        assert len(results) > 0
        assert results[0]["dense_score"] == 0

    async def test_hybrid_search_only_dense_results(self, mock_session):
        """Dense만 결과 있을 때 테스트"""
        service = HybridSearchService(mock_session)

        from rank_bm25 import BM25Okapi

        # BM25에 다른 문서만 있음
        documents = [{"drug_id": "2", "item_name": "감기약", "efficacy": "감기"}]
        corpus = [["감기"]]
        bm25 = BM25Okapi(corpus)
        service.bm25_service.cache.set_data(bm25, documents, corpus)

        # Dense 결과만
        dense_results = [
            {"drug_id": "1", "item_name": "두통약", "similarity": 0.9},
        ]

        results = await service.search("두통", dense_results, top_k=5)

        # Dense 결과가 포함되어야 함
        drug_ids = [r["drug_id"] for r in results]
        assert "1" in drug_ids


class TestFactoryFunctions:
    """팩토리 함수 테스트"""

    def test_get_bm25_service(self):
        """BM25 서비스 팩토리"""
        mock_session = AsyncMock()
        service = get_bm25_service(mock_session)

        assert isinstance(service, BM25SearchService)
        assert service.session is mock_session

    def test_get_hybrid_service(self):
        """Hybrid 서비스 팩토리"""
        mock_session = AsyncMock()
        service = get_hybrid_service(mock_session, dense_weight=0.6, sparse_weight=0.4)

        assert isinstance(service, HybridSearchService)
        assert service.dense_weight == 0.6
        assert service.sparse_weight == 0.4

    def test_get_hybrid_service_default_weights(self):
        """Hybrid 서비스 기본 가중치"""
        mock_session = AsyncMock()
        service = get_hybrid_service(mock_session)

        assert service.dense_weight == 0.7
        assert service.sparse_weight == 0.3


class TestRefreshIndex:
    """인덱스 새로고침 테스트"""

    def setup_method(self):
        cache = BM25IndexCache()
        cache.clear()

    def teardown_method(self):
        cache = BM25IndexCache()
        cache.clear()

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    async def test_refresh_index_clears_and_reinitializes(self, mock_session):
        """refresh_index가 캐시를 지우고 재초기화하는지 테스트"""
        service = BM25SearchService(mock_session)

        # 초기 캐시 설정
        from rank_bm25 import BM25Okapi

        tokenizer = service.tokenizer
        doc_tokens = tokenizer.tokenize("테스트 문서", expand_synonyms=False)
        documents = [{"drug_id": "1", "item_name": "테스트"}]
        corpus = [doc_tokens]
        bm25 = BM25Okapi(corpus)
        service.cache.set_data(bm25, documents, corpus)

        assert service.cache.is_initialized

        # Mock DB 결과 설정 (빈 결과)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        # refresh_index 호출
        await service.refresh_index()

        # 캐시가 비어있어야 함 (DB에서 빈 결과 반환)
        assert service.cache.documents == []
        assert service.cache.corpus == []

    async def test_refresh_index_loads_new_data(self, mock_session):
        """refresh_index가 DB에서 새 데이터를 로드하는지 테스트"""
        service = BM25SearchService(mock_session)

        # Mock DB row 생성
        mock_row = MagicMock()
        mock_row.drug_id = "123"
        mock_row.item_name = "테스트약"
        mock_row.entp_name = "테스트제약"
        mock_row.efficacy = "두통 완화"
        mock_row.use_method = "1일 3회"
        mock_row.caution_info = "주의사항"
        mock_row.side_effects = "부작용"

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        # refresh_index 호출
        await service.refresh_index()

        # 새 데이터가 로드되어야 함
        assert service.cache.is_initialized
        assert len(service.cache.documents) == 1
        assert service.cache.documents[0]["drug_id"] == "123"
        assert service.cache.documents[0]["item_name"] == "테스트약"


class TestInitializeBm25:
    """initialize_bm25 서버 시작 함수 테스트"""

    def setup_method(self):
        _bm25_cache.clear()

    def teardown_method(self):
        _bm25_cache.clear()

    async def test_initialize_bm25_already_initialized(self):
        """이미 초기화된 경우 True 반환"""
        # 캐시를 초기화된 상태로 설정
        from rank_bm25 import BM25Okapi

        bm25 = BM25Okapi([["test"]])
        _bm25_cache.set_data(bm25, [{"id": 1}], [["test"]])

        assert _bm25_cache.is_initialized

        result = await initialize_bm25()

        assert result is True

    @patch("app.db.session.async_session_maker")
    async def test_initialize_bm25_success(self, mock_session_maker):
        """초기화 성공 시 True 반환"""
        # Mock 세션 컨텍스트 매니저 설정
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_session
        mock_context.__aexit__.return_value = None
        mock_session_maker.return_value = mock_context

        # Mock DB row
        mock_row = MagicMock()
        mock_row.drug_id = "1"
        mock_row.item_name = "테스트약"
        mock_row.entp_name = "제약사"
        mock_row.efficacy = "효능"
        mock_row.use_method = "용법"
        mock_row.caution_info = "주의"
        mock_row.side_effects = "부작용"

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        result = await initialize_bm25()

        assert result is True
        assert _bm25_cache.is_initialized

    @patch("app.db.session.async_session_maker")
    async def test_initialize_bm25_failure(self, mock_session_maker):
        """초기화 실패 시 False 반환"""
        # 예외 발생하도록 설정
        mock_session_maker.side_effect = Exception("DB connection failed")

        result = await initialize_bm25()

        assert result is False

    @patch("app.db.session.async_session_maker")
    async def test_initialize_bm25_empty_db(self, mock_session_maker):
        """DB에 데이터가 없는 경우"""
        mock_session = AsyncMock()
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_session
        mock_context.__aexit__.return_value = None
        mock_session_maker.return_value = mock_context

        # 빈 결과 반환
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        result = await initialize_bm25()

        # 데이터가 없으면 is_initialized는 False
        assert result is False


class TestHybridServiceInitialize:
    """HybridSearchService.initialize 테스트"""

    def setup_method(self):
        cache = BM25IndexCache()
        cache.clear()

    def teardown_method(self):
        cache = BM25IndexCache()
        cache.clear()

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    async def test_hybrid_service_initialize(self, mock_session):
        """HybridSearchService.initialize가 BM25 서비스를 초기화하는지 테스트"""
        service = HybridSearchService(mock_session)

        # Mock DB row
        mock_row = MagicMock()
        mock_row.drug_id = "1"
        mock_row.item_name = "테스트약"
        mock_row.entp_name = "제약사"
        mock_row.efficacy = "효능"
        mock_row.use_method = "용법"
        mock_row.caution_info = "주의"
        mock_row.side_effects = "부작용"

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        await service.initialize()

        assert service.bm25_service.cache.is_initialized
