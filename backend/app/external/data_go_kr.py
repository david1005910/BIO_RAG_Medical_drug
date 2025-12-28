"""공공데이터포털 e약은요 API 클라이언트"""
import asyncio
import logging
from typing import List, Optional

import httpx
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class DrugInfo(BaseModel):
    """e약은요 API 응답 스키마"""

    itemSeq: str  # 품목기준코드
    itemName: str  # 제품명
    entpName: Optional[str] = None  # 제조사
    efcyQesitm: Optional[str] = None  # 효능효과
    useMethodQesitm: Optional[str] = None  # 용법용량
    atpnWarnQesitm: Optional[str] = None  # 경고
    atpnQesitm: Optional[str] = None  # 주의사항
    intrcQesitm: Optional[str] = None  # 상호작용
    seQesitm: Optional[str] = None  # 부작용
    depositMethodQesitm: Optional[str] = None  # 보관법


class DataGoKrClient:
    """공공데이터포털 e약은요 API 클라이언트"""

    BASE_URL = "http://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.DATA_GO_KR_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_drug_list(
        self,
        page_no: int = 1,
        num_of_rows: int = 100,
        item_name: Optional[str] = None,
    ) -> List[DrugInfo]:
        """의약품 목록 조회

        Args:
            page_no: 페이지 번호 (1부터 시작)
            num_of_rows: 페이지당 결과 수
            item_name: 의약품명 필터 (선택)

        Returns:
            의약품 정보 리스트
        """
        params = {
            "serviceKey": self.api_key,
            "pageNo": str(page_no),
            "numOfRows": str(num_of_rows),
            "type": "json",
        }

        if item_name:
            params["itemName"] = item_name

        try:
            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()

            data = response.json()

            # API 응답 구조 파싱
            body = data.get("body", {})
            items = body.get("items", [])

            # items가 dict일 경우 (단일 결과)
            if isinstance(items, dict):
                items = items.get("item", [])
            # items가 list일 경우
            elif isinstance(items, list):
                pass
            else:
                items = []

            # 단일 항목도 리스트로 처리
            if isinstance(items, dict):
                items = [items]

            return [DrugInfo(**item) for item in items] if items else []

        except httpx.HTTPStatusError as e:
            logger.error(f"API HTTP 에러: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"API 호출 실패: {e}")
            return []

    async def get_total_count(self) -> int:
        """전체 의약품 수 조회"""
        params = {
            "serviceKey": self.api_key,
            "pageNo": "1",
            "numOfRows": "1",
            "type": "json",
        }

        try:
            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()

            data = response.json()
            return data.get("body", {}).get("totalCount", 0)

        except Exception as e:
            logger.error(f"전체 수 조회 실패: {e}")
            return 0

    async def collect_all_drugs(
        self,
        max_pages: int = 10,
        num_of_rows: int = 100,
    ) -> List[DrugInfo]:
        """전체 의약품 데이터 수집

        Args:
            max_pages: 최대 페이지 수
            num_of_rows: 페이지당 결과 수

        Returns:
            수집된 모든 의약품 정보
        """
        all_drugs = []

        for page in range(1, max_pages + 1):
            logger.info(f"📥 페이지 {page}/{max_pages} 수집 중...")
            drugs = await self.get_drug_list(page_no=page, num_of_rows=num_of_rows)

            if not drugs:
                logger.info(f"페이지 {page}에서 더 이상 데이터 없음")
                break

            all_drugs.extend(drugs)
            await asyncio.sleep(0.5)  # Rate limit 방지

        logger.info(f"✅ 총 {len(all_drugs)}개 의약품 수집 완료")
        return all_drugs

    async def close(self):
        """클라이언트 종료"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
