#!/usr/bin/env python
"""
벡터 인덱스 재구축 스크립트
기존 DB 데이터로 벡터 인덱스를 다시 구축합니다.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import async_session_maker
from app.services.data_sync import DataSyncService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """벡터 인덱스 재구축"""
    logger.info("=" * 50)
    logger.info("벡터 인덱스 재구축 시작")
    logger.info("=" * 50)

    async with async_session_maker() as session:
        sync_service = DataSyncService(session)

        try:
            count = await sync_service.rebuild_vectors()

            logger.info("=" * 50)
            logger.info(f"재구축 완료: {count}개 벡터 생성")
            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"재구축 실패: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
