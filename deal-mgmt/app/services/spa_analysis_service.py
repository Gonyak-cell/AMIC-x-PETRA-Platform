"""SPA 계약서 LLM 역분석 서비스 — 3단계 Human-in-the-Loop 파이프라인.

Step 1: 원문 → 변수 추출 (deal_structure/industry_type 분류, 동적 BOOLEAN 발견)
Step 2: 확정 변수 → 조항 분해 + Jinja2 변환 + condition_expression 생성
Step 3: 최종 확정 → DB 저장 (ContractTemplate + Clauses + Variables)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.contract_clause import ContractClause
from app.models.contract_template import ContractTemplate
from app.models.enums import (
    ContractTemplateStatus,
    LegalDocType,
    TemplateVariableInputType,
)
from app.models.template_variable import TemplateVariable
from app.ralph.llm_client import RalphLLMClient
from app.schemas.spa_analysis import (
    AnalyzedClause,
    DiscoveredBoolean,
    ExtractedVariable,
)
from app.services.contract_generation_service import (
    _parse_expression,
    sanitize_html,
)

logger = logging.getLogger(__name__)


class Step1Result(TypedDict):
    """Step 1 분석 결과 — 이름 기반 접근으로 tuple 인덱스 오류 방지."""

    session_id: str
    variables: list[ExtractedVariable]
    deal_structure: str
    industry_type: str
    detected_doc_type: str
    discovered_booleans: list[DiscoveredBoolean]
    sha_type: str | None
    exit_strategy: str | None
    bta_scope: str | None
    severance_pay_handling: str | None
    security_type: str | None
    transaction_context: str | None
    mou_transaction_type: str | None
    deposit_handling: str | None
    cost: float | None
    model: str | None


# ── 세션 관리 (인메모리, TTL 30분) ────────────────────────────────────────────

_SESSION_TTL = 1800.0  # 30분
_MAX_COST_PER_SESSION = 5.0  # USD
_MAX_SESSIONS = 100  # 인메모리 세션 수 상한 (B-3)
_LLM_CALL_TIMEOUT = 120.0  # LLM 호출 타임아웃 (초) (D-4)

# 조건식 내 금지 토큰 (import, exec, eval, open, 던더) — defence-in-depth (B-1)

_FORBIDDEN_RE = re.compile(
    r"(__\w+__|import|exec|eval|compile|globals|locals|getattr|setattr|delattr|open|os\.|sys\.|subprocess)",
    re.IGNORECASE,
)


@dataclass
class AnalysisSession:
    """Step 간 상태를 보존하는 분석 세션."""

    session_id: str
    spa_text: str
    owner_user_id: str = ""
    detected_doc_type: str = "SPA"
    created_at: float = field(default_factory=time.monotonic)
    cost_usd: float = 0.0
    model_used: str | None = None


_sessions: dict[str, AnalysisSession] = {}


def _get_session(session_id: str, *, owner_user_id: str = "") -> AnalysisSession:
    """세션을 조회한다. 만료/미존재/소유자 불일치 시 ValueError."""
    _cleanup_expired_sessions()
    session = _sessions.get(session_id)
    if session is None:
        msg = "분석 세션이 만료되었거나 존재하지 않습니다. Step 1부터 다시 시작하세요."
        raise ValueError(msg)
    # C1: 세션 소유권 검증 — 타 사용자의 계약서 원문 접근 차단
    if owner_user_id and session.owner_user_id and session.owner_user_id != owner_user_id:
        msg = "이 분석 세션에 접근할 권한이 없습니다."
        raise ValueError(msg)
    return session


def _cleanup_expired_sessions() -> None:
    """만료된 세션을 제거한다."""
    now = time.monotonic()
    expired = [k for k, v in _sessions.items() if now - v.created_at > _SESSION_TTL]
    if expired:
        logger.debug("만료 세션 정리: %d건", len(expired))
    for k in expired:
        del _sessions[k]


# ── LLM 클라이언트 ────────────────────────────────────────────────────────────

_llm_client: RalphLLMClient | None = None


def _get_llm_client() -> RalphLLMClient:
    """LLM 클라이언트 싱글턴을 반환한다."""
    global _llm_client
    if _llm_client is None:
        _llm_client = RalphLLMClient.from_settings(settings)
    return _llm_client


# ── LLM 호출 + JSON 파싱 ──────────────────────────────────────────────────────


async def _call_llm_json(
    system_prompt: str,
    user_prompt: str,
    *,
    max_retries: int = 1,
) -> tuple[dict[str, Any], float | None, str | None]:
    """LLM을 호출하고 JSON 응답을 파싱한다.

    Returns:
        (파싱된 dict, 비용 USD, 사용 모델)
    """
    llm = _get_llm_client()
    if not llm.is_available:
        raise RuntimeError("사용 가능한 LLM 프로바이더가 없습니다.")

    cost_before = llm.total_cost_usd

    for attempt in range(max_retries + 1):
        try:
            raw = await asyncio.wait_for(
                llm.call(system_prompt, user_prompt),
                timeout=_LLM_CALL_TIMEOUT,
            )
            # LLM 출력에서 JSON 블록 추출 (```json ... ``` 또는 순수 JSON)
            parsed = _extract_json(raw)
            cost = llm.total_cost_usd - cost_before
            model_name = getattr(llm, "_primary_model", None)
            return parsed, cost, model_name
        except TimeoutError as exc:
            raise RuntimeError(f"LLM 호출이 {_LLM_CALL_TIMEOUT:.0f}초 내에 응답하지 않았습니다.") from exc
        except (json.JSONDecodeError, ValueError) as exc:
            if attempt < max_retries:
                logger.warning("LLM JSON 파싱 실패 (시도 %d/%d): %s", attempt + 1, max_retries + 1, exc)
                continue
            raise ValueError(f"LLM 응답을 JSON으로 파싱할 수 없습니다: {exc}") from exc

    raise RuntimeError("unreachable")  # pragma: no cover


def _extract_json(text: str) -> dict[str, Any]:
    """LLM 출력에서 JSON 객체를 추출한다."""
    stripped = text.strip()

    # ```json ... ``` 블록 추출
    if "```json" in stripped:
        start = stripped.index("```json") + 7
        end = stripped.index("```", start)
        stripped = stripped[start:end].strip()
    elif "```" in stripped:
        start = stripped.index("```") + 3
        end = stripped.index("```", start)
        stripped = stripped[start:end].strip()

    # 순수 JSON 파싱
    result = json.loads(stripped)
    if not isinstance(result, dict):
        msg = f"JSON 최상위가 object가 아닙니다: {type(result).__name__}"
        raise ValueError(msg)
    return result


# ── 조건식 검증 ───────────────────────────────────────────────────────────────


def validate_condition_expression(expr: str | None) -> bool:
    """condition_expression의 안전성을 검증한다.

    _FORBIDDEN_RE로 금지 토큰(import/exec/eval/open/던더)을 먼저 차단하고,
    AST 파싱으로 문법 안전성을 검증한다.
    """
    if not expr:
        return True
    if _FORBIDDEN_RE.search(expr):
        logger.warning("조건식에 금지 토큰 발견: %s", expr)
        return False
    try:
        _parse_expression(expr)
        return True
    except SyntaxError:
        return False


# ── Step 1: 변수 추출 ─────────────────────────────────────────────────────────

_STEP1_SYSTEM_PROMPT = """당신은 한국 M&A 법률 문서 전문가이자 데이터 엔지니어입니다.
M&A 관련 계약서(SPA/SHA/BTA/SSA/MOU) 원문을 분석하여 재사용 가능한 템플릿 변수를 추출합니다.

