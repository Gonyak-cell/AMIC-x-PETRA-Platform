"""금감원(FSS) 기관전용 PEF 현황 시딩 스크립트 (CLI).

기존 FSSPEFService를 호출하여 엑셀 파일을 파싱하고
GP 전수목록 + 총약정액 합산을 DB에 적재한다.

사용법:
    cd kiis
    python -m scripts.seed_fss_pef path/to/fss_pef.xlsx
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory, engine
from app.services.fss_pef_service import FSSPEFService

logger = logging.getLogger(__name__)


async def seed_fss_pef(file_path: Path) -> None:
    """금감원 PEF 현황 엑셀을 파싱하여 DB에 시딩한다."""
    service = FSSPEFService()

    logger.info("파일 파싱 시작: %s", file_path)
    items = service.parse_fss_pef_excel(file_path)
    if not items:
        logger.warning("파싱된 PEF 데이터가 없습니다. 파일을 확인하세요.")
        return

    logger.info("파싱 완료: %d건 PEF", len(items))

    async with async_session_factory() as db:
        result = await service.sync_pef_data(db, items)

    logger.info(
        "동기화 완료:\n  총 PEF: %d건\n  PEF 생성: %d건\n  기존 GP 매칭: %d건\n  신규 GP 생성: %d건\n  에러: %d건",
        result.total_items,
        result.created,
        result.matched_existing,
        result.new_companies,
        len(result.errors),
    )
    if result.errors:
        logger.warning("에러 PEF 목록: %s", ", ".join(result.errors[:10]))


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("사용법: python -m scripts.seed_fss_pef <엑셀 파일 경로>")
        print("예시:   python -m scripts.seed_fss_pef ../기관전용_사모집합투자기구_현황.xlsx")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        logger.error("파일이 존재하지 않습니다: %s", file_path)
        sys.exit(1)

    if file_path.suffix.lower() not in (".xlsx", ".xls"):
        logger.error("엑셀 파일(.xlsx, .xls)만 지원합니다: %s", file_path.suffix)
        sys.exit(1)

    await seed_fss_pef(file_path)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
