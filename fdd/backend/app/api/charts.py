"""Chart API 엔드포인트 — Phase 3 (차트 서비스 강화).

Plotly 기반 차트를 생성하여 PNG 이미지로 반환합니다.
EBITDA Bridge, NWC Bridge, Net Debt Bridge 등 FDD 보고서용 차트를 지원합니다.
"""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.auth.dependencies import CurrentUser, get_current_user
from app.renderers.design_system import get_design_system
from app.schemas.chart import (
    EBITDABridgeRequest,
    GenericWaterfallRequest,
    NetDebtBridgeRequest,
    NWCBridgeRequest,
)
from app.services.chart.waterfall import create_ebitda_bridge, create_generic_waterfall

router = APIRouter(prefix="/charts", tags=["charts"])


def _parse_values(values: list[str | None]) -> list[Decimal | None]:
    """문자열 값 리스트를 Decimal 리스트로 변환."""
    result: list[Decimal | None] = []
    for v in values:
        if v is None:
            result.append(None)
        else:
            result.append(Decimal(v))
    return result


@router.post(
    "/ebitda-bridge",
    response_class=StreamingResponse,
    summary="EBITDA Bridge 워터폴 차트 생성",
    description="Reported EBITDA에서 Adjusted EBITDA까지의 조정 과정을 시각화한 워터폴 차트를 생성합니다.",
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "PNG 이미지 반환",
        }
    },
)
async def generate_ebitda_bridge(
    request: EBITDABridgeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    design_system: dict[str, Any] = Depends(get_design_system),
) -> StreamingResponse:
    """EBITDA Bridge 워터폴 차트를 생성합니다.

    - 첫 번째 항목: Reported EBITDA (absolute)
    - 중간 항목들: 조정 금액 (relative)
    - 마지막 항목: Adjusted EBITDA (total, 값은 null 가능)

    Returns:
        PNG 이미지 스트림
    """
    if len(request.categories) != len(request.values):
        raise HTTPException(
            status_code=400,
            detail="categories와 values의 개수가 일치해야 합니다",
        )

    try:
        decimal_values = _parse_values(request.values)
        buffer = create_ebitda_bridge(
            categories=request.categories,
            values=decimal_values,
            title=request.title,
            design_override=design_system.get("charts", {}).get("waterfall"),
        )
        return StreamingResponse(
            buffer,
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=ebitda_bridge.png"},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/nwc-bridge",
    response_class=StreamingResponse,
    summary="NWC Bridge 워터폴 차트 생성",
    description="Net Working Capital 구성 항목을 시각화한 워터폴 차트를 생성합니다.",
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "PNG 이미지 반환",
        }
    },
)
async def generate_nwc_bridge(
    request: NWCBridgeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    design_system: dict[str, Any] = Depends(get_design_system),
) -> StreamingResponse:
    """NWC Bridge 워터폴 차트를 생성합니다."""
    if len(request.categories) != len(request.values):
        raise HTTPException(
            status_code=400,
            detail="categories와 values의 개수가 일치해야 합니다",
        )

    try:
        decimal_values = _parse_values(request.values)
        buffer = create_generic_waterfall(
            categories=request.categories,
            values=decimal_values,
            title=request.title,
            y_axis_title="금액 (백만원)",
            design_override=design_system.get("charts", {}).get("waterfall"),
        )
        return StreamingResponse(
            buffer,
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=nwc_bridge.png"},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/net-debt-bridge",
    response_class=StreamingResponse,
    summary="Net Debt Bridge 워터폴 차트 생성",
    description="Net Debt 구성 항목을 시각화한 워터폴 차트를 생성합니다.",
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "PNG 이미지 반환",
        }
    },
)
async def generate_net_debt_bridge(
    request: NetDebtBridgeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    design_system: dict[str, Any] = Depends(get_design_system),
) -> StreamingResponse:
    """Net Debt Bridge 워터폴 차트를 생성합니다."""
    if len(request.categories) != len(request.values):
        raise HTTPException(
            status_code=400,
            detail="categories와 values의 개수가 일치해야 합니다",
        )

    try:
        decimal_values = _parse_values(request.values)
        buffer = create_generic_waterfall(
            categories=request.categories,
            values=decimal_values,
            title=request.title,
            y_axis_title="금액 (백만원)",
            design_override=design_system.get("charts", {}).get("waterfall"),
        )
        return StreamingResponse(
            buffer,
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=net_debt_bridge.png"},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/waterfall",
    response_class=StreamingResponse,
    summary="범용 워터폴 차트 생성",
    description="커스텀 데이터로 워터폴 차트를 생성합니다.",
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "PNG 이미지 반환",
        }
    },
)
async def generate_generic_waterfall(
    request: GenericWaterfallRequest,
    current_user: CurrentUser = Depends(get_current_user),
    design_system: dict[str, Any] = Depends(get_design_system),
) -> StreamingResponse:
    """범용 워터폴 차트를 생성합니다.

    measures를 지정하여 각 항목의 타입(absolute/relative/total)을 제어할 수 있습니다.
    """
    if len(request.categories) != len(request.values):
        raise HTTPException(
            status_code=400,
            detail="categories와 values의 개수가 일치해야 합니다",
        )

    if request.measures and len(request.measures) != len(request.categories):
        raise HTTPException(
            status_code=400,
            detail="measures와 categories의 개수가 일치해야 합니다",
        )

    try:
        decimal_values = _parse_values(request.values)
        buffer = create_generic_waterfall(
            categories=request.categories,
            values=decimal_values,
            measures=request.measures,
            title=request.title,
            y_axis_title=request.y_axis_title,
            design_override=design_system.get("charts", {}).get("waterfall"),
        )
        return StreamingResponse(
            buffer,
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=waterfall.png"},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