## 0. 계약서 유형 감지 (detected_doc_type)
원문의 제목, 내용, 구조를 분석하여 계약서 유형을 감지합니다:
- SPA: 주식매매계약서 (Stock Purchase Agreement) — "주식 양도", "주식매매", "대상주식", "매매대금", "주당 가격"
- SHA: 주주간계약서 (Shareholders' Agreement) — "주주간", "주주 권리", "이사회 구성", "이사 지명", "동반매도", "Tag-Along", "Drag-Along", "Put Option", "Call Option", "의결권", "거부권"
- BTA: 영업양수도계약서 (Business Transfer Agreement) — "영업양수도", "영업 양도", "사업 양도", "사업 이전", "영업 매각", "양도대상 영업", "양도대상 자산", "임직원 승계", "전환서비스", "TSA"
- SSA: 신주인수계약서 (Share Subscription Agreement) — "신주 발행", "신주 인수", "유상증자", "주금 납입"
- MOU: 양해각서 (Memorandum of Understanding) — "양해각서", "의향서", "우선협상"
핵심 구분: SPA는 "주식(지분)"을 거래, BTA는 "자산/부채/영업"을 거래, SHA는 "주주 간 권리/의무"를 규정

## 1. 분석 순서
1. 전문(Preamble) → 당사자 정보 (이름, 주소, 대표자, 사업자등록번호/법인등록번호)
   - **복수 당사자 주의**: 매도인/매수인이 2인 이상인 경우 seller_name_1, seller_name_2 등으로 분리하거나, seller_names (TEXTAREA)로 통합
2. 제1조(정의) → 대상회사, 대상주식, 기준일, 액면가 추출
3. 제2조(매매) → 주식 수, 지분비율, 매매대금, 주당 가격
4. 제3조(종결) → 체결일, 거래종결일, long-stop date
5. 제4~5조(진술보장) → 중요성 기준(materiality_threshold), 존속기간(survival_period_months)
6. 제8조(손해배상) → 손해배상 한도(indemnity_cap), 바스켓(indemnity_basket)
7. 전체 스캔 → deal_structure / industry_type 분류
8. 전체 스캔 → 조건부 조항 존재 여부 (BOOLEAN)
9. 별지/공개목록(Disclosure Schedule) 참조 여부 발견 → has_disclosure_schedule BOOLEAN

## 2. 기본 변수 목록 (반드시 원문에서 찾아 포함)
| group_name | variable_key | input_type | 설명 |
|-----------|-------------|-----------|------|
| 당사자 정보 | seller_name | TEXT | 매도인 명칭 |
| 당사자 정보 | seller_address | TEXT | 매도인 주소 |
| 당사자 정보 | seller_representative | TEXT | 매도인 대표자 |
| 당사자 정보 | seller_reg_number | TEXT | 매도인 사업자등록번호 |
| 당사자 정보 | buyer_name | TEXT | 매수인 명칭 |
| 당사자 정보 | buyer_address | TEXT | 매수인 주소 |
| 당사자 정보 | buyer_representative | TEXT | 매수인 대표자 |
| 당사자 정보 | buyer_reg_number | TEXT | 매수인 사업자등록번호 |
| 거래 대상 | target_company | TEXT | 대상회사 명칭 |
| 거래 대상 | target_address | TEXT | 대상회사 소재지 |
| 거래 대상 | target_reg_number | TEXT | 대상회사 사업자등록번호 |
| 거래 대상 | share_count | NUMBER | 양도 주식 수 |
| 거래 대상 | share_ratio | PERCENTAGE | 지분율 |
| 거래 대상 | par_value | CURRENCY | 1주 액면가 |
| 거래 조건 | total_purchase_price | CURRENCY | 총 매매대금 (원 단위) |
| 거래 조건 | price_per_share | CURRENCY | 주당 매매가격 |
| 일정 | signing_date | DATE | 계약 체결일 |
| 일정 | closing_date | DATE | 거래 종결일 |
| 일정 | base_financial_date | DATE | 기준 재무제표 일자 |
| 일정 | long_stop_date | DATE | 최종 기한 (Long-stop date) |
| 특약 사항 | escrow_included | BOOLEAN | 에스크로 포함 여부 |
| 특약 사항 | escrow_amount | CURRENCY | 에스크로 금액 (visible: escrow_included == True) |
| 특약 사항 | escrow_period_months | NUMBER | 에스크로 기간 (visible: escrow_included == True) |
| 특약 사항 | earnout_included | BOOLEAN | 어닝아웃 포함 여부 |
| 특약 사항 | non_compete_years | NUMBER | 경업금지 기간 (년, 0=미포함) |
| 특약 사항 | has_price_adjustment | BOOLEAN | 가격조정 조항 포함 여부 |
| 손해배상 | indemnity_cap | CURRENCY | 손해배상 한도 |
| 손해배상 | indemnity_basket | CURRENCY | 바스켓 금액 |
| 손해배상 | survival_period_months | NUMBER | 진술보증 존속기간 (개월) |
| 기타 | governing_law | SELECT | 준거법 |
| 기타 | dispute_resolution | SELECT | 분쟁해결 방법 |

원문에 해당 항목이 없으면 extracted_value를 null로, confidence를 낮게 설정하세요.

## 3. deal_structure 분류 기준
- PURE_SHARE_TRANSFER: 단순 주식 양수도 (분할/유상증자 없음)
- CARVE_OUT: 물적분할 + 주식 양수도 (분할 관련 조항 포함)
- WITH_NEW_SHARES: 유상증자 동반
- OTHER_STRUCTURE: 위에 해당하지 않는 복합 구조

## 4. industry_type 분류 기준
- MANUFACTURING: 제조업 (공장, 생산, 재고, 환경 관련 조항)
- SOFTWARE: 소프트웨어/IT (지식재산권, 라이선스 관련 조항)
- FRANCHISE: 가맹점/프랜차이즈
- GENERAL: 특정 산업 특화 없음
- OTHER_INDUSTRY: 위에 해당하지 않는 산업

## 5. input_type 매핑 규칙
- 이름/주소/회사명/등록번호 → TEXT
- 긴 설명/비고 → TEXTAREA
- 금액 (원, 억원, 백만원) → CURRENCY (반드시 원 단위로 정규화: 10억 → 1000000000)
- 비율 (%) → PERCENTAGE
- 날짜 → DATE
- 주식 수, 기간(개월/년) 등 → NUMBER
- 예/아니오 → BOOLEAN
- 선택지 → SELECT (select_options 필수)

## 6. 동적 BOOLEAN 발견 규칙
표준 BOOLEAN 외에, 원문에서 특수 조항이 발견되면 has_{영문명} BOOLEAN을 자율 생성:
- 동반매도청구권 → has_drag_along
- 동반매도참여권 → has_tag_along
- 보호예수/Lock-up → has_lock_up
- 중대한 부정적 변경(MAC) → has_mac_clause
- 분할 관련 특약 → has_carve_out_provisions
- 풋옵션 → has_put_option / 콜옵션 → has_call_option
- 공개목록/별지 참조 → has_disclosure_schedule
- 기타 발견 시 자율 생성

## 7. 거래 구조별 추가 변수
CARVE_OUT (물적분할 + 주식양도) 구조가 감지되면 아래 변수를 추가 추출:
| variable_key | input_type | 설명 |
|-------------|-----------|------|
| split_company_name | TEXT | 분할신설회사 명칭 |
| split_base_date | DATE | 분할 기준일 |
| split_registration_date | DATE | 분할 등기 예정일 |
| split_ratio | PERCENTAGE | 분할 비율 |
| pre_split_assets_desc | TEXTAREA | 분할 전 승계 자산/부채 범위 |
| has_split_warranties | BOOLEAN | 분할 관련 추가 진술보장 존재 |
| has_post_split_covenants | BOOLEAN | 분할 후 존속회사 확약 존재 |

WITH_NEW_SHARES (유상증자 동반) 구조가 감지되면 아래 변수를 추가 추출:
| variable_key | input_type | 설명 |
|-------------|-----------|------|
| new_share_count | NUMBER | 신주 발행 수 |
| subscription_price | CURRENCY | 신주 인수대금 |
| capital_increase_date | DATE | 유상증자 예정일 |
| has_preemptive_waiver | BOOLEAN | 기존 주주 신주인수권 포기 여부 |

## 8. 복수 당사자 처리 규칙
매도인/매수인이 2인 이상인 경우:
- 2인: seller_name_1, seller_name_2 (TEXT) + seller_address_1, seller_address_2 패턴
- 3인 이상: seller_names (TEXTAREA, 줄바꿈 구분) + seller_count (NUMBER)
- 대주주 + 소수주주 구분이 명확한 경우: majority_seller_name (TEXT) + minority_sellers (TEXTAREA)
- 연대책임 여부: joint_and_several_liability (BOOLEAN) — "연대하여" 문구 감지 시

## 9. 어닝아웃/조건부 대금 세부 추출
earnout_included == True인 경우 아래 변수를 추가 추출:
| variable_key | input_type | 설명 |
|-------------|-----------|------|
| earnout_period_months | NUMBER | 어닝아웃 측정 기간 (개월) |
| earnout_metric | TEXT | 성과 측정 기준 (예: EBITDA, 매출액) |
| earnout_target_amount | CURRENCY | 어닝아웃 목표 금액 |
| earnout_max_amount | CURRENCY | 어닝아웃 최대 지급액 |
| earnout_payment_schedule | TEXT | 지급 일정 설명 |

## 10. 가격조정 세부 추출
has_price_adjustment == True인 경우 아래 변수를 추가 추출:
| variable_key | input_type | 설명 |
|-------------|-----------|------|
| price_adj_base_date | DATE | 가격조정 기준일 |
| price_adj_method | SELECT | 조정 방식 (select_options: {"nwc": "순운전자본", "nav": "순자산", "ebitda": "EBITDA"}) |
| price_adj_cap | CURRENCY | 가격조정 상한 |
| price_adj_dispute_period_days | NUMBER | 이의제기 기한 (일) |

## 11. R&W 하위조 산업별 특화 변수
industry_type에 따라 아래 BOOLEAN 변수를 추가 스캔:
- MANUFACTURING: has_environmental_rw (환경), has_product_liability_rw (제조물책임), has_facility_rw (시설/설비)
- SOFTWARE: has_ip_rw (지식재산권), has_data_privacy_rw (개인정보), has_license_rw (라이선스/OSS)
- FRANCHISE: has_franchise_rw (가맹계약), has_territory_rw (영업지역 보호)
위 변수는 원문에서 해당 진술보장 하위조가 발견된 경우에만 추출합니다.

## 출력 형식
JSON만 반환하세요. 설명이나 코멘트를 포함하지 마세요.
```json
{
  "detected_doc_type": "SPA",
  "variables": [
    {
      "variable_key": "seller_name",
      "input_type": "TEXT",
      "question_label": "매도인 명칭",
      "description": "매도인의 법인명 또는 성명",
      "extracted_value": "주식회사 ABC",
      "default_value": null,
      "is_required": true,
      "select_options": null,
      "display_order": 1,
      "group_name": "당사자 정보",
      "visible_condition": null,
      "confidence": 0.95
    }
  ],
  "deal_structure": "PURE_SHARE_TRANSFER",
  "industry_type": "GENERAL",
  "discovered_booleans": [
    {
      "variable_key": "has_drag_along",
      "question_label": "동반매도청구권 조항 포함 여부",
      "detected_in_clause": "제8조 (동반매도청구권)"
    }
  ]
}
```"""

# ── SHA Step 1: 변수 추출 ────────────────────────────────────────────────────

_SHA_STEP1_SYSTEM_PROMPT = """당신은 한국 M&A 법률 문서 전문가이자 데이터 엔지니어입니다.
주주간계약서(SHA, Shareholders' Agreement) 원문을 분석하여 재사용 가능한 템플릿 변수를 추출합니다.

## 0. 계약서 유형 확정
이 계약서는 주주간계약서(SHA)입니다.
detected_doc_type은 반드시 "SHA"로 설정하세요.

## 1. SHA 유형 분류 (sha_type → deal_structure에도 동일 값)
원문의 거래 배경, 당사자 관계, 투자 목적을 분석하여 분류합니다:
- POST_BUYOUT: 경영권 인수 완료 후 주주간 권리의무 (SPA 이후 체결, 대주주 + PE/전략적 투자자)
- JOINT_VENTURE: 합작투자 목적 (2개 이상 법인이 공동 출자, 합작회사 설립/운영)
- MINORITY_INVESTMENT: 소수지분 투자 (VC/PI 투자, 지분율 50% 미만, 투자자 보호 중심)
- OTHER_TYPE: 위에 해당하지 않는 경우

## 2. Exit 전략 분류 (exit_strategy)
- IPO_FOCUSED: IPO 관련 조항이 주요 exit 경로 (상장 의무, IPO 협력, 상장 시 공동매각)
- MNA_FOCUSED: M&A 매각이 주요 exit 경로 (drag-along, 매각 우선, 매각 결정권)
- OTHER_STRATEGY: IPO/M&A 외 exit (자사주 매입, 청산 등) 또는 exit 조항 미약

## 3. 분석 순서
1. 전문(Preamble) → 주주 목록, 지분구조, 대상회사 정보
2. 정의 조항 → 핵심 정의 (관계사, 주주, 신주, 보통주/우선주 등)
3. 이사회 구성 → 총 의석수, 주주별 지명권, 대표이사 선임, 의장, 정족수
4. 의결/동의 사항 → 주주 동의 필요 사항, Veto 항목, 특별결의 요건
5. 주식 처분 제한 → Lock-up, ROFR, ROFO, 동의 필요 여부
6. Tag-Along / Drag-Along → 조건, 비율, 절차
7. 옵션 → Put/Call 조건, 행사가격 산식, 행사 기간
8. 신주인수권/희석방지 → Anti-dilution, Pre-emptive Rights
9. 배당/수익분배 → 배당 정책, Waterfall, 우선배당
10. Exit → IPO 의무/일정, 매각 절차, Drag 임계치
11. 정보권/검사권 → 재무정보 제공 주기, 접근 범위, Key-Man 조항
12. 비밀유지/경업금지 → 기간, 범위, 위반 시 제재
13. 계약 기간/종료 → 존속 기간, 종료 사유
14. 전체 스캔 → 조건부 BOOLEAN 발견

## 4. 기본 변수 목록 (반드시 원문에서 찾아 포함)
| group_name | variable_key | input_type | 설명 |
|-----------|-------------|-----------|------|
| 당사자 정보 | shareholders | TEXTAREA | 주주 목록 (이름, 지분율, 줄바꿈 구분) |
| 당사자 정보 | shareholder_count | NUMBER | 주주 수 |
| 대상회사 | target_company | TEXT | 대상회사 명칭 |
| 대상회사 | target_address | TEXT | 대상회사 소재지 |
| 대상회사 | target_reg_number | TEXT | 대상회사 사업자등록번호 |
| 대상회사 | total_shares_issued | NUMBER | 발행주식 총수 |
| 대상회사 | par_value | CURRENCY | 1주 액면가 |
| 이사회 | board_seats_total | NUMBER | 이사회 총 의석수 |
| 이사회 | nominating_shareholder_seats | TEXTAREA | 주주별 이사 지명권 (줄바꿈 구분) |
| 이사회 | board_quorum | TEXT | 이사회 의사 정족수 |
| 이사회 | ceo_nomination | TEXT | 대표이사 선임 방법 |
| 의결/동의 | veto_item_descriptions | TEXTAREA | 주주 거부권(Veto) 대상 항목 목록 (줄바꿈 구분, visible: has_veto_rights == True) |
| 처분 제한 | lock_up_period_months | NUMBER | Lock-up 기간 (개월, 0=미포함) |
| 처분 제한 | lock_up_exception_conditions | TEXT | Lock-up 예외 조건 (예: IPO 후, 계열회사 이전) |
| 처분 제한 | rofr_notice_days | NUMBER | ROFR 통지 기간 (일, 0=미포함) |
| 처분 제한 | rofo_notice_days | NUMBER | ROFO(선매권) 통지 기간 (일, 0=미포함, visible: has_right_of_first_refusal == True) |
| 옵션 | put_trigger_event | TEXT | Put 옵션 행사 사유 |
| 옵션 | put_price_formula | TEXTAREA | Put 옵션 가격 산식 |
| 옵션 | put_exercise_period_months | NUMBER | Put 옵션 행사 가능 기간 (개월, visible: has_put_option == True) |
| 옵션 | put_valuation_method | SELECT | Put 행사 시 가격 산정 방법 (select_options: {"ebitda_multiple": "EBITDA 배수", "nav": "순자산가", "dcf": "현금흐름할인", "fixed": "고정가", "transaction": "거래가 기반"}) |
| 옵션 | call_trigger_event | TEXT | Call 옵션 행사 사유 |
| 옵션 | call_price_formula | TEXTAREA | Call 옵션 가격 산식 |
| 옵션 | call_exercise_period_months | NUMBER | Call 옵션 행사 가능 기간 (개월, visible: has_call_option == True) |
| Exit | ipo_timeline_months | NUMBER | IPO 추진 기한 (개월, 0=미정) |
| Exit | drag_threshold_percentage | PERCENTAGE | Drag-Along 행사 비율 |
| Exit | tag_threshold_percentage | PERCENTAGE | Tag-Along 행사 비율 |
| 재무 | waterfall_tiers | TEXTAREA | 수익분배 구조 (Waterfall) |
| 재무 | distribution_priority | TEXT | 분배 우선순위 |
| 비밀유지 | confidentiality_period_months | NUMBER | 비밀유지 기간 (개월) |
| 경업금지 | non_compete_period_months | NUMBER | 경업금지 기간 (개월, 0=미포함) |
| 경업금지 | non_compete_scope | TEXT | 경업금지 범위 |
| 정보권 | financial_report_frequency | SELECT | 재무정보 제공 주기 (select_options: {"monthly": "월간", "quarterly": "분기", "annually": "연간"}) |
| 정보권 | information_access_scope | TEXTAREA | 정보 접근 범위 (재무제표, 사업계획, 이사회 의사록 등) |
| 계약 기간 | agreement_term_months | NUMBER | 계약 존속 기간 (개월, 0=무기한) |
| 계약 기간 | agreement_termination_event | TEXT | 계약 종료 사유 (예: IPO 완료, 지분 전량 매각) |
| 일정 | signing_date | DATE | 계약 체결일 |
| 기타 | governing_law | SELECT | 준거법 |
| 기타 | dispute_resolution | SELECT | 분쟁해결 방법 |

원문에 해당 항목이 없으면 extracted_value를 null로, confidence를 낮게 설정하세요.

## 5. SHA 전용 동적 BOOLEAN 발견 규칙
| 조항 키워드 | variable_key | 설명 |
|------------|-------------|------|
| 이사 지명권 | has_board_nomination_right | 이사 지명권 존재 |
| 거부권/동의권/비토 | has_veto_rights | 주주 거부권/Veto 존재 |
| 상장/IPO | has_ipo_obligation | IPO 의무 조항 존재 |
| 풋옵션 | has_put_option | 풋옵션 존재 |
| 콜옵션 | has_call_option | 콜옵션 존재 |
| 우선매수권/ROFR | has_right_of_first_refusal | ROFR 존재 |
| 동반매도참여권/Tag | has_tag_along_right | Tag-Along 존재 |
| 동반매도청구권/Drag | has_drag_along_right | Drag-Along 존재 |
| Waterfall/분배 | has_waterfall_distribution | 수익분배 구조 존재 |
| 질권/담보 | has_pledge_agreement | 질권 설정 계약 존재 |
| 경업금지 | has_non_compete_obligation | 경업금지 의무 존재 |
| 우선매수/신주인수 | has_preemptive_rights | 신주인수권/우선매수권 존재 |
| Anti-dilution | has_anti_dilution | 희석방지 조항 존재 |
| 정보권/검사권 | has_information_rights | 재무정보 접근권/검사권 존재 |
| Key-Man/핵심인력 | has_key_man_clause | 핵심 경영진 이탈 트리거 존재 |
기타 발견 시 has_{영문명} 형식으로 자율 생성하세요.

## 6. SHA 유형별 추가 변수
POST_BUYOUT (경영권 인수 후):
| variable_key | input_type | 설명 |
|-------------|-----------|------|
| majority_shareholder_name | TEXT | 대주주(경영권 보유) 명칭 |
| minority_shareholder_name | TEXT | 소수주주(투자자) 명칭 |
| acquisition_reference | TEXT | 관련 SPA 참조 (체결일/계약명) |

JOINT_VENTURE (합작투자):
| variable_key | input_type | 설명 |
|-------------|-----------|------|
| jv_company_name | TEXT | 합작회사 명칭 |
| jv_purpose | TEXTAREA | 합작 사업 목적 |
| capital_contribution_ratio | TEXTAREA | 출자 비율 |
| deadlock_resolution | TEXT | 교착상태 해결 방법 |

MINORITY_INVESTMENT (소수지분 투자):
| variable_key | input_type | 설명 |
|-------------|-----------|------|
| investor_name | TEXT | 투자자 명칭 |
| investment_amount | CURRENCY | 투자 금액 |
| pre_money_valuation | CURRENCY | Pre-money 기업가치 |
| anti_dilution_type | SELECT | 희석방지 방식 (select_options: {"full_ratchet": "완전 래칫", "weighted_average_broad": "가중평균(광의)", "weighted_average_narrow": "가중평균(협의)"}) |

## 7. input_type 매핑 규칙
- 이름/주소/회사명/등록번호 → TEXT
- 긴 설명/비고/목록 → TEXTAREA
- 금액 (원, 억원, 백만원) → CURRENCY (반드시 원 단위로 정규화: 10억 → 1000000000)
- 비율 (%) → PERCENTAGE
- 날짜 → DATE
- 주식 수, 기간(개월/년), 의석수 등 → NUMBER
- 예/아니오 → BOOLEAN
- 선택지 → SELECT (select_options 필수)

## 출력 형식
JSON만 반환하세요. 설명이나 코멘트를 포함하지 마세요.
```json
{
  "detected_doc_type": "SHA",
  "sha_type": "POST_BUYOUT",
  "exit_strategy": "MNA_FOCUSED",
  "variables": [
    {
      "variable_key": "shareholders",
      "input_type": "TEXTAREA",
      "question_label": "주주 목록",
      "description": "주주 이름, 지분율을 줄바꿈으로 구분",
      "extracted_value": "A펀드 60%\\nB법인 40%",
      "default_value": null,
      "is_required": true,
      "select_options": null,
      "display_order": 1,
      "group_name": "당사자 정보",
      "visible_condition": null,
      "confidence": 0.95
    }
  ],
  "deal_structure": "POST_BUYOUT",
  "industry_type": "GENERAL",
  "discovered_booleans": [
    {
      "variable_key": "has_drag_along_right",
      "question_label": "Drag-Along 조항 포함 여부",
      "detected_in_clause": "제6조 (동반매도청구권)"
    }
  ]
}
```
주의: deal_structure 필드에는 sha_type과 동일한 값을 넣어주세요."""


# ── BTA Step 1: 변수 추출 프롬프트 ─────────────────────────────────────────────

_BTA_STEP1_SYSTEM_PROMPT = """당신은 한국 M&A 법률 문서 전문가이자 데이터 엔지니어입니다.
영업양수도계약서(BTA, Business Transfer Agreement) 원문을 분석하여 재사용 가능한 템플릿 변수를 추출합니다.

## 0. 계약서 유형 확정
이 계약서는 영업양수도계약서(BTA)입니다.
detected_doc_type은 반드시 "BTA"로 설정하세요.

## 1. BTA 양도 범위 분류 (bta_scope → deal_structure에도 동일 값)
원문의 양도 대상, 자산/부채 범위를 분석하여 분류합니다:
- COMPREHENSIVE_TRANSFER: 포괄 양수도 (사업부 전체, 자산+부채+계약+직원 일괄 이전)
- PARTIAL_TRANSFER: 부분 양수도 (특정 자산/사업라인만 선별 이전, cherry-picking)
- OTHER_SCOPE: 위에 해당하지 않는 경우

## 2. 퇴직금 처리 분류 (severance_pay_handling)
- ASSUMED_BY_BUYER: 매수인이 퇴직금 부채를 승계 (직원 근속 연수 인정)
- PAID_BY_SELLER: 매도인이 거래종결일 기준 퇴직금 정산 후 이전
- OTHER_METHOD: 기타 방식 (분담, 별도 합의 등)

## 3. 분석 순서
1. 전문(Preamble) → 양도인(매도인), 양수인(매수인) 정보
2. 정의 조항 → 양도대상 영업, 자산, 부채, 계약, 핵심 정의
3. 양도대상 특정 → 유형자산, 무형자산, 재고, 매출채권, 부채, 계약관계
4. 양수도대금 → 기본 매매대금, 보증금/예치금, 정산 방법
5. 가격조정 → 운전자본 조정, 기준일, 정산 절차
6. 임직원 승계 → 승계 대상, 퇴직금 처리, 근로조건
7. 선행조건(CP) → 규제 승인, 핵심 계약 동의, 임직원 동의
8. 거래종결(Closing) → 종결 절차, 인도 사항
9. 진술 및 보증 → 매도인/매수인 R&W
10. 확약/서약(Covenants) → 중간기간 운영, 제한 사항
11. 경업금지(Non-compete) → 기간, 범위, 비유인
12. 전환서비스(TSA) → 서비스 범위, 기간, 대가
13. 상표/브랜드 라이선스 → 라이선스 범위, 기간, 로열티
14. 손해배상(Indemnification) → de minimis, basket, cap, 존속기간
15. 해제/해지(Termination) → 종료 사유, 위약금
16. 일반 조항 → 비밀유지, 준거법, 분쟁해결
17. 전체 스캔 → 조건부 BOOLEAN 발견

## 4. 기본 변수 목록 (반드시 원문에서 찾아 포함)
| group_name | variable_key | input_type | 설명 |
|-----------|-------------|-----------|------|
| 당사자 정보 | seller_name | TEXT | 양도인(매도인) 명칭 |
| 당사자 정보 | seller_address | TEXT | 양도인 주소 |
| 당사자 정보 | seller_representative | TEXT | 양도인 대표자 |
| 당사자 정보 | seller_reg_number | TEXT | 양도인 사업자등록번호 |
| 당사자 정보 | buyer_name | TEXT | 양수인(매수인) 명칭 |
| 당사자 정보 | buyer_address | TEXT | 양수인 주소 |
| 당사자 정보 | buyer_representative | TEXT | 양수인 대표자 |
| 당사자 정보 | buyer_reg_number | TEXT | 양수인 사업자등록번호 |
| 양도대상 | target_business_description | TEXTAREA | 양도대상 영업의 범위/설명 |
| 양도대상 | transferred_assets_description | TEXTAREA | 양도 자산 목록/설명 |
| 양도대상 | assumed_liabilities_description | TEXTAREA | 승계 부채 목록/설명 |
| 양도대상 | transferred_contracts_description | TEXTAREA | 승계 계약 목록/설명 |
| 양도대상 | excluded_assets_description | TEXTAREA | 제외 자산 목록 (있는 경우) |
| 양도대상 | excluded_liabilities_description | TEXTAREA | 제외 부채 목록 (있는 경우) |
| 거래 조건 | base_purchase_price | CURRENCY | 기본 양수도대금 (원 단위) |
| 거래 조건 | deposit_amount | CURRENCY | 보증금/계약금 (원 단위) |
| 거래 조건 | balance_amount | CURRENCY | 잔금 (원 단위) |
| 가격조정 | price_adjustment_included | BOOLEAN | 가격조정 조항 포함 여부 |
| 가격조정 | price_adj_base_date | DATE | 가격조정 기준일 (visible: price_adjustment_included == True) |
| 가격조정 | price_adj_method | SELECT | 조정 방식 (select_options: {"nwc": "순운전자본", "nav": "순자산", "custom": "개별 합의"}) |
| 임직원 | employee_succession_included | BOOLEAN | 임직원 승계 포함 여부 |
| 임직원 | employee_count | NUMBER | 승계 대상 임직원 수 (visible: employee_succession_included == True) |
| 임직원 | severance_pay_base_date | DATE | 퇴직금 정산 기준일 (visible: employee_succession_included == True) |
| 경업금지 | non_compete_obligation_included | BOOLEAN | 경업금지 의무 포함 여부 |
| 경업금지 | non_compete_period_months | NUMBER | 경업금지 기간 (개월, visible: non_compete_obligation_included == True) |
| 경업금지 | non_compete_scope | TEXT | 경업금지 범위 (visible: non_compete_obligation_included == True) |
| 전환서비스 | tsa_required | BOOLEAN | 전환서비스(TSA) 포함 여부 |
| 전환서비스 | tsa_period_months | NUMBER | TSA 기간 (개월, visible: tsa_required == True) |
| 전환서비스 | tsa_scope | TEXTAREA | TSA 서비스 범위 (visible: tsa_required == True) |
| 브랜드 | brand_license_required | BOOLEAN | 상표/브랜드 라이선스 포함 여부 |
| 브랜드 | brand_license_period_months | NUMBER | 라이선스 기간 (개월, visible: brand_license_required == True) |
| 브랜드 | brand_license_scope | TEXT | 라이선스 범위 (visible: brand_license_required == True) |
| 부동산 | real_estate_lease_included | BOOLEAN | 부동산 임대차 승계 포함 여부 |
| 손해배상 | de_minimis_amount | CURRENCY | De Minimis 금액 |
| 손해배상 | basket_amount | CURRENCY | Basket(공제) 금액 |
| 손해배상 | indemnity_cap | CURRENCY | 손해배상 한도(Cap) |
| 손해배상 | survival_period_months | NUMBER | 진술보증 존속기간 (개월) |
| 일정 | signing_date | DATE | 계약 체결일 |
| 일정 | closing_date | DATE | 거래 종결일 |
| 일정 | long_stop_date | DATE | 최종 기한 (Long-stop date) |
| 선행조건 | has_condition_precedent | BOOLEAN | 선행조건(CP) 조항 포함 여부 |
| 선행조건 | cp_regulatory_approval | TEXT | 필요 규제/정부 승인 (visible: has_condition_precedent == True) |
| 선행조건 | cp_key_contract_consent | TEXT | 핵심 계약 상대방 동의 사항 (visible: has_condition_precedent == True) |
| 선행조건 | cp_employee_consent_required | BOOLEAN | 임직원 전적 동의 필요 여부 (visible: has_condition_precedent == True) |
| 경업금지 | has_non_solicitation | BOOLEAN | 비유인(Non-solicitation) 조항 별도 존재 여부 |
| 경업금지 | non_solicitation_period_months | NUMBER | 비유인 기간 (개월, visible: has_non_solicitation == True) |
| 경업금지 | non_solicitation_scope | TEXT | 비유인 범위 (visible: has_non_solicitation == True) |
| 브랜드 | brand_license_royalty_rate | PERCENTAGE | 상표 라이선스 로열티율 (visible: brand_license_required == True) |
| 손해배상 | indemnity_holdback_pct | PERCENTAGE | 이행보증금 공제율 (visible: de_minimis_amount > 0) |
| 손해배상 | has_special_indemnity | BOOLEAN | 환경/세무 특별 배상 별도 조항 존재 여부 |
| 해제/해지 | termination_fee_amount | CURRENCY | 위약금 액수 |
| 해제/해지 | termination_cause_summary | TEXT | 해지 사유 요약 |
| 비밀유지 | confidentiality_period_months | NUMBER | 비밀유지 기간 (개월) |
| 비밀유지 | confidentiality_scope | TEXT | 비밀유지 범위 |
| 기타 | governing_law | SELECT | 준거법 (select_options: {"korean": "대한민국법", "english": "영국법", "other": "기타"}) |
| 기타 | dispute_resolution | SELECT | 분쟁해결 (select_options: {"arbitration": "중재", "litigation": "소송", "mediation": "조정"}) |

원문에 해당 항목이 없으면 extracted_value를 null로, confidence를 낮게 설정하세요.

## 5. BTA 전용 동적 BOOLEAN 발견 규칙
| 조항 키워드 | variable_key | 설명 |
|------------|-------------|------|
| 환경 오염/토양 오염/환경 책임 | has_environmental_indemnity | 환경 면책/보상 조항 존재 |
| 인허가/사업 허가/면허 | has_permit_transfer | 영업 인허가 이전 조항 존재 |
| 지식재산/특허/상표 | has_ip_transfer | 지식재산권 이전 조항 존재 |
| 재고 실사/재고 조정 | has_inventory_adjustment | 재고 실사/조정 조항 존재 |
| 매출채권/미수금 | has_receivables_transfer | 매출채권 이전 조항 존재 |
| 소송/분쟁/우발채무 | has_contingent_liabilities | 우발채무 조항 존재 |
| 세무/조세/원천징수 | has_tax_indemnity | 세무 면책/보상 조항 존재 |
| 연금/퇴직연금/DB/DC | has_pension_transfer | 퇴직연금 이전 조항 존재 |
| 보험/보험 승계 | has_insurance_transfer | 보험 계약 승계 조항 존재 |
| 공급계약/구매계약 | has_supply_agreement_transfer | 공급/구매 계약 승계 조항 존재 |
| 리스/임대 | has_lease_transfer | 리스/임대 계약 승계 조항 존재 |
| IT 시스템/데이터 이전 | has_it_system_transfer | IT 시스템/데이터 이전 조항 존재 |
| 정부보조금/보조금 반환 | has_government_subsidy | 정부보조금 관련 조항 존재 |
| 하도급/하청 | has_subcontract_transfer | 하도급 계약 승계 조항 존재 |
기타 발견 시 has_{영문명} 형식으로 자율 생성하세요.

## 6. industry_type 분류 기준
- MANUFACTURING: 제조업 (공장, 생산, 재고, 환경 관련 조항)
- SOFTWARE: 소프트웨어/IT (지식재산권, 라이선스 관련 조항)
- FRANCHISE: 가맹점/프랜차이즈
- GENERAL: 특정 산업 특화 없음
- OTHER_INDUSTRY: 위에 해당하지 않는 산업

## 7. input_type 매핑 규칙
- 이름/주소/회사명/등록번호 → TEXT
- 긴 설명/비고/목록 → TEXTAREA
- 금액 (원, 억원, 백만원) → CURRENCY (반드시 원 단위로 정규화: 10억 → 1000000000)
- 비율 (%) → PERCENTAGE
- 날짜 → DATE
- 수량, 기간(개월/년) 등 → NUMBER
- 예/아니오 → BOOLEAN
- 선택지 → SELECT (select_options 필수)

## 8. BTA 양도 범위별 추가 변수
### COMPREHENSIVE_TRANSFER (포괄 양수도)
- comprehensive_scope_confirmation: BOOLEAN — 사업 전체 양수도 확인
### PARTIAL_TRANSFER (부분 양수도)
- carve_out_scope: TEXTAREA — 분리 대상 사업/부문 상세 설명
- retained_business_description: TEXTAREA — 양도인 잔존 사업 설명
해당 유형일 때만 위 변수를 추가로 식별하세요.

## 출력 형식
JSON만 반환하세요. 설명이나 코멘트를 포함하지 마세요.
```json
{
  "detected_doc_type": "BTA",
  "bta_scope": "COMPREHENSIVE_TRANSFER",
  "severance_pay_handling": "ASSUMED_BY_BUYER",
  "variables": [
    {
      "variable_key": "seller_name",
      "input_type": "TEXT",
      "question_label": "양도인 명칭",
      "description": "양도인의 법인명 또는 성명",
      "extracted_value": "주식회사 ABC",
      "default_value": null,
      "is_required": true,
      "select_options": null,
      "display_order": 1,
      "group_name": "당사자 정보",
      "visible_condition": null,
      "confidence": 0.95
    }
  ],
  "deal_structure": "COMPREHENSIVE_TRANSFER",
  "industry_type": "MANUFACTURING",
  "discovered_booleans": [
    {
      "variable_key": "has_environmental_indemnity",
      "question_label": "환경 면책/보상 조항 포함 여부",
      "detected_in_clause": "제13조 (손해배상)"
    }
  ]
}
```
주의: deal_structure 필드에는 bta_scope과 동일한 값을 넣어주세요."""


# ── SSA Step 1: 변수 추출 프롬프트 ─────────────────────────────────────────────

_SSA_STEP1_SYSTEM_PROMPT = """당신은 한국 M&A 법률 문서 전문가이자 데이터 엔지니어입니다.
신주인수계약서(SSA, Share Subscription Agreement) 원문을 분석하여 재사용 가능한 템플릿 변수를 추출합니다.

## 0. 계약서 유형 확정
이 계약서는 신주인수계약서(SSA)입니다.
detected_doc_type은 반드시 "SSA"로 설정하세요.

## 1. SSA 증권 종류 분류 (security_type → deal_structure에도 동일 값)
원문의 발행 증권, 투자 구조를 분석하여 분류합니다:
- COMMON_SHARE: 보통주 신주 인수 (단순 유상증자)
- RCPS: 상환전환우선주 (Redeemable Convertible Preferred Shares) — 전환권/상환권 부여
- CB: 전환사채 (Convertible Bond) — 사채 + 전환권
- BW: 신주인수권부사채 (Bond with Warrants) — 사채 + 신주인수권
- OTHER_SECURITY: 위에 해당하지 않는 증권 (무의결권주, 종류주 등)

## 2. SSA 거래 맥락 분류 (transaction_context)
- STANDALONE_INVESTMENT: 단독 신주투자 (유상증자만 진행, 기존 주식 거래 없음)
- PARALLEL_WITH_SPA: 구주매매 병행 (기존 주주의 지분 매각 + 신주 발행 동시 진행)
- PARALLEL_WITH_BTA: 영업양수도 병행 (사업 이전 + 신주 투자 동시 진행)
- OTHER_CONTEXT: 위에 해당하지 않는 거래 맥락

## 3. 분석 순서
1. 전문(Preamble) → 발행회사, 인수인(투자자), 이해관계인 정보
2. 정의 조항 → 핵심 정의 (신주, 인수대금, 전환가, 상환가 등)
3. 신주 발행 및 인수 → 증권 종류, 발행 주식 수, 발행가, 총 인수대금
4. 인수대금 납입 → 납입일, 납입 방법, 분할 납입 여부
5. 전환/상환 조건 → 전환가, 전환비율, 상환기간, 상환수익률 (RCPS/CB/BW)
6. 선행조건(CP) → 규제 승인, 이사회 결의, 주주총회 승인
7. 거래종결(Closing) → 종결 절차, 인도 사항
8. 진술 및 보증(R&W) → 발행회사/인수인 R&W
9. 확약(Covenants) → 자금 용도 제한, 경영 참여, 정보 제공
10. 의무보유등록(Lock-up) → 보유 기간, 예외 조건
11. 희석방지/우선매수권 → Anti-dilution, Pre-emptive Rights
12. 손해배상(Indemnification) → de minimis, basket, cap, 존속기간
13. 해제/해지(Termination) → 종료 사유, 위약금
14. 비밀유지(Confidentiality) → 범위, 기간
15. 일반조항 → 준거법, 분쟁해결, 통지
16. 전체 스캔 → 조건부 BOOLEAN 발견

## 4. 기본 변수 목록 (반드시 원문에서 찾아 포함)
| group_name | variable_key | input_type | 설명 |
|-----------|-------------|-----------|------|
| 당사자 정보 | issuer_name | TEXT | 발행회사 명칭 |
| 당사자 정보 | issuer_address | TEXT | 발행회사 주소 |
| 당사자 정보 | issuer_representative | TEXT | 발행회사 대표자 |
| 당사자 정보 | issuer_reg_number | TEXT | 발행회사 사업자등록번호 |
| 당사자 정보 | subscriber_name | TEXT | 인수인(투자자) 명칭 |
| 당사자 정보 | subscriber_address | TEXT | 인수인 주소 |
| 당사자 정보 | subscriber_representative | TEXT | 인수인 대표자 |
| 당사자 정보 | subscriber_reg_number | TEXT | 인수인 사업자등록번호 |
| 증권 정보 | security_class | TEXT | 증권 종류 (보통주/RCPS/CB/BW 등) |
| 증권 정보 | subscription_share_count | NUMBER | 인수 주식 수 |
| 증권 정보 | issue_price_per_share | CURRENCY | 1주당 발행가 (원 단위) |
| 증권 정보 | total_subscription_amount | CURRENCY | 총 인수대금 (원 단위) |
| 증권 정보 | par_value | CURRENCY | 1주 액면가 |
| 증권 정보 | post_investment_equity_ratio | PERCENTAGE | 투자 후 지분율 |
| 납입 | payment_date | DATE | 납입일 |
| 납입 | payment_method | TEXT | 납입 방법 (현금, 현물출자 등) |
| 납입 | installment_payment_included | BOOLEAN | 분할 납입 여부 |
| 전환/상환 | conversion_price | CURRENCY | 전환가 (visible: deal_structure in ["RCPS", "CB"]) |
| 전환/상환 | conversion_ratio | TEXT | 전환 비율 (visible: deal_structure in ["RCPS", "CB"]) |
| 전환/상환 | redemption_period_months | NUMBER | 상환 기간 (개월, visible: deal_structure in ["RCPS", "BW"]) |
| 전환/상환 | redemption_yield_rate | PERCENTAGE | 상환수익률 (visible: deal_structure in ["RCPS", "BW"]) |
| 전환/상환 | conversion_period_start | DATE | 전환 청구 가능 시작일 |
| 전환/상환 | conversion_period_end | DATE | 전환 청구 가능 종료일 |
| 자금 용도 | use_of_proceeds_description | TEXTAREA | 인수대금 사용 용도 |
| 의무보유 | lock_up_period_months | NUMBER | 의무보유 기간 (개월, 0=미포함) |
| 의무보유 | lock_up_exception_conditions | TEXT | 의무보유 예외 조건 |
| 손해배상 | de_minimis_amount | CURRENCY | De Minimis 금액 |
| 손해배상 | basket_amount | CURRENCY | Basket(공제) 금액 |
| 손해배상 | indemnity_cap | CURRENCY | 손해배상 한도(Cap) |
| 손해배상 | survival_period_months | NUMBER | 진술보증 존속기간 (개월) |
| 일정 | signing_date | DATE | 계약 체결일 |
| 일정 | closing_date | DATE | 거래 종결일 |
| 일정 | long_stop_date | DATE | 최종 기한 (Long-stop date) |
| 선행조건 | has_condition_precedent | BOOLEAN | 선행조건(CP) 조항 포함 여부 |
| 선행조건 | cp_board_approval | BOOLEAN | 이사회 승인 필요 여부 (visible: has_condition_precedent == True) |
| 선행조건 | cp_shareholder_approval | BOOLEAN | 주주총회 승인 필요 여부 (visible: has_condition_precedent == True) |
| 선행조건 | cp_regulatory_approval | TEXT | 필요 규제/정부 승인 (visible: has_condition_precedent == True) |
| 비밀유지 | confidentiality_period_months | NUMBER | 비밀유지 기간 (개월) |
| 기타 | governing_law | SELECT | 준거법 (select_options: {"korean": "대한민국법", "english": "영국법", "other": "기타"}) |
| 기타 | dispute_resolution | SELECT | 분쟁해결 (select_options: {"arbitration": "중재", "litigation": "소송", "mediation": "조정"}) |

원문에 해당 항목이 없으면 extracted_value를 null로, confidence를 낮게 설정하세요.

## 5. SSA 전용 동적 BOOLEAN 발견 규칙
| 조항 키워드 | variable_key | 설명 |
|------------|-------------|------|
| 병행 거래/구주매매/SPA | has_parallel_transaction | 병행 거래(SPA/BTA) 조항 존재 |
| 의무보유/Lock-up/보호예수 | has_lock_up | 의무보유 조항 존재 |
| 자금용도 제한/사용처 | has_use_of_proceeds_restriction | 자금 용도 제한 조항 존재 |
| 손해배상 한도/Cap | has_indemnification_cap | 손해배상 한도 조항 존재 |
| 희석방지/Anti-dilution | has_anti_dilution | 희석방지 조항 존재 |
| 우선분배/청산우선권 | has_liquidation_preference | 잔여재산 우선분배 조항 존재 |
| 동반매도청구/Drag-Along | has_drag_along | 동반매도청구권 존재 |
| 동반매도참여/Tag-Along | has_tag_along | 동반매도참여권 존재 |
| 이사 지명/이사회 참여 | has_board_nomination_right | 이사 지명권 존재 |
| 정보권/검사권 | has_information_rights | 재무정보 접근권/검사권 존재 |
| 우선매수권/신주인수권 | has_preemptive_rights | 신주인수권/우선매수권 존재 |
| 전환권 | has_conversion_right | 전환권 조항 존재 |
| 상환권 | has_redemption_right | 상환권 조항 존재 |
| 풋옵션 | has_put_option | 풋옵션 존재 |
| 콜옵션 | has_call_option | 콜옵션 존재 |
| 배당 우선 | has_dividend_preference | 배당 우선권 존재 |
| 마일스톤 지급 | has_milestone_payment | 마일스톤 기반 추가 납입 조항 존재 |
| 에스크로 | has_escrow | 에스크로 조항 존재 |
기타 발견 시 has_{영문명} 형식으로 자율 생성하세요.

## 6. industry_type 분류 기준
- MANUFACTURING: 제조업 (공장, 생산, 재고, 환경 관련 조항)
- SOFTWARE: 소프트웨어/IT (지식재산권, 라이선스 관련 조항)
- FRANCHISE: 가맹점/프랜차이즈
- GENERAL: 특정 산업 특화 없음
- OTHER_INDUSTRY: 위에 해당하지 않는 산업

## 7. input_type 매핑 규칙
- 이름/주소/회사명/등록번호 → TEXT
- 긴 설명/비고/목록 → TEXTAREA
- 금액 (원, 억원, 백만원) → CURRENCY (반드시 원 단위로 정규화: 10억 → 1000000000)
- 비율 (%) → PERCENTAGE
- 날짜 → DATE
- 수량, 기간(개월/년) 등 → NUMBER
- 예/아니오 → BOOLEAN
- 선택지 → SELECT (select_options 필수)

## 8. 증권 종류별 추가 변수
### RCPS (상환전환우선주)
- preferred_dividend_rate: PERCENTAGE — 우선배당률
- cumulative_dividend: BOOLEAN — 누적적/비누적적
- participating_preferred: BOOLEAN — 참가적/비참가적
### CB (전환사채)
- coupon_rate: PERCENTAGE — 표면이율
- maturity_date: DATE — 만기일
- bond_amount: CURRENCY — 사채 발행 총액
### BW (신주인수권부사채)
- warrant_exercise_price: CURRENCY — 신주인수권 행사가격
- warrant_exercise_ratio: PERCENTAGE — 행사 비율
- warrant_detachable: BOOLEAN — 분리형/비분리형
해당 유형일 때만 위 변수를 추가로 식별하세요.

## 출력 형식
JSON만 반환하세요. 설명이나 코멘트를 포함하지 마세요.
```json
{
  "detected_doc_type": "SSA",
  "security_type": "RCPS",
  "transaction_context": "STANDALONE_INVESTMENT",
  "variables": [
    {
      "variable_key": "issuer_name",
      "input_type": "TEXT",
      "question_label": "발행회사 명칭",
      "description": "발행회사의 법인명",
      "extracted_value": "주식회사 ABC",
      "default_value": null,
      "is_required": true,
      "select_options": null,
      "display_order": 1,
      "group_name": "당사자 정보",
      "visible_condition": null,
      "confidence": 0.95
    }
  ],
  "deal_structure": "RCPS",
  "industry_type": "SOFTWARE",
  "discovered_booleans": [
    {
      "variable_key": "has_anti_dilution",
      "question_label": "희석방지 조항 포함 여부",
      "detected_in_clause": "제10조 (희석방지)"
    }
  ]
}
```
주의: deal_structure 필드에는 security_type과 동일한 값을 넣어주세요."""


# ── MOU Step 1: 변수 추출 프롬프트 ─────────────────────────────────────────────

_MOU_STEP1_SYSTEM_PROMPT = """당신은 한국 M&A 법률 문서 전문가이자 데이터 엔지니어입니다.
양해각서(MOU, Memorandum of Understanding) 원문을 분석하여 재사용 가능한 템플릿 변수를 추출합니다.

## 0. 계약서 유형 확정
이 계약서는 양해각서(MOU)입니다.
detected_doc_type은 반드시 "MOU"로 설정하세요.

## 1. MOU 거래 유형 분류 (mou_transaction_type → deal_structure에도 동일 값)
원문의 거래 구조, 향후 본계약 유형을 분석하여 분류합니다:
- SHARE_PURCHASE: 주식양수도 예정 (MOU 후 SPA로 이어질 구주매매)
- BUSINESS_TRANSFER: 영업양수도 예정 (MOU 후 BTA로 이어질 사업 양도)
- NEW_SHARE_ISSUE: 신주인수 예정 (MOU 후 SSA/투자계약으로 이어질 유상증자)
- COMBINED: 복합 구조 (구주매매 + 신주발행, 영업양수도 + 투자 등)
- OTHER_MOU_TYPE: 위에 해당하지 않는 경우

## 2. 보증금 처리 분류 (deposit_handling)
- REFUNDABLE: 환불 가능 보증금 (거래 불성립 시 전액 반환)
- NON_REFUNDABLE: 환불 불가/위약금 전환 (특정 시점 후 반환불가, 위약벌로 전환)
- NO_DEPOSIT: 보증금 없음

## 3. 분석 순서
1. 전문(Preamble) → 매도인(양도인), 매수인(투자자) 정보
2. 정의 조항 → 대상회사, 대상 주식/영업, 핵심 정의
3. 거래 구조 개요 → 양도 방식(주식/영업/신주), 지분율, 거래 개요
4. 가격 조건 → 잠정 매매대금, EBITDA 배수, 순운전자본 조정 등 산식
5. 독점협상(Exclusivity) → 배타적 협상권 기간, 범위, 위반 시 효과
6. 보증금/이행보증(Deposit) → 금액, 납입 방법, 반환/몰취 조건, 질권
7. 실사(Due Diligence) → 실사 기간, 범위, 자료 접근, 비용 부담
8. 진행 일정(Timeline) → MOU 체결일, 실사 완료일, 본계약 목표일, MOU 유효기한
9. 텀시트/별지(Term Sheet) → 우선주 전환, 풋/콜, Drag/Tag 등 본계약 핵심 조건
10. 종료/해제(Termination) → 해지 사유, 유효기한, 위약금
11. 비밀유지(Confidentiality) → 범위, 기간, 위약벌
12. 법적 구속력(Binding) → 구속력 있는 조항 범위 (비밀유지, 독점협상 등)
13. 일반조항 → 준거법, 분쟁해결, 통지, 완전합의
14. 전체 스캔 → 조건부 BOOLEAN 발견

## 4. 기본 변수 목록 (반드시 원문에서 찾아 포함)
| group_name | variable_key | input_type | 설명 |
|-----------|-------------|-----------|------|
| 당사자 정보 | seller_name | TEXT | 매도인/양도인 명칭 |
| 당사자 정보 | seller_address | TEXT | 매도인 주소 |
| 당사자 정보 | seller_representative | TEXT | 매도인 대표자 |
| 당사자 정보 | buyer_name | TEXT | 매수인/투자자 명칭 |
| 당사자 정보 | buyer_address | TEXT | 매수인 주소 |
| 당사자 정보 | buyer_representative | TEXT | 매수인 대표자 |
| 거래 대상 | target_company | TEXT | 대상회사 명칭 |
| 거래 대상 | target_business_description | TEXTAREA | 거래 대상 사업/주식 설명 |
| 거래 조건 | indicative_price | CURRENCY | 잠정 매매대금/투자금액 (원 단위) |
| 거래 조건 | price_formula_included | BOOLEAN | 가격산정 공식 포함 여부 |
| 거래 조건 | price_formula_description | TEXTAREA | 가격산정 기준/공식 설명 (visible: price_formula_included == True) |
| 거래 조건 | valuation_multiple | NUMBER | EBITDA 배수 등 (visible: price_formula_included == True) |
| 거래 조건 | equity_ratio | PERCENTAGE | 양도/투자 지분율 |
| 독점협상 | exclusivity_period_included | BOOLEAN | 독점협상기간 포함 여부 |
| 독점협상 | exclusivity_period_days | NUMBER | 독점협상 기간 (일, visible: exclusivity_period_included == True) |
| 독점협상 | exclusivity_scope | TEXT | 독점협상 범위/예외 (visible: exclusivity_period_included == True) |
| 보증금 | deposit_included | BOOLEAN | 보증금 포함 여부 |
| 보증금 | deposit_amount | CURRENCY | 보증금 금액 (visible: deposit_included == True) |
| 보증금 | deposit_due_date | DATE | 보증금 납입 기한 (visible: deposit_included == True) |
| 보증금 | deposit_return_conditions | TEXTAREA | 보증금 반환 조건 (visible: deposit_included == True) |
| 실사 | dd_period_days | NUMBER | 실사 기간 (일) |
| 실사 | dd_scope | TEXTAREA | 실사 범위 |
| 실사 | dd_access_scope | TEXTAREA | 실사 자료 접근 범위 |
| 일정 | signing_date | DATE | MOU 체결일 |
| 일정 | target_closing_date | DATE | 목표 본계약 체결일 |
| 일정 | mou_expiry_date | DATE | MOU 유효기한 |
| 텀시트 | term_sheet_included | BOOLEAN | 주요 조건 Term Sheet 포함 여부 |
| 위약금 | penalty_clause_included | BOOLEAN | 위약금 조항 포함 여부 |
| 위약금 | penalty_amount | CURRENCY | 위약금 금액 (visible: penalty_clause_included == True) |
| 위약금 | penalty_trigger_conditions | TEXTAREA | 위약금 발동 조건 (visible: penalty_clause_included == True) |
| 비밀유지 | confidentiality_period_months | NUMBER | 비밀유지 기간 (개월) |
| 비밀유지 | confidentiality_penalty_amount | CURRENCY | 비밀유지 위반 위약벌 금액 |
| 기타 | governing_law | SELECT | 준거법 (select_options: {"korean": "대한민국법", "english": "영국법", "other": "기타"}) |
| 기타 | dispute_resolution | SELECT | 분쟁해결 (select_options: {"arbitration": "중재", "litigation": "소송", "mediation": "조정"}) |

원문에 해당 항목이 없으면 extracted_value를 null로, confidence를 낮게 설정하세요.

## 5. MOU 전용 동적 BOOLEAN 발견 규칙
| 조항 키워드 | variable_key | 설명 |
|------------|-------------|------|
| 독점/배타적 협상/Exclusivity | has_exclusivity | 독점협상권 조항 존재 |
| 보증금 질권/담보/Deposit Pledge | has_deposit_pledge | 보증금 질권 설정 조항 존재 |
| 위약금/Break Fee/해약금 | has_break_fee | 거래 중단 시 위약금 조항 존재 |
| 실사비용 보전/DD Cost | has_dd_cost_reimbursement | 실사비용 보전 조항 존재 |
| 가격조정/운전자본/NWC | has_price_adjustment_clause | 가격조정 산식 별도 조항 존재 |
| 텀시트/별지/Term Sheet | has_term_sheet_annex | 별지 Term Sheet 존재 |
| 규제 승인/공정위/FTC | has_regulatory_approval | 규제 승인 조건 존재 |
| 핵심인력/Key-Man | has_key_man_clause | 핵심 경영진 유지 조건 존재 |
| 경업금지/Non-Compete | has_non_compete | 경업금지 조항 존재 |
| 어닝아웃/Earnout 언급 | has_earnout_indication | 어닝아웃 관련 언급 존재 |
| 에스크로/Escrow 언급 | has_escrow_indication | 에스크로 관련 언급 존재 |
| 선행조건/CP | has_condition_precedent | 선행조건 조항 존재 |
| 법적 구속력 명시 | has_binding_clause | 법적 구속력 범위 명시 조항 존재 |
기타 발견 시 has_{영문명} 형식으로 자율 생성하세요.

## 6. industry_type 분류 기준
- MANUFACTURING: 제조업 (공장, 생산, 재고, 환경 관련 조항)
- SOFTWARE: 소프트웨어/IT (지식재산권, 라이선스 관련 조항)
- FRANCHISE: 가맹점/프랜차이즈
- GENERAL: 특정 산업 특화 없음
- OTHER_INDUSTRY: 위에 해당하지 않는 산업

## 7. input_type 매핑 규칙
- 이름/주소/회사명/등록번호 → TEXT
- 긴 설명/비고/목록 → TEXTAREA
- 금액 (원, 억원, 백만원) → CURRENCY (반드시 원 단위로 정규화: 10억 → 1000000000)
- 비율 (%) → PERCENTAGE
- 날짜 → DATE
- 수량, 기간(개월/년/일) 등 → NUMBER
- 예/아니오 → BOOLEAN
- 선택지 → SELECT (select_options 필수)

## 8. 거래 유형별 추가 변수
### SHARE_PURCHASE (주식양수도 예정)
- share_count: NUMBER — 양도 예정 주식 수
- share_ratio: PERCENTAGE — 양도 지분율
### BUSINESS_TRANSFER (영업양수도 예정)
- transferred_business_scope: TEXTAREA — 양도 대상 영업 범위
- employee_succession_mentioned: BOOLEAN — 임직원 승계 언급 여부
### NEW_SHARE_ISSUE (신주인수 예정)
- new_share_count: NUMBER — 발행 예정 주식 수
- security_class: TEXT — 증권 종류 (보통주/RCPS/CB 등)
- pre_money_valuation: CURRENCY — Pre-money 기업가치
해당 유형일 때만 위 변수를 추가로 식별하세요.

## 출력 형식
JSON만 반환하세요. 설명이나 코멘트를 포함하지 마세요.
```json
{
  "detected_doc_type": "MOU",
  "mou_transaction_type": "SHARE_PURCHASE",
  "deposit_handling": "NON_REFUNDABLE",
  "variables": [
    {
      "variable_key": "seller_name",
      "input_type": "TEXT",
      "question_label": "매도인 명칭",
      "description": "매도인의 법인명 또는 성명",
      "extracted_value": "주식회사 ABC",
      "default_value": null,
      "is_required": true,
      "select_options": null,
      "display_order": 1,
      "group_name": "당사자 정보",
      "visible_condition": null,
      "confidence": 0.95
    }
  ],
  "deal_structure": "SHARE_PURCHASE",
  "industry_type": "GENERAL",
  "discovered_booleans": [
    {
      "variable_key": "has_exclusivity",
      "question_label": "독점협상권 조항 포함 여부",
      "detected_in_clause": "제4조 (독점적 협상)"
    }
  ]
}
```
주의: deal_structure 필드에는 mou_transaction_type과 동일한 값을 넣어주세요."""


async def analyze_step1_variables(
    spa_text: str,
    language_hint: str | None = None,
    doc_type_hint: str | None = None,
    *,
    owner_user_id: str = "",
) -> Step1Result:
    """Step 1: 계약서 원문에서 변수를 추출한다.

    Returns:
        Step1Result TypedDict — 이름 기반 키 접근으로 tuple 인덱스 오류 방지.
    """
    session_id = str(uuid.uuid4())

    # 세션 수 상한 체크 (B-3)
    if len(_sessions) >= _MAX_SESSIONS:
        _cleanup_expired_sessions()
        if len(_sessions) >= _MAX_SESSIONS:
            raise RuntimeError("분석 세션 수가 한도에 도달했습니다. 잠시 후 다시 시도하세요.")

    # 세션 생성 (소유자 기록 — C1 세션 소유권 검증용)
    session = AnalysisSession(
        session_id=session_id,
        spa_text=spa_text,
        owner_user_id=owner_user_id,
    )
    _sessions[session_id] = session

    # 프롬프트 선택: doc_type_hint에 따라 전용 프롬프트 분기
    if doc_type_hint == "SHA":
        system_prompt = _SHA_STEP1_SYSTEM_PROMPT
    elif doc_type_hint == "BTA":
        system_prompt = _BTA_STEP1_SYSTEM_PROMPT
    elif doc_type_hint == "SSA":
        system_prompt = _SSA_STEP1_SYSTEM_PROMPT
    elif doc_type_hint == "MOU":
        system_prompt = _MOU_STEP1_SYSTEM_PROMPT
    else:
        system_prompt = _STEP1_SYSTEM_PROMPT

    # 사용자 프롬프트
    lang_hint = f"\n언어: {language_hint}" if language_hint else ""
    doc_hint = f"\n문서 유형 힌트: {doc_type_hint}" if doc_type_hint else ""
    user_prompt = f"""--- 계약서 원문 시작 ---
{spa_text}
--- 계약서 원문 끝 ---{lang_hint}{doc_hint}

위 계약서 원문을 분석하여 계약 유형을 감지하고, 재사용 가능한 템플릿 변수를 추출하세요."""

    try:
        data, cost, model = await _call_llm_json(system_prompt, user_prompt)
    except (RuntimeError, ValueError):
        _sessions.pop(session_id, None)
        raise

    # 비용 기록
    if cost:
        session.cost_usd += cost
    session.model_used = model

    # 응답 파싱 — ValidationError/TypeError/KeyError 시 세션 정리 보장
    try:
        variables = [ExtractedVariable(**v) for v in data.get("variables", [])]
        deal_structure = data.get("deal_structure", "OTHER_STRUCTURE")
        industry_type = data.get("industry_type", "GENERAL")
        detected_doc_type = data.get("detected_doc_type", "SPA")
        discovered = [DiscoveredBoolean(**b) for b in data.get("discovered_booleans", [])]
    except (ValueError, TypeError, KeyError):
        _sessions.pop(session_id, None)
        raise
    sha_type: str | None = data.get("sha_type")
    exit_strategy: str | None = data.get("exit_strategy")
    bta_scope: str | None = data.get("bta_scope")
    severance_pay_handling: str | None = data.get("severance_pay_handling")
    security_type: str | None = data.get("security_type")
    transaction_context: str | None = data.get("transaction_context")
    mou_transaction_type: str | None = data.get("mou_transaction_type")
    deposit_handling: str | None = data.get("deposit_handling")

    # 세션에 detected_doc_type 저장 (Step 2 프롬프트 분기용)
    session.detected_doc_type = detected_doc_type

    # variable_key 중복 제거 (첫 번째 등장만 유지)
    seen_keys: set[str] = set()
    unique_variables: list[ExtractedVariable] = []
    for v in variables:
        if v.variable_key not in seen_keys:
            seen_keys.add(v.variable_key)
            unique_variables.append(v)
        else:
            logger.warning("Step 1: 중복 variable_key 제거: %s", v.variable_key)
    variables = unique_variables

    logger.info(
        "Step 1 완료: session=%s, doc_type=%s, variables=%d, deal=%s, industry=%s, booleans=%d, cost=$%.4f",
        session_id,
        detected_doc_type,
        len(variables),
        deal_structure,
        industry_type,
        len(discovered),
        cost or 0.0,
    )

    return Step1Result(
        session_id=session_id,
        variables=variables,
        deal_structure=deal_structure,
        industry_type=industry_type,
        detected_doc_type=detected_doc_type,
        discovered_booleans=discovered,
        sha_type=sha_type,
        exit_strategy=exit_strategy,
        bta_scope=bta_scope,
        severance_pay_handling=severance_pay_handling,
        security_type=security_type,
        transaction_context=transaction_context,
        mou_transaction_type=mou_transaction_type,
        deposit_handling=deposit_handling,
        cost=cost,
        model=model,
    )


# ── Step 2: 조항 분해 ─────────────────────────────────────────────────────────

_STEP2_SYSTEM_PROMPT = """당신은 한국 M&A 법률 문서 전문가이자 Jinja2 템플릿 엔지니어입니다.
SPA 원문을 조항별로 분해하고, 변수 값을 Jinja2 템플릿 문법으로 변환합니다.

## 표준 SPA 조항 구조 (12~15조)
- 전문 (Preamble) — 당사자 식별, 배경
- 제1조 용어의 정의 (Definitions)
- 제2조 대상주식의 매매 / 매매대금 (Sale & Purchase Price)
- 제3조 거래의 종결 (Closing)
- 제4조 매도인의 진술 및 보장 (Seller's R&W) — 하위조 10~15개
- 제5조 매수인의 진술 및 보장 (Buyer's R&W)
- 제6조 거래종결의 선행조건 (Conditions Precedent)
- 제7조 확약/서약 (Covenants)
- 제8조 손해배상/면책 (Indemnification)
- 제9조 비밀유지 (Confidentiality)
- 제10조 해제/종료 (Termination)
- 제11조 일반조항 (General Provisions)
- 제12조 준거법 및 분쟁해결 (Governing Law)

원문의 조/항/호 구조를 최대한 보존하세요.

## Jinja2 변환 규칙
- confirmed_variables 목록에 있는 변수만 사용하세요.
- 리터럴 값 → {{ variable_key }}
- 금액 → {{ total_purchase_price | currency_format }}  (출력: "금 1,000,000,000원")
  - ⚠ currency_format은 이미 "금 {숫자}원" 형태로 출력합니다. "금"이나 "원"을 별도로 추가하지 마세요.
  - 숫자만 필요한 경우: {{ total_purchase_price | number_format }}  (출력: "1,000,000,000")
- 날짜 → {{ closing_date | date_format }}  (출력: "2024년 03월 15일")
- 숫자 → {{ share_count | number_format }}  (출력: "1,000,000")
- 조건부 블록 → {% if escrow_included %}...{% endif %}

## 한글 금액 표기 가이드
- currency_format 필터는 "금 {천단위 구분 숫자}원" 형태를 이미 포함합니다:
  - 입력: 10000000000 → 출력: "금 10,000,000,000원"
- 원문의 "금 일백억원정 (₩10,000,000,000)" 전체를 {{ variable_key | currency_format }}으로 치환하세요.
- ⚠ 이중 래핑 금지: "금 {{ var | currency_format }}원" (X) → {{ var | currency_format }} (O)
- 원문의 "OO억원" → 원 단위 숫자로 추출하여 변수에 저장, 표시는 currency_format 필터 사용
- 한글 표기와 아라비아 숫자가 병기된 경우: {{ variable_key | currency_format }} 하나로 통합

## condition_expression 규칙
- Python 문법 사용
- 지원 연산자: ==, !=, <, >, <=, >=, in, not in, and, or, not
- 예: has_escrow == True
- 예: deal_structure == "CARVE_OUT"
- 예: has_escrow == True and deal_structure == "CARVE_OUT"
- 항상 포함되는 조항은 condition_expression을 null로 설정

## is_boilerplate 분류
- True: 용어 정의(구조), 비밀유지, 일반조항, 준거법/분쟁해결
- False: 매매, 종결, 진술보장, 선행조건, 확약, 손해배상, 해제

## 진술 및 보장 처리
- 매도인/매수인 R&W 하위조(설립존속, 소유권, 재무제표 등)는 하나의 clause 내 HTML로 유지
- industry_type별 특화 하위조는 Jinja2 조건문으로 제어

## content HTML 형식
조항 내용을 HTML로 구조화하세요:
- <p> 태그로 각 조항/항 감싸기
- <ol>, <li> 태그로 호/목 나열
- 들여쓰기와 구조 보존

## 거래 구조별 조항 분해 규칙
- CARVE_OUT: 분할 관련 조항(분할 사항, 존속회사 확약)을 독립 clause로 분리
  - condition_expression: deal_structure == "CARVE_OUT"
  - 분할 전/후 진술보장은 별도 clause (condition: deal_structure == "CARVE_OUT" and has_split_warranties == True)
- WITH_NEW_SHARES: 유상증자 관련 조항을 독립 clause로 분리
  - condition_expression: deal_structure == "WITH_NEW_SHARES"
- 해당 구조가 아닌 경우 해당 조항은 생략 (condition_expression으로 제어)

## R&W 산업별 조건부 렌더링
진술 및 보장(R&W) 하위조 중 산업 특화 항목을 Jinja2 조건문으로 제어:
- 환경: {% if industry_type == "MANUFACTURING" %}환경 관련 진술보장 내용{% endif %}
- 지식재산권: {% if industry_type == "SOFTWARE" %}IP 관련 진술보장 내용{% endif %}
- 가맹계약: {% if industry_type == "FRANCHISE" %}가맹 관련 진술보장 내용{% endif %}
- 공통 하위조(설립존속, 소유권, 재무제표, 소송, 조세)는 조건 없이 항상 포함

## 비밀유지 조항 참고
- boilerplate로 분류하되, 존속기간이 명시되면 confidentiality_period_months 변수 사용
- 한국 SPA 비밀유지 표준: 비밀 범위, 예외 사항, 존속기간, 위반 시 손해배상

## 별지/공개목록 처리
- 본문에서 "별지 제X호" 또는 "공개목록" 참조 시: 참조 텍스트만 유지, 별지 본문은 clause에 포함하지 않음
- 별지가 있는 조항: has_disclosure_schedule == True 조건으로 참조 문구 제어

## 금액 표기 실전 변환 예제
- "금 일백억원정 (₩10,000,000,000)" → {{ total_purchase_price | currency_format }}
- "금 이십억원" → {{ escrow_amount | currency_format }}
- "10,000,000,000원" → {{ total_purchase_price | currency_format }}
- 숫자만 필요한 맥락: "1,000,000주" → {{ share_count | number_format }}주

## 복합 condition_expression 예제
- deal_structure == "CARVE_OUT" and has_split_warranties == True
- earnout_included == True and earnout_period_months > 0
- industry_type == "MANUFACTURING" and has_environmental_rw == True
- has_escrow == True or earnout_included == True
- non_compete_years > 0
- has_price_adjustment == True and price_adj_method == "nwc"

## 출력 형식
JSON만 반환하세요. 설명이나 코멘트를 포함하지 마세요.
```json
{
  "clauses": [
    {
      "clause_order": 0,
      "title": "전문",
      "content": "<p>{{ seller_name }}(이하 &quot;매도인&quot;)과 ...</p>",
      "original_content": "<p>주식회사 ABC(이하 &quot;매도인&quot;)과 ...</p>",
      "is_boilerplate": false,
      "condition_expression": null,
      "confidence": 0.9
    }
  ]
}
```"""

# ── SHA Step 2: 조항 분해 ────────────────────────────────────────────────────

_SHA_STEP2_SYSTEM_PROMPT = """당신은 한국 M&A 법률 문서 전문가이자 Jinja2 템플릿 엔지니어입니다.
SHA(주주간계약서) 원문을 조항별로 분해하고, 변수 값을 Jinja2 템플릿 문법으로 변환합니다.

## 표준 SHA 조항 구조 (13개 표준 조)
1. 전문 (Preamble) — 배경, 당사자 식별, 지분 현황
2. 정의 (Definitions) — 핵심 용어 정의
3. 이사회/경영진 구성 (Board Composition & Governance) — 의석수, 지명권, 정족수
4. 주주 의결 사항 / 동의권 (Voting & Consent Rights / Veto) — 중요사항 동의, 거부권
5. 주식 처분 제한 (Transfer Restrictions) — ROFR, Lock-up, 사전동의
6. Tag-Along / Drag-Along — 동반매도참여/청구, 비율, 절차
7. 옵션 (Put/Call Options) — 행사 조건, 가격 산식, 기간
8. 우선매수권 / 신주인수권 (Pre-emptive Rights) — 희석방지, 신주배정
9. 배당 및 수익분배 (Dividends & Waterfall) — 배당 정책, 우선배당, 분배 순서
10. 퇴출 전략 (Exit Strategy) — IPO 의무/일정, 매각 절차
11. 비밀유지 (Confidentiality) — 범위, 기간, 예외
12. 경업금지 (Non-Compete) — 범위, 기간, 위반 시 제재
13. 준거법 및 분쟁해결 (Governing Law & Dispute Resolution)

원문의 조/항/호 구조를 최대한 보존하세요.

## Jinja2 변환 규칙
- confirmed_variables 목록에 있는 변수만 사용하세요.
- 리터럴 값 → {{ variable_key }}
- 금액 → {{ investment_amount | currency_format }}
- 날짜 → {{ signing_date | date_format }}
- 숫자 → {{ board_seats_total | number_format }}
- 비율 → {{ drag_threshold_percentage }}%
- 조건부 블록 → {% if has_put_option %}...{% endif %}

## 한글 금액 표기 가이드
- currency_format 필터는 "금 {천단위 구분 숫자}원" 형태를 이미 포함합니다:
  - 입력: 2000000000 → 출력: "금 2,000,000,000원"
- 원문의 "금 이십억원정 (₩2,000,000,000)" 전체를 {{ variable_key | currency_format }}으로 치환하세요.
- ⚠ 이중 래핑 금지: "금 {{ var | currency_format }}원" (X) → {{ var | currency_format }} (O)
- 원문의 "OO억원" → 원 단위 숫자로 추출하여 변수에 저장, 표시는 currency_format 필터 사용
- 한글 표기와 아라비아 숫자가 병기된 경우: {{ variable_key | currency_format }} 하나로 통합
- 숫자만 필요한 경우: {{ investment_amount | number_format }} (출력: "2,000,000,000")

## SHA 특화 조건부 렌더링
- 이사 지명권: {% if has_board_nomination_right %}...{% endif %}
- 거부권/Veto: {% if has_veto_rights %}...{% endif %}
- IPO 의무: {% if has_ipo_obligation %}...{% endif %}
- 풋옵션: {% if has_put_option %}...{% endif %}
- 콜옵션: {% if has_call_option %}...{% endif %}
- ROFR: {% if has_right_of_first_refusal %}...{% endif %}
- Tag-Along: {% if has_tag_along_right %}...{% endif %}
- Drag-Along: {% if has_drag_along_right %}...{% endif %}
- Waterfall: {% if has_waterfall_distribution %}...{% endif %}
- 경업금지: {% if has_non_compete_obligation %}...{% endif %}
- 질권: {% if has_pledge_agreement %}...{% endif %}
- 신주인수권: {% if has_preemptive_rights %}...{% endif %}
- 희석방지: {% if has_anti_dilution %}...{% endif %}
- 정보권: {% if has_information_rights %}...{% endif %}
- Key-Man: {% if has_key_man_clause %}...{% endif %}

## SHA 유형별 조건부 조항 및 변수 사용
- POST_BUYOUT: deal_structure == "POST_BUYOUT" — 경영권 이전 관련
  - 유형별 변수 활용: {{ majority_shareholder_name }}(대주주), {{ minority_shareholder_name }}(소수주주), {{ acquisition_reference }}(관련 SPA)
  - 예: "<p>{{ majority_shareholder_name }}(이하 "대주주")는 {{ acquisition_reference }}에 따른 경영권 인수를 완료하고...</p>"
- JOINT_VENTURE: deal_structure == "JOINT_VENTURE" — 합작 사업 관련
  - 유형별 변수 활용: {{ jv_company_name }}(합작회사), {{ jv_purpose }}(사업 목적), {{ capital_contribution_ratio }}(출자 비율), {{ deadlock_resolution }}(교착상태 해결)
  - 예: "<p>{{ jv_company_name }}의 사업 목적은 {{ jv_purpose }}으로 한다.</p>"
- MINORITY_INVESTMENT: deal_structure == "MINORITY_INVESTMENT" — 투자자 보호
  - 유형별 변수 활용: {{ investor_name }}(투자자), {{ investment_amount | currency_format }}(투자금액), {{ pre_money_valuation | currency_format }}(Pre-money), {{ anti_dilution_type }}(희석방지 방식)
  - 예: "<p>{{ investor_name }}(이하 "투자자")는 {{ investment_amount | currency_format }}을 출자한다.</p>"

## 별지/부속서(Schedule) 처리
- 본문에서 "별지", "부속서", "별표" 참조 시: 참조 텍스트만 유지, 별지 본문은 clause에 포함하지 않음
- 흔한 SHA 별지: Veto 항목 목록, Waterfall 계산 상세, 주주 지분 현황, 이사 지명 기준
- 별지가 있는 조항: 관련 BOOLEAN 조건으로 참조 문구 제어
  - 예: {% if has_veto_rights %}<p>거부권 대상 사항은 별지 제1호에 따른다.</p>{% endif %}

## condition_expression 규칙
- Python 문법 사용
- 지원 연산자: ==, !=, <, >, <=, >=, in, not in, and, or, not
- 예: has_put_option == True
- 예: deal_structure == "JOINT_VENTURE"
- 예: has_drag_along_right == True and drag_threshold_percentage > 0
- 항상 포함되는 조항은 condition_expression을 null로 설정

## is_boilerplate 분류 (SHA 기준)
- True: 정의(구조), 비밀유지, 준거법/분쟁해결
- False: 이사회, 동의권/Veto, 처분제한, Tag/Drag, 옵션, 신주인수권, 배당/Waterfall, Exit, 경업금지

## content HTML 형식
조항 내용을 HTML로 구조화하세요:
- <p> 태그로 각 조항/항 감싸기
- <ol>, <li> 태그로 호/목 나열
- 들여쓰기와 구조 보존

## 복합 condition_expression 예제
- deal_structure == "JOINT_VENTURE" and has_veto_rights == True
- has_put_option == True and put_trigger_event != ""
- deal_structure == "MINORITY_INVESTMENT" and has_anti_dilution == True
- has_tag_along_right == True or has_drag_along_right == True
- has_ipo_obligation == True and ipo_timeline_months > 0
- non_compete_period_months > 0

## 출력 형식
JSON만 반환하세요. 설명이나 코멘트를 포함하지 마세요.
```json
{
  "clauses": [
    {
      "clause_order": 0,
      "title": "전문",
      "content": "<p>{{ shareholders }}(이하 각 &quot;주주&quot;)는 ...</p>",
      "original_content": "<p>A펀드와 B법인(이하 각 &quot;주주&quot;)은 ...</p>",
      "is_boilerplate": false,
      "condition_expression": null,
      "confidence": 0.9
    }
  ]
}
```"""


# ── BTA Step 2: 조항 분해 프롬프트 ─────────────────────────────────────────────

_BTA_STEP2_SYSTEM_PROMPT = """당신은 한국 M&A 법률 문서 전문가이자 Jinja2 템플릿 엔지니어입니다.
BTA(영업양수도계약서) 원문을 조항별로 분해하고, 변수 값을 Jinja2 템플릿 문법으로 변환합니다.

## 표준 BTA 조항 구조 (16개 표준 조)
1. 전문 (Preamble) — 당사자 식별, 양도 배경
2. 정의 (Definitions) — 양도대상 영업, 자산, 부채 등 핵심 정의
3. 양도대상 영업/자산/부채의 특정 (Transfer Scope) — 유형자산, 무형자산, 계약, 제외 항목
4. 양수도대금 및 정산 (Purchase Price & Adjustments) — 대금, 보증금, 잔금, 운전자본 조정
5. 임직원 승계 (Employee Succession) — 승계 대상, 퇴직금 처리, 근로조건
6. 거래종결 전 선행조건 (Conditions Precedent) — 규제 승인, 핵심 계약 동의
7. 거래종결 (Closing Mechanics) — 종결 절차, 인도 사항
8. 진술 및 보증 (Representations & Warranties) — 매도인/매수인 R&W
9. 확약/서약 (Covenants) — 중간기간 운영 제한
10. 경업금지 (Non-Compete & Non-Solicitation) — 기간, 범위
11. 전환서비스 (Transition Services Agreement) — 서비스 범위, 기간
12. 상표/브랜드 라이선스 (Brand License) — 범위, 기간, 로열티
13. 손해배상 (Indemnification) — de minimis, basket, cap
14. 해제/해지 (Termination) — 종료 사유, 위약금
15. 비밀유지 (Confidentiality) — 범위, 기간
16. 일반 조항 (General Provisions) — 준거법, 분쟁해결, 통지

원문의 조/항/호 구조를 최대한 보존하세요.

## Jinja2 변환 규칙
- confirmed_variables 목록에 있는 변수만 사용하세요.
- 리터럴 값 → {{ variable_key }}
- 금액 → {{ base_purchase_price | currency_format }}
- 날짜 → {{ closing_date | date_format }}
- 숫자 → {{ employee_count | number_format }}
- 조건부 블록 → {% if employee_succession_included %}...{% endif %}

## 한글 금액 표기 가이드
- currency_format 필터는 "금 {천단위 구분 숫자}원" 형태를 이미 포함합니다:
  - 입력: 10000000000 → 출력: "금 10,000,000,000원"
- 원문의 "금 일백억원정 (₩10,000,000,000)" 전체를 {{ variable_key | currency_format }}으로 치환하세요.
- ⚠ 이중 래핑 금지: "금 {{ var | currency_format }}원" (X) → {{ var | currency_format }} (O)
- 원문의 "OO억원" → 원 단위 숫자로 추출하여 변수에 저장, 표시는 currency_format 필터 사용
- 한글 표기와 아라비아 숫자가 병기된 경우: {{ variable_key | currency_format }} 하나로 통합
- 숫자만 필요한 경우: {{ base_purchase_price | number_format }}

## BTA 특화 조건부 렌더링
- 가격조정: {% if price_adjustment_included %}...{% endif %}
- 임직원 승계: {% if employee_succession_included %}...{% endif %}
- 경업금지: {% if non_compete_obligation_included %}...{% endif %}
- TSA: {% if tsa_required %}...{% endif %}
- 브랜드 라이선스: {% if brand_license_required %}...{% endif %}
- 부동산 임대: {% if real_estate_lease_included %}...{% endif %}
- 환경 면책: {% if has_environmental_indemnity %}...{% endif %}
- 인허가 이전: {% if has_permit_transfer %}...{% endif %}
- IP 이전: {% if has_ip_transfer %}...{% endif %}
- 재고 조정: {% if has_inventory_adjustment %}...{% endif %}
- 매출채권: {% if has_receivables_transfer %}...{% endif %}
- 우발채무: {% if has_contingent_liabilities %}...{% endif %}
- 세무 면책: {% if has_tax_indemnity %}...{% endif %}
- 퇴직연금: {% if has_pension_transfer %}...{% endif %}
- 보험 승계: {% if has_insurance_transfer %}...{% endif %}
- 공급/구매 계약: {% if has_supply_agreement_transfer %}...{% endif %}
- 리스/임대: {% if has_lease_transfer %}...{% endif %}
- IT 시스템: {% if has_it_system_transfer %}...{% endif %}
- 정부보조금: {% if has_government_subsidy %}...{% endif %}
- 하도급: {% if has_subcontract_transfer %}...{% endif %}
- 비유인: {% if has_non_solicitation %}...{% endif %}
- 선행조건: {% if has_condition_precedent %}...{% endif %}
- 특별 배상: {% if has_special_indemnity %}...{% endif %}

## BTA 양도 범위별 조건부 조항
- COMPREHENSIVE_TRANSFER: deal_structure == "COMPREHENSIVE_TRANSFER" — 포괄 양수도
  - 모든 자산/부채/계약/직원 일괄 이전, 제외 항목 최소
  - 예: {% if deal_structure == "COMPREHENSIVE_TRANSFER" and comprehensive_scope_confirmation %}<p>양도인은 본 계약에 따라 양도대상 영업 전부를 양수인에게 양도합니다.</p>{% endif %}
- PARTIAL_TRANSFER: deal_structure == "PARTIAL_TRANSFER" — 부분 양수도
  - 제외 자산/부채 목록이 상세, cherry-picking 구조
  - 예: {% if deal_structure == "PARTIAL_TRANSFER" %}<p>분리 대상 사업: {{ carve_out_scope }}</p><p>제외 자산: {{ excluded_assets_description }}</p><p>양도인 잔존 사업: {{ retained_business_description }}</p>{% endif %}

## 별지/부속서(Schedule) 처리
- 본문에서 "별지", "부속서", "양도대상 자산 목록" 참조 시: 참조 텍스트만 유지
- 흔한 BTA 별지: 양도대상 자산 목록, 승계 부채 목록, 승계 계약 목록, 승계 임직원 명단
- 별지 참조 조항: 관련 BOOLEAN 조건으로 제어

## condition_expression 규칙
- Python 문법 사용
- 지원 연산자: ==, !=, <, >, <=, >=, in, not in, and, or, not
- 예: employee_succession_included == True
- 예: deal_structure == "PARTIAL_TRANSFER"
- 예: tsa_required == True and tsa_period_months > 0
- 예: has_special_indemnity == True and deal_structure == "COMPREHENSIVE_TRANSFER"
- 항상 포함되는 조항은 condition_expression을 null로 설정

## 진술 및 보증 처리
- 매도인/매수인 R&W 하위조(영업 소유권, 자산 하자, 환경, 고용 등)는 하나의 clause 내 HTML로 유지
- industry_type별 특화 하위조는 Jinja2 조건문으로 제어:
  - MANUFACTURING: 환경(has_environmental_indemnity), 재고(has_inventory_adjustment), 인허가(has_permit_transfer)
  - SOFTWARE: IP 이전(has_ip_transfer), IT 시스템(has_it_system_transfer)

## is_boilerplate 분류 (BTA 기준)
- True: 정의(구조), 비밀유지, 일반조항, 준거법/분쟁해결
- False: 양도대상, 대금/정산, 임직원, 선행조건, 종결, R&W, 확약, 경업금지, TSA, 브랜드, 손해배상, 해제

## 복합 condition_expression 예제
- deal_structure == "COMPREHENSIVE_TRANSFER" and employee_succession_included == True
- price_adjustment_included == True and price_adj_method == "nwc"
- tsa_required == True and tsa_period_months > 0
- non_compete_obligation_included == True and non_compete_period_months > 0
- brand_license_required == True and brand_license_period_months > 0
- has_environmental_indemnity == True and deal_structure == "COMPREHENSIVE_TRANSFER"
- deal_structure == "PARTIAL_TRANSFER" and has_ip_transfer == True
- has_non_solicitation == True and non_solicitation_period_months > 0
- has_condition_precedent == True
- has_insurance_transfer == True or has_lease_transfer == True

## content HTML 형식
조항 내용을 HTML로 구조화하세요:
- <p> 태그로 각 조항/항 감싸기
- <ol>, <li> 태그로 호/목 나열
- 들여쓰기와 구조 보존

## 출력 형식
JSON만 반환하세요. 설명이나 코멘트를 포함하지 마세요.
```json
{
  "clauses": [
    {
      "clause_order": 0,
      "title": "전문",
      "content": "<p>{{ seller_name }}(이하 &quot;양도인&quot;)과 {{ buyer_name }}(이하 &quot;양수인&quot;)은...</p>",
      "original_content": "<p>주식회사 ABC(이하 &quot;양도인&quot;)과 주식회사 DEF(이하 &quot;양수인&quot;)은...</p>",
      "is_boilerplate": false,
      "condition_expression": null,
      "confidence": 0.9
    }
  ]
}
```"""


# ── SSA Step 2: 조항 분해 프롬프트 ─────────────────────────────────────────────

_SSA_STEP2_SYSTEM_PROMPT = """당신은 한국 M&A 법률 문서 전문가이자 Jinja2 템플릿 엔지니어입니다.
SSA(신주인수계약서) 원문을 조항별로 분해하고, 변수 값을 Jinja2 템플릿 문법으로 변환합니다.

## 표준 SSA 조항 구조 (13개 표준 조)
1. 전문 (Preamble) — 당사자 식별, 투자 배경
2. 정의 (Definitions) — 신주, 인수대금, 전환가, 상환가 등 핵심 정의
3. 신주 발행 및 인수 (Subscription) — 증권 종류, 발행 주식 수, 발행가, 총 인수대금
4. 인수대금 납입 (Payment) — 납입일, 납입 방법, 분할 납입
5. 선행조건 (Conditions Precedent) — 이사회/주주총회 승인, 규제 승인
6. 거래종결 (Closing) — 종결 절차, 인도 사항
7. 진술 및 보증 (Representations & Warranties) — 발행회사/인수인 R&W
8. 확약 (Covenants) — 자금 용도 제한, 경영 참여, 정보 제공
9. 의무보유등록 (Lock-up) — 보유 기간, 예외 조건
10. 손해배상 (Indemnification) — de minimis, basket, cap, 존속기간
11. 해제/해지 (Termination) — 종료 사유, 위약금
12. 비밀유지 (Confidentiality) — 범위, 기간
13. 일반조항 (General Provisions) — 준거법, 분쟁해결, 통지

원문의 조/항/호 구조를 최대한 보존하세요.

## Jinja2 변환 규칙
- confirmed_variables 목록에 있는 변수만 사용하세요.
- 리터럴 값 → {{ variable_key }}
- 금액 → {{ total_subscription_amount | currency_format }}
- 날짜 → {{ payment_date | date_format }}
- 숫자 → {{ subscription_share_count | number_format }}
- 비율 → {{ post_investment_equity_ratio }}%
- 조건부 블록 → {% if has_anti_dilution %}...{% endif %}

## 한글 금액 표기 가이드
- currency_format 필터는 "금 {천단위 구분 숫자}원" 형태를 이미 포함합니다:
  - 입력: 5000000000 → 출력: "금 5,000,000,000원"
- 원문의 "금 오십억원정 (₩5,000,000,000)" 전체를 {{ variable_key | currency_format }}으로 치환하세요.
- ⚠ 이중 래핑 금지: "금 {{ var | currency_format }}원" (X) → {{ var | currency_format }} (O)
- 숫자만 필요한 경우: {{ total_subscription_amount | number_format }}

## SSA 특화 조건부 렌더링
- 병행 거래: {% if has_parallel_transaction %}...{% endif %}
- 의무보유: {% if has_lock_up %}...{% endif %}
- 자금 용도 제한: {% if has_use_of_proceeds_restriction %}...{% endif %}
- 손해배상 한도: {% if has_indemnification_cap %}...{% endif %}
- 희석방지: {% if has_anti_dilution %}...{% endif %}
- 청산우선권: {% if has_liquidation_preference %}...{% endif %}
- Drag-Along: {% if has_drag_along %}...{% endif %}
- Tag-Along: {% if has_tag_along %}...{% endif %}
- 이사 지명: {% if has_board_nomination_right %}...{% endif %}
- 정보권: {% if has_information_rights %}...{% endif %}
- 신주인수권: {% if has_preemptive_rights %}...{% endif %}
- 전환권: {% if has_conversion_right %}...{% endif %}
- 상환권: {% if has_redemption_right %}...{% endif %}
- 풋옵션: {% if has_put_option %}...{% endif %}
- 콜옵션: {% if has_call_option %}...{% endif %}
- 배당 우선: {% if has_dividend_preference %}...{% endif %}
- 마일스톤: {% if has_milestone_payment %}...{% endif %}
- 에스크로: {% if has_escrow %}...{% endif %}
- 분할 납입: {% if installment_payment_included %}...{% endif %}
- 선행조건: {% if has_condition_precedent %}...{% endif %}

## 증권 종류별 조건부 조항
- RCPS 관련: deal_structure == "RCPS" — 전환/상환 조건, 우선배당, 참가적/비참가적
- CB 관련: deal_structure == "CB" — 전환사채 조건, 표면이율, 만기
- BW 관련: deal_structure == "BW" — 신주인수권 행사가격, 분리형/비분리형

## 별지/부속서(Schedule) 처리
- 본문에서 "별지", "부속서" 참조 시: 참조 텍스트만 유지
- 흔한 SSA 별지: 주주명부, 전환/상환 조건 상세, R&W 목록, CP 체크리스트

## condition_expression 규칙
- Python 문법 사용
- 지원 연산자: ==, !=, <, >, <=, >=, in, not in, and, or, not
- 예: has_anti_dilution == True
- 예: deal_structure == "RCPS"
- 예: has_lock_up == True and lock_up_period_months > 0
- 항상 포함되는 조항은 condition_expression을 null로 설정

## is_boilerplate 분류 (SSA 기준)
- True: 정의(구조), 비밀유지, 일반조항, 준거법/분쟁해결
- False: 신주 발행, 납입, 선행조건, 종결, R&W, 확약, 의무보유, 손해배상, 해제

## content HTML 형식
조항 내용을 HTML로 구조화하세요:
- <p> 태그로 각 조항/항 감싸기
- <ol>, <li> 태그로 호/목 나열
- 들여쓰기와 구조 보존

## 복합 condition_expression 예제
- deal_structure == "RCPS" and has_conversion_right == True
- deal_structure == "CB" and coupon_rate > 0
- has_anti_dilution == True and has_preemptive_rights == True
- has_lock_up == True and lock_up_period_months > 0
- has_parallel_transaction == True
- has_use_of_proceeds_restriction == True
- has_condition_precedent == True and cp_board_approval == True
- installment_payment_included == True

## 출력 형식
JSON만 반환하세요. 설명이나 코멘트를 포함하지 마세요.
```json
{
  "clauses": [
    {
      "clause_order": 0,
      "title": "전문",
      "content": "<p>{{ issuer_name }}(이하 &quot;발행회사&quot;)과 {{ subscriber_name }}(이하 &quot;인수인&quot;)은...</p>",
      "original_content": "<p>주식회사 ABC(이하 &quot;발행회사&quot;)과 주식회사 DEF(이하 &quot;인수인&quot;)은...</p>",
      "is_boilerplate": false,
      "condition_expression": null,
      "confidence": 0.9
    }
  ]
}
```"""


# ── MOU Step 2: 조항 분해 프롬프트 ─────────────────────────────────────────────

_MOU_STEP2_SYSTEM_PROMPT = """당신은 한국 M&A 법률 문서 전문가이자 Jinja2 템플릿 엔지니어입니다.
MOU(양해각서) 원문을 조항별로 분해하고, 변수 값을 Jinja2 템플릿 문법으로 변환합니다.

## 표준 MOU 조항 구조 (10개 표준 조)
1. 전문 (Preamble) — 당사자 식별, 거래 배경
2. 정의 (Definitions) — 대상회사, 대상 주식/영업, 핵심 용어
3. 거래 구조 개요 (Transaction Overview) — 양도 방식, 지분율, 거래 개요
4. 가격 조건 (Price Terms) — 잠정 매매대금, 가격산정 공식, EBITDA 배수
5. 독점협상 (Exclusivity) — 배타적 협상권, 기간, 위반 효과
6. 보증금/이행보증 (Deposit) — 금액, 납입, 반환/몰취 조건
7. 실사 (Due Diligence) — 기간, 범위, 자료 접근
8. 진행 일정 및 종료 (Timeline & Termination) — MOU 유효기한, 해지 사유
9. 비밀유지 (Confidentiality) — 범위, 기간, 위약벌
10. 일반조항 (General Provisions) — 법적 구속력, 준거법, 분쟁해결, 통지

원문의 조/항/호 구조를 최대한 보존하세요.

## Jinja2 변환 규칙
- confirmed_variables 목록에 있는 변수만 사용하세요.
- 리터럴 값 → {{ variable_key }}
- 금액 → {{ indicative_price | currency_format }}
- 날짜 → {{ signing_date | date_format }}
- 숫자 → {{ dd_period_days | number_format }}
- 비율 → {{ equity_ratio }}%
- 조건부 블록 → {% if deposit_included %}...{% endif %}

## 한글 금액 표기 가이드
- currency_format 필터는 "금 {천단위 구분 숫자}원" 형태를 이미 포함합니다:
  - 입력: 10000000000 → 출력: "금 10,000,000,000원"
- 원문의 "금 일백억원정 (₩10,000,000,000)" 전체를 {{ variable_key | currency_format }}으로 치환하세요.
- ⚠ 이중 래핑 금지: "금 {{ var | currency_format }}원" (X) → {{ var | currency_format }} (O)
- 숫자만 필요한 경우: {{ indicative_price | number_format }}

## MOU 특화 조건부 렌더링
- 가격산정 공식: {% if price_formula_included %}...{% endif %}
- 독점협상: {% if exclusivity_period_included %}...{% endif %}
- 보증금: {% if deposit_included %}...{% endif %}
- 텀시트: {% if term_sheet_included %}...{% endif %}
- 위약금: {% if penalty_clause_included %}...{% endif %}
- 보증금 질권: {% if has_deposit_pledge %}...{% endif %}
- Break Fee: {% if has_break_fee %}...{% endif %}
- 실사비용 보전: {% if has_dd_cost_reimbursement %}...{% endif %}
- 가격조정 산식: {% if has_price_adjustment_clause %}...{% endif %}
- 텀시트 별지: {% if has_term_sheet_annex %}...{% endif %}
- 규제 승인: {% if has_regulatory_approval %}...{% endif %}
- Key-Man: {% if has_key_man_clause %}...{% endif %}
- 경업금지: {% if has_non_compete %}...{% endif %}
- 선행조건: {% if has_condition_precedent %}...{% endif %}
- 법적 구속력: {% if has_binding_clause %}...{% endif %}

## MOU 거래 유형별 조건부 조항
- SHARE_PURCHASE: deal_structure == "SHARE_PURCHASE" — 주식양수도 관련 용어/조항 사용
- BUSINESS_TRANSFER: deal_structure == "BUSINESS_TRANSFER" — 영업양수도 관련 용어/조항 사용
- NEW_SHARE_ISSUE: deal_structure == "NEW_SHARE_ISSUE" — 신주인수 관련 용어/조항 사용
- COMBINED: deal_structure == "COMBINED" — 복합 구조 조항

## 별지/부속서(Schedule) 처리
- MOU 별지: 텀시트(Term Sheet), 가격산정 별지, 실사 체크리스트, 이행보증금 납입 약정
- 별지 참조 시 참조 텍스트만 유지, 관련 BOOLEAN으로 제어

## condition_expression 규칙
- Python 문법 사용
- 지원 연산자: ==, !=, <, >, <=, >=, in, not in, and, or, not
- 예: deposit_included == True
- 예: deal_structure == "SHARE_PURCHASE"
- 예: exclusivity_period_included == True and exclusivity_period_days > 0
- 항상 포함되는 조항은 condition_expression을 null로 설정

## is_boilerplate 분류 (MOU 기준)
- True: 정의(구조), 비밀유지(일반), 통지, 완전합의, 준거법/분쟁해결
- False: 거래구조, 가격조건, 독점협상, 보증금, 실사, 일정/종료, 법적 구속력, 위약금

## content HTML 형식
조항 내용을 HTML로 구조화하세요:
- <p> 태그로 각 조항/항 감싸기
- <ol>, <li> 태그로 호/목 나열
- 들여쓰기와 구조 보존

## 복합 condition_expression 예제
- deposit_included == True and deposit_amount > 0
- exclusivity_period_included == True and exclusivity_period_days > 0
- price_formula_included == True and valuation_multiple > 0
- penalty_clause_included == True and penalty_amount > 0
- term_sheet_included == True
- has_binding_clause == True
- deal_structure == "COMBINED"
- has_dd_cost_reimbursement == True and dd_period_days > 0

## 출력 형식
JSON만 반환하세요. 설명이나 코멘트를 포함하지 마세요.
```json
{
  "clauses": [
    {
      "clause_order": 0,
      "title": "전문",
      "content": "<p>{{ seller_name }}(이하 &quot;매도인&quot;)과 {{ buyer_name }}(이하 &quot;매수인&quot;)은...</p>",
      "original_content": "<p>주식회사 ABC(이하 &quot;매도인&quot;)과 주식회사 DEF(이하 &quot;매수인&quot;)은...</p>",
      "is_boilerplate": false,
      "condition_expression": null,
      "confidence": 0.9
    }
  ]
}
```"""


async def analyze_step2_clauses(
    session_id: str,
    confirmed_variables: list[ExtractedVariable],
    deal_structure: str,
    industry_type: str,
    *,
    spa_text: str | None = None,
    doc_type_hint: str | None = None,
    owner_user_id: str = "",
) -> tuple[list[AnalyzedClause], float | None, str | None]:
    """Step 2: 확정 변수를 기반으로 조항을 분해한다.

    Args:
        spa_text: 멀티워커 폴백용. 세션 유실 시 이 텍스트로 임시 세션 생성.
        doc_type_hint: 멀티워커 폴백용. 세션 유실 시 detected_doc_type 복원.
        owner_user_id: 세션 소유권 검증용 사용자 ID.

    Returns:
        (clauses, cost, model)
    """
    try:
        session = _get_session(session_id, owner_user_id=owner_user_id)
    except ValueError:
        if spa_text:
            # 세션 한도 체크 (폴백 경로에서도 적용)
            if len(_sessions) >= _MAX_SESSIONS:
                _cleanup_expired_sessions()
                if len(_sessions) >= _MAX_SESSIONS:
                    raise RuntimeError("분석 세션 수가 한도에 도달했습니다. 잠시 후 다시 시도하세요.") from None
            session = AnalysisSession(session_id=session_id, spa_text=spa_text)
            if doc_type_hint:
                session.detected_doc_type = doc_type_hint
            _sessions[session_id] = session
            logger.info("멀티워커 폴백: session=%s 임시 생성 (doc_type=%s)", session_id, doc_type_hint or "SPA")
        else:
            raise

    # 비용 한도 체크
    if session.cost_usd >= _MAX_COST_PER_SESSION:
        msg = f"세션 비용 한도 초과 (${session.cost_usd:.2f} / ${_MAX_COST_PER_SESSION:.2f})"
        raise ValueError(msg)

    # 프롬프트 선택: 세션의 detected_doc_type에 따라 분기
    doc_type = session.detected_doc_type
    if doc_type == "SHA":
        system_prompt = _SHA_STEP2_SYSTEM_PROMPT
        doc_label = "SHA 주주간계약서"
    elif doc_type == "BTA":
        system_prompt = _BTA_STEP2_SYSTEM_PROMPT
        doc_label = "BTA 영업양수도계약서"
    elif doc_type == "SSA":
        system_prompt = _SSA_STEP2_SYSTEM_PROMPT
        doc_label = "SSA 신주인수계약서"
    elif doc_type == "MOU":
        system_prompt = _MOU_STEP2_SYSTEM_PROMPT
        doc_label = "MOU 양해각서"
    else:
        system_prompt = _STEP2_SYSTEM_PROMPT
        doc_label = "SPA"

    type_label_map: dict[str, str] = {
        "SHA": "SHA 유형",
        "BTA": "BTA 양도범위",
        "SSA": "SSA 증권종류",
        "MOU": "MOU 거래유형",
    }
    type_label = type_label_map.get(doc_type, "거래 구조")

    # 변수 목록을 프롬프트에 포함
    var_summary = "\n".join(f"- {v.variable_key} ({v.input_type}): {v.question_label}" for v in confirmed_variables)

    user_prompt = f"""## 확정된 변수 목록
{var_summary}

## {type_label}: {deal_structure}
## 산업 유형: {industry_type}

--- 계약서 원문 시작 ---
{session.spa_text}
--- 계약서 원문 끝 ---

위 {doc_label} 원문을 조항별로 분해하고, 확정된 변수를 Jinja2 템플릿으로 변환하세요."""

    data, cost, model = await _call_llm_json(system_prompt, user_prompt)

    if cost:
        session.cost_usd += cost

    # 조항 파싱 + condition_expression 검증 + clause_order 중복 제거
    raw_clauses = data.get("clauses", [])
    clauses: list[AnalyzedClause] = []
    seen_orders: set[int] = set()
    for rc in raw_clauses:
        # condition_expression 안전성 검증
        expr = rc.get("condition_expression")
        if expr and not validate_condition_expression(expr):
            logger.warning("Step 2: 유효하지 않은 condition_expression 제거: %s", expr)
            rc["condition_expression"] = None

        # clause_order 중복 방지
        order = rc.get("clause_order", len(seen_orders))
        if order in seen_orders:
            order = max(seen_orders) + 1 if seen_orders else 0
            logger.warning("Step 2: 중복 clause_order 재할당 → %d", order)
            rc["clause_order"] = order
        seen_orders.add(order)

        # LLM 응답의 content/original_content에 sanitize 적용 (XSS 방지)
        if rc.get("content"):
            rc["content"] = sanitize_html(rc["content"])
        if rc.get("original_content"):
            rc["original_content"] = sanitize_html(rc["original_content"])

        clauses.append(AnalyzedClause(**rc))

    doc_label_log = doc_type if doc_type != "SPA" else "SPA"
    logger.info(
        "%s Step 2 완료: session=%s, clauses=%d, cost=$%.4f, total_cost=$%.4f",
        doc_label_log,
        session_id,
        len(clauses),
        cost or 0.0,
        session.cost_usd,
    )

    return clauses, cost, model


# ── Step 3: 템플릿 생성 (DB 저장) ─────────────────────────────────────────────

_INPUT_TYPE_MAP: dict[str, TemplateVariableInputType] = {
    "TEXT": TemplateVariableInputType.TEXT,
    "TEXTAREA": TemplateVariableInputType.TEXTAREA,
    "NUMBER": TemplateVariableInputType.NUMBER,
    "DATE": TemplateVariableInputType.DATE,
    "SELECT": TemplateVariableInputType.SELECT,
    "BOOLEAN": TemplateVariableInputType.BOOLEAN,
    "CURRENCY": TemplateVariableInputType.CURRENCY,
    "PERCENTAGE": TemplateVariableInputType.PERCENTAGE,
}


_DOC_TYPE_MAP: dict[str, LegalDocType] = {
    "SPA": LegalDocType.SPA,
    "SHA": LegalDocType.SHA,
    "BTA": LegalDocType.BTA,
    "SSA": LegalDocType.SSA,
    "MOU": LegalDocType.MOU,
}


async def create_template_from_analysis(
    db: AsyncSession,
    template_name: str,
    template_description: str | None,
    variables: list[ExtractedVariable],
    clauses: list[AnalyzedClause],
    created_by_email: str | None,
    doc_type: str = "SPA",
) -> ContractTemplate:
    """Step 3: 분석 결과를 DB에 ContractTemplate으로 저장한다."""
    legal_doc_type = _DOC_TYPE_MAP.get(doc_type, LegalDocType.SPA)

    # 1. ContractTemplate 생성
    template = ContractTemplate(
        doc_type=legal_doc_type,
        name=template_name,
        description=template_description or f"LLM 분석으로 생성된 {doc_type} 템플릿: {template_name}",
        version="1.0.0",
        status=ContractTemplateStatus.ACTIVE,
        metadata_json={"source": "spa_analysis", "created_by": created_by_email},
        created_by_email=created_by_email,
    )
    db.add(template)
    await db.flush()

    # 2. ContractClause 생성 (clause_order 중복 방지)
    seen_orders: set[int] = set()
    for clause in clauses:
        order = clause.clause_order
        if order in seen_orders:
            # 중복 시 다음 빈 번호로 재할당
            order = max(seen_orders) + 1
            logger.warning("Step 3: 중복 clause_order 재할당: %d → %d", clause.clause_order, order)
        seen_orders.add(order)

        sanitized_content = sanitize_html(clause.content)
        # M4: Step 3에서 클라이언트 전송 condition_expression 재검증
        safe_condition = clause.condition_expression
        if safe_condition and not validate_condition_expression(safe_condition):
            logger.warning("Step 3: 유효하지 않은 condition_expression 제거: %s", safe_condition)
            safe_condition = None
        db_clause = ContractClause(
            template_id=template.id,
            clause_order=order,
            title=clause.title,
            content=sanitized_content,
            is_boilerplate=clause.is_boilerplate,
            condition_expression=safe_condition,
        )
        db.add(db_clause)

    # 3. TemplateVariable 생성 (variable_key 중복 방지)
    seen_keys: set[str] = set()
    for var in variables:
        if var.variable_key in seen_keys:
            logger.warning("Step 3: 중복 variable_key 무시: %s", var.variable_key)
            continue
        seen_keys.add(var.variable_key)

        input_type = _INPUT_TYPE_MAP.get(var.input_type, TemplateVariableInputType.TEXT)
        db_var = TemplateVariable(
            template_id=template.id,
            variable_key=var.variable_key,
            input_type=input_type,
            question_label=var.question_label,
            description=var.description,
            default_value=var.default_value,
            is_required=var.is_required,
            select_options=var.select_options,
            display_order=var.display_order,
            group_name=var.group_name,
            visible_condition=var.visible_condition,
        )
        db.add(db_var)

    await db.flush()
    await db.refresh(template)

    logger.info(
        "%s Step 3 완료: template_id=%s, name=%s, clauses=%d, variables=%d, user=%s",
        doc_type,
        template.id,
        template_name,
        len(clauses),
        len(variables),
        created_by_email,
    )

    return template
