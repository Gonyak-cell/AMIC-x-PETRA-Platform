import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_jwt_claims
from app.schemas.public_data import (
    FreeSISSyncResponse,
    FSSPEFSyncResponse,
    GPCompanyDetailResponse,
    GPCompanyItem,
    GPCompanyListResponse,
    GPRegistryItem,
    GPRegistryListResponse,
    GPSyncResponse,
    KVICFundItemResponse,
    KVICSyncResponse,
    PEFFundItemResponse,
)
from app.services.freesis_service import FreeSISService
from app.services.fss_pef_service import FSSPEFService
from app.services.kvic_service import KVICService
from app.services.public_data_service import PublicDataService, search_gp_companies

logger = logging.getLogger(__name__)

# 업로드 보안 상수
_MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
_XLSX_MAGIC = b"PK\x03\x04"  # ZIP (xlsx)
_XLS_MAGIC = b"\xd0\xcf\x11\xe0"  # OLE2 (xls)

router = APIRouter()


def get_public_data_service() -> PublicDataService:
    return PublicDataService()


@router.get("/gp", response_model=GPRegistryListResponse, summary="등록 자산운용사 목록 조회")
async def list_registered_gps(
    company_name: str | None = Query(None, description="운용사명 검색 (부분 일치)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    _claims=Depends(get_jwt_claims),
    service: PublicDataService = Depends(get_public_data_service),
):
    """공공데이터포털 금융통계 기반 등록 자산운용사 목록을 조회한다.

    금융통계자산운용사정보 + 금융회사기본정보 API를 조합하여
    AUM, 펀드수, 재무현황, 설립일, 주소 등 통합 정보를 제공한다.
    KOFIA DIS에 미포함된 기관전용 사모펀드 운용사도 포함된다.
    """
    items, total = await service.search_gp_registry(
        company_name=company_name,
        page=page,
        size=size,
    )
    await service.close()
    return GPRegistryListResponse(total=total, page=page, size=size, items=items)


@router.get("/gp/companies", response_model=GPCompanyListResponse, summary="동기화된 GP 통합 목록 조회")
async def list_gp_companies(
    company_name: str | None = Query(None, description="운용사명 검색 (부분 일치)"),
    source: str | None = Query(None, description="데이터 소스 필터 (freesis, kvic, public_data)"),
    strategy: str | None = Query(None, description="전략 태그 필터 (institutional_pef, kvic_fund)"),
    sort_by: str = Query("aum", description="정렬 기준 (aum, commitment, fund_count, company_name)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지당 건수"),
    _claims=Depends(get_jwt_claims),
    db: AsyncSession = Depends(get_db),
) -> GPCompanyListResponse:
    """Company 테이블에 동기화된 GP(사모펀드 운용사) 전수목록을 통합 조회한다.

    FreeSIS(기관전용 사모펀드), KVIC(모태펀드), 공공데이터포털 등
    여러 소스에서 수집된 GP 데이터를 source/strategy 필터로 검색한다.
    """
    companies, total = await search_gp_companies(
        db,
        company_name=company_name,
        source=source,
        strategy=strategy,
        sort_by=sort_by,
        page=page,
        size=size,
    )
    items = [
        GPCompanyItem(
            id=c.id,
            corp_name=c.corp_name,
            corp_name_eng=c.corp_name_eng,
            corp_code=c.corp_code,
            finance_company_code=c.finance_company_code,
            est_dt=c.est_dt,
            adres=c.adres,
            phn_no=c.phn_no,
            gp_authorization_date=c.gp_authorization_date,
            gp_aum=c.gp_aum,
            gp_total_commitment=c.gp_total_commitment,
            gp_fund_count=c.gp_fund_count,
            gp_employee_count=c.gp_employee_count,
            sources=(c.gp_strategy_tags or {}).get("sources", []),
            strategies=(c.gp_strategy_tags or {}).get("strategies", []),
            gp_profile_synced_at=c.gp_profile_synced_at,
        )
        for c in companies
    ]
    # 최신 동기화 시각을 기준일자로 사용
    latest_sync = max(
        (c.gp_profile_synced_at for c in companies if c.gp_profile_synced_at),
        default=None,
    )
    ref_date = latest_sync.strftime("%Y-%m-%d") if latest_sync else None
    return GPCompanyListResponse(
        total=total,
        page=page,
        size=size,
        items=items,
        data_reference_date=ref_date,
    )


@router.get(
    "/gp/companies/{company_id}",
    response_model=GPCompanyDetailResponse,
    summary="GP 운용사 상세 조회 (자조합/PEF 포함)",
)
async def get_gp_company_detail(
    company_id: int,
    _claims=Depends(get_jwt_claims),
    db: AsyncSession = Depends(get_db),
) -> GPCompanyDetailResponse:
    """GP 운용사 상세 정보를 조회한다. 연결된 KVIC 자조합 및 금감원 PEF 목록을 포함한다."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.company import Company
    from app.models.gp_fund import PEFFund

    stmt = (
        select(Company)
        .where(Company.id == company_id, Company.is_gp.is_(True))
        .options(
            selectinload(Company.kvic_funds),
            selectinload(Company.pef_funds_as_gp1).selectinload(PEFFund.gp2_company),
            selectinload(Company.pef_funds_as_gp1).selectinload(PEFFund.gp3_company),
            selectinload(Company.pef_funds_as_gp2).selectinload(PEFFund.gp1_company),
            selectinload(Company.pef_funds_as_gp2).selectinload(PEFFund.gp3_company),
            selectinload(Company.pef_funds_as_gp3).selectinload(PEFFund.gp1_company),
            selectinload(Company.pef_funds_as_gp3).selectinload(PEFFund.gp2_company),
        )
    )
    result = await db.execute(stmt)
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="GP 운용사를 찾을 수 없습니다.")

    kvic_items = [
        KVICFundItemResponse(
            id=f.id,
            fund_name=f.fund_name,
            fund_size=f.fund_size,
            operator_type=f.operator_type,
            established_date=f.established_date,
            synced_at=f.synced_at,
        )
        for f in company.kvic_funds
    ]

    # GP1/GP2/GP3 역할별 PEF를 합쳐서 중복 제거 (동일 PEF가 GP1+GP2에 동시 등장 방지)
    seen_pef_ids: set[int] = set()
    pef_items: list[PEFFundItemResponse] = []

    for p in company.pef_funds_as_gp1:
        seen_pef_ids.add(p.id)
        pef_items.append(
            PEFFundItemResponse(
                id=p.id,
                pef_name=p.pef_name,
                legal_basis=p.legal_basis,
                registration_date=p.registration_date,
                total_commitment=p.total_commitment,
                gp1_name=company.corp_name,
                gp2_name=p.gp2_company.corp_name if p.gp2_company else None,
                gp3_name=p.gp3_company.corp_name if p.gp3_company else None,
                synced_at=p.synced_at,
            )
        )

    for p in company.pef_funds_as_gp2:
        if p.id not in seen_pef_ids:
            seen_pef_ids.add(p.id)
            pef_items.append(
                PEFFundItemResponse(
                    id=p.id,
                    pef_name=p.pef_name,
                    legal_basis=p.legal_basis,
                    registration_date=p.registration_date,
                    total_commitment=p.total_commitment,
                    gp1_name=p.gp1_company.corp_name,
                    gp2_name=company.corp_name,
                    gp3_name=p.gp3_company.corp_name if p.gp3_company else None,
                    synced_at=p.synced_at,
                )
            )

    for p in company.pef_funds_as_gp3:
        if p.id not in seen_pef_ids:
            seen_pef_ids.add(p.id)
            pef_items.append(
                PEFFundItemResponse(
                    id=p.id,
                    pef_name=p.pef_name,
                    legal_basis=p.legal_basis,
                    registration_date=p.registration_date,
                    total_commitment=p.total_commitment,
                    gp1_name=p.gp1_company.corp_name,
                    gp2_name=p.gp2_company.corp_name if p.gp2_company else None,
                    gp3_name=company.corp_name,
                    synced_at=p.synced_at,
                )
            )

    return GPCompanyDetailResponse(
        id=company.id,
        corp_name=company.corp_name,
        corp_name_eng=company.corp_name_eng,
        corp_code=company.corp_code,
        finance_company_code=company.finance_company_code,
        est_dt=company.est_dt,
        adres=company.adres,
        phn_no=company.phn_no,
        gp_authorization_date=company.gp_authorization_date,
        gp_aum=company.gp_aum,
        gp_total_commitment=company.gp_total_commitment,
        gp_fund_count=company.gp_fund_count,
        gp_employee_count=company.gp_employee_count,
        sources=(company.gp_strategy_tags or {}).get("sources", []),
        strategies=(company.gp_strategy_tags or {}).get("strategies", []),
        gp_profile_synced_at=company.gp_profile_synced_at,
        kvic_funds=kvic_items,
        pef_funds=pef_items,
    )


@router.get("/gp/{company_name}", response_model=GPRegistryItem | None, summary="운용사 상세 조회")
async def get_registered_gp(
    company_name: str,
    _claims=Depends(get_jwt_claims),
    service: PublicDataService = Depends(get_public_data_service),
):
    """특정 운용사의 등록 정보를 조회한다."""
    result = await service.get_gp_by_name(company_name)
    await service.close()
    return result


@router.post("/gp/sync", response_model=GPSyncResponse, summary="GP 프로파일 DB 동기화")
async def sync_gp_profiles(
    _claims=Depends(get_jwt_claims),
    db: AsyncSession = Depends(get_db),
    service: PublicDataService = Depends(get_public_data_service),
):
    """공공데이터포털 GP 레지스트리를 Company 테이블에 동기화한다.

    - 기존 Company와 EntityResolver로 매칭 → GP 컬럼 업데이트
    - 미매칭 → 신규 Company 생성 (is_gp=True)
    - CompanyAlias 자동 등록
    """
    result = await service.sync_gp_profiles(db)
    await service.close()
    return GPSyncResponse(
        total_api_items=result.total_api_items,
        created=result.created,
        updated=result.updated,
        aliases_added=result.aliases_added,
        errors=result.errors,
    )


# ──────────────────────────────────────────────
# FreeSIS 기관전용 사모펀드 GP
# ──────────────────────────────────────────────


@router.post(
    "/gp/freesis/upload",
    response_model=FreeSISSyncResponse,
    summary="FreeSIS 기관전용 사모펀드 GP 엑셀 업로드 및 동기화",
)
async def upload_freesis_gp(
    file: UploadFile,
    reference_date: str | None = Query(None, description="데이터 기준일 (YYYY-MM-DD)"),
    _claims=Depends(get_jwt_claims),
    db: AsyncSession = Depends(get_db),
) -> FreeSISSyncResponse:
    """FreeSIS에서 다운로드한 기관전용 사모펀드 운용사별 통계 엑셀을 업로드하여 동기화한다.

    자료 확보 방법::

        1. https://freesis.kofia.or.kr 접속 (회원가입 불필요)
        2. 상단 메뉴: 펀드 > 운용사통계
        3. 좌측 트리: 사모 > 기관전용 사모집합투자기구
        4. 검색 조건 설정:
           - 기준일: 원하는 월말 날짜 선택 (예: 2024-12-31)
           - 구분: "설정잔액" 선택 (운용사별 AUM 확인)
           - 또는 "설정·해지" 선택 (자금 유출입 확인)
        5. [조회] 버튼 클릭
        6. 결과 테이블 상단의 [엑셀 다운로드] 아이콘 클릭
        7. 다운로드된 .xlsx 파일을 이 API에 업로드

    기대 컬럼: 운용사명, 설정잔액(백만원), 펀드수, 자금유입(백만원), 자금유출(백만원)

    주의사항:
        - FreeSIS 데이터는 매월 말 기준으로 갱신됨
        - 엑셀 파일만 지원 (.xlsx). CSV는 지원하지 않음
        - 기준일(reference_date)을 지정하면 파싱 결과에 기준일이 태깅됨
    """
    service = FreeSISService()
    content = await file.read()
    filename = file.filename or ""

    if not filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="FreeSIS 업로드는 엑셀 파일(.xlsx)만 지원합니다. "
            "FreeSIS(freesis.kofia.or.kr) > 펀드 > 운용사통계 > "
            "기관전용 사모집합투자기구에서 엑셀을 다운로드하세요.",
        )

    if len(content) > _MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"파일 크기가 {_MAX_UPLOAD_SIZE // (1024 * 1024)}MB를 초과합니다.",
        )

    if content[:4] not in (_XLSX_MAGIC, _XLS_MAGIC):
        raise HTTPException(
            status_code=400,
            detail="유효한 엑셀 파일이 아닙니다. FreeSIS에서 다운로드한 .xlsx 파일을 업로드하세요.",
        )

    logger.info("FreeSIS 업로드: file=%s, size=%d, reference_date=%s", filename, len(content), reference_date)

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        items = service.parse_freesis_excel(tmp_path, reference_date=reference_date)
    except Exception as exc:
        logger.warning("FreeSIS 엑셀 파싱 실패: file=%s, error=%s", filename, exc)
        raise HTTPException(
            status_code=400,
            detail="엑셀 파일을 파싱할 수 없습니다. FreeSIS에서 다운로드한 원본 .xlsx 파일인지 확인하세요.",
        ) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    result = await service.sync_pef_gp_from_freesis(db, items)
    return FreeSISSyncResponse(
        total_items=result.total_items,
        created=result.created,
        updated=result.updated,
        matched_existing=result.matched_existing,
        errors=result.errors,
    )


# ──────────────────────────────────────────────
# KVIC 모태펀드 운용사정보
# ──────────────────────────────────────────────


@router.post(
    "/gp/kvic/upload",
    response_model=KVICSyncResponse,
    summary="KVIC 모태펀드 자조합 운용사정보 파일 업로드 및 동기화",
)
async def upload_kvic_gp(
    file: UploadFile,
    _claims=Depends(get_jwt_claims),
    db: AsyncSession = Depends(get_db),
) -> KVICSyncResponse:
    """KVIC(한국벤처투자) 모태펀드 자조합 운용사정보 CSV/Excel 파일을 업로드하여 동기화한다.

    자료 확보 방법::

        1. https://www.data.go.kr 접속 → 회원가입/로그인
        2. 검색: "한국벤처투자_모태펀드 자조합 운용사정보" (데이터셋 #3060708)
           직접 URL: https://www.data.go.kr/data/3060708/fileData.do
        3. [다운로드] 버튼 클릭 → CSV 파일 다운로드
           - 파일명 예시: 한국벤처투자_모태펀드 자조합 운용사정보_20251212.csv
           - 인코딩: CP949 (한글 Windows 기본 인코딩, 자동 감지됨)
        4. 다운로드된 CSV 파일을 이 API에 업로드

    기대 컬럼 (3컬럼 형식):
        - 대표운영사: 운용사명
        - 운영사구분: 벤처투자회사, 신기술사, LLC, 기타운용사, 기타법인, 개인
        - 자조합 규모(백만원): 조합 규모

    참고:
        - 2024-12 기준 약 1,400건, 327개 고유 운용사
        - 동일 운용사가 여러 조합에 등장 → 자동 중복 제거 (최대 fund_size 보존)
        - CSV(.csv)와 Excel(.xlsx/.xls) 모두 지원
        - CSV 인코딩: UTF-8-sig, CP949, EUC-KR 자동 감지
    """
    service = KVICService()
    content = await file.read()
    filename = file.filename or ""

    if len(content) > _MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"파일 크기가 {_MAX_UPLOAD_SIZE // (1024 * 1024)}MB를 초과합니다.",
        )

    logger.info("KVIC 업로드: file=%s, size=%d", filename, len(content))

    try:
        if filename.endswith(".csv"):
            # CSV 콘텐츠 검증: 바이너리 파일이 .csv 확장자로 위장한 경우 차단
            if content[:4] in (_XLSX_MAGIC, _XLS_MAGIC) or content[:2] == b"MZ":
                raise HTTPException(
                    status_code=400,
                    detail="CSV 확장자이나 실제 콘텐츠가 CSV 형식이 아닙니다. 올바른 CSV 파일을 업로드하세요.",
                )
            items = service.parse_kvic_csv(content)
        else:
            if content[:4] not in (_XLSX_MAGIC, _XLS_MAGIC):
                raise HTTPException(
                    status_code=400,
                    detail="유효한 엑셀 파일이 아닙니다. CSV(.csv) 또는 엑셀(.xlsx) 파일을 업로드하세요.",
                )
            # Excel 처리
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
            try:
                items = service.parse_kvic_excel(tmp_path)
            finally:
                tmp_path.unlink(missing_ok=True)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("KVIC 파일 파싱 실패: file=%s, error=%s", filename, exc)
        raise HTTPException(
            status_code=400,
            detail="파일을 파싱할 수 없습니다. data.go.kr에서 다운로드한 원본 파일인지 확인하세요.",
        ) from exc

    result = await service.sync_kvic_gp_data(db, items)
    return KVICSyncResponse(
        total_items=result.total_items,
        unique_operators=result.unique_operators,
        created=result.created,
        updated=result.updated,
        matched_existing=result.matched_existing,
        errors=result.errors,
    )


# ──────────────────────────────────────────────
# 금감원(FSS) 기관전용 PEF 현황
# ──────────────────────────────────────────────


@router.post(
    "/gp/fss-pef/upload",
    response_model=FSSPEFSyncResponse,
    summary="금감원 PEF 현황 엑셀 업로드 및 동기화",
)
async def upload_fss_pef(
    file: UploadFile,
    _claims=Depends(get_jwt_claims),
    db: AsyncSession = Depends(get_db),
) -> FSSPEFSyncResponse:
    """금감원에서 공개한 기관전용 사모집합투자기구 현황 엑셀을 업로드하여 동기화한다.

    자료 확보 방법::

        1. 금감원 통합홈페이지(fss.or.kr) 또는 전자공시시스템(dart.fss.or.kr) 접속
        2. 기관전용 사모집합투자기구 현황 파일 다운로드
        3. 다운로드된 .xlsx 파일을 이 API에 업로드

    기대 컬럼: 순번, 설립근거법률, PEF 명칭, 등록일, GP1, GP2, GP3, 총약정액(억원)
    """
    service = FSSPEFService()
    content = await file.read()
    filename = file.filename or ""

    if not filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="엑셀 파일(.xlsx)만 지원합니다.",
        )

    if len(content) > _MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"파일 크기가 {_MAX_UPLOAD_SIZE // (1024 * 1024)}MB를 초과합니다.",
        )

    if content[:4] not in (_XLSX_MAGIC, _XLS_MAGIC):
        raise HTTPException(
            status_code=400,
            detail="유효한 엑셀 파일이 아닙니다.",
        )

    logger.info("FSS PEF 업로드: file=%s, size=%d", filename, len(content))

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        items = service.parse_fss_pef_excel(tmp_path)
    except Exception as exc:
        logger.warning("FSS PEF 엑셀 파싱 실패: file=%s, error=%s", filename, exc)
        raise HTTPException(
            status_code=400,
            detail="엑셀 파일을 파싱할 수 없습니다. 금감원 PEF 현황 원본 파일인지 확인하세요.",
        ) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    result = await service.sync_pef_data(db, items)
    return FSSPEFSyncResponse(
        total_items=result.total_items,
        created=result.created,
        matched_existing=result.matched_existing,
        new_companies=result.new_companies,
        errors=result.errors,
    )
