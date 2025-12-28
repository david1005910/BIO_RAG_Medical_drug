#!/usr/bin/env python
"""
데이터 동기화 스크립트
공공데이터 API에서 의약품 데이터를 수집하고 벡터 인덱스를 구축합니다.
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.db.session import async_session_maker
from app.db.init_db import init_db
from app.services.data_sync import DataSyncService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main(max_pages: int, build_vectors: bool):
    """메인 동기화 함수"""
    logger.info("=" * 50)
    logger.info("의약품 데이터 동기화 시작")
    logger.info("=" * 50)

    # 데이터베이스 초기화
    logger.info("데이터베이스 초기화...")
    await init_db()

    # 동기화 실행
    async with async_session_maker() as session:
        sync_service = DataSyncService(session)

        try:
            stats = await sync_service.sync_drugs(
                max_pages=max_pages,
                build_vectors=build_vectors,
            )

            logger.info("=" * 50)
            logger.info("동기화 완료!")
            logger.info(f"  - 수집: {stats['fetched']}개")
            logger.info(f"  - 전처리: {stats['processed']}개")
            logger.info(f"  - 저장: {stats['saved']}개")
            logger.info(f"  - 벡터: {stats['vectors_created']}개")
            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"동기화 실패: {e}")
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="의약품 데이터 동기화")
    parser.add_argument(
        "--pages",
        type=int,
        default=10,
        help="수집할 최대 페이지 수 (기본값: 10)",
    )
    parser.add_argument(
        "--no-vectors",
        action="store_true",
        help="벡터 인덱스 구축 건너뛰기",
    )

    args = parser.parse_args()

    asyncio.run(main(
        max_pages=args.pages,
        build_vectors=not args.no_vectors,
    ))
