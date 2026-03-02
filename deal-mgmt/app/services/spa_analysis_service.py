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
from typing import Any

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

# ── 세션 관리 (인메모리, TTL 30분) ────────────────────────────────────────────

_SESSION_TTL = 1800.0  # 30분
_MAX_COST_PER_SESSION = 5.0  # USD
_MAX_SESSIONS = 100  # 인메모리 세션 수 상한 (B-3)
_LLM_CALL_TIMEOUT = 120.0  # LLM 호출 타임아웃 (초) (D-4)

# 조건식 내 금지 토큰 (import, exec, eval, open, 던더) — defence-in-depth (B-1)

_FORBIDDEN_RE = re.compile(r"\b(import|exec|eval|open)\b|__", re.IGNORECASE)


@dataclass
class AnalysisSession:
    """Step 간 상태를 보존하는 분석 세션."""

    session_id: str
    spa_text: str
    created_at: float = field(default_factory=time.monotonic)
    cost_usd: float = 0.0
    model_used: str | None = None


_sessions: dict[str, AnalysisSession] = {}


def _get_session(session_id: str) -> AnalysisSession:
    """세션을 조회한다. 만료/미존재 시 ValueError."""
    _cleanup_expired_sessions()
    session = _sessions.get(session_id)
    if session is None:
        msg = "분석 세션이 만료되었거나 존재하지 않습니다. Step 1부터 다시 시작하세요."
        raise ValueError(msg)
    return session


def _cleanup_expired_sessions() -> None:
    """만료된 세션을 제거한다."""
    now = time.monotonic()
    expired = [k for k, v in _sessions.items() if now - v.created_at > _SESSION_TTL]
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
        except TimeoutError:
            raise RuntimeError(f"LLM 호출이 {_LLM_CALL_TIMEOUT:.0f}초 내에 응답하지 않았습니다.")
        except (json.JSONDecodeError, ValueError) as exc:
            if attempt < max_retries:
                logger.warning("LLM JSON 파싱 실패 (시도 %d/%d): %s", attempt + 1, max_retries + 1, exc)
                continue
            raise ValueError(f"LLM 응답을 JSON으로 파싱할 수 없습니다: {exc}") from exc


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
- SPA: 주식매매계약서 (Stock Purchase Agreement) — "주식 양도", "매매대금" 등
- SHA: 주주간계약서 (Shareholders' Agreement) — "주주 권리", "이사회 구성" 등
- BTA: 영업양수도계약서 (Business Transfer Agreement) — "영업 양도" 등
- SSA: 신주인수계약서 (Share Subscription Agreement) — "신주 발행", "인수" 등
- MOU: 양해각서 (Memorandum of Understanding) — "의향", "양해" 등

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


async def analyze_step1_variables(
    spa_text: str,
    language_hint: str | None = None,
) -> tuple[str, list[ExtractedVariable], str, str, str, list[DiscoveredBoolean], float | None, str | None]:
    """Step 1: 계약서 원문에서 변수를 추출한다.

    Returns:
        (session_id, variables, deal_structure, industry_type, detected_doc_type,
         discovered_booleans, cost, model)
    """
    session_id = str(uuid.uuid4())

    # 세션 수 상한 체크 (B-3)
    if len(_sessions) >= _MAX_SESSIONS:
        _cleanup_expired_sessions()
        if len(_sessions) >= _MAX_SESSIONS:
            raise RuntimeError("분석 세션 수가 한도에 도달했습니다. 잠시 후 다시 시도하세요.")

    # 세션 생성
    session = AnalysisSession(session_id=session_id, spa_text=spa_text)
    _sessions[session_id] = session

    # 사용자 프롬프트
    lang_hint = f"\n언어: {language_hint}" if language_hint else ""
    user_prompt = f"""--- 계약서 원문 시작 ---
{spa_text}
--- 계약서 원문 끝 ---{lang_hint}

위 계약서 원문을 분석하여 계약 유형을 감지하고, 재사용 가능한 템플릿 변수를 추출하세요."""

    data, cost, model = await _call_llm_json(_STEP1_SYSTEM_PROMPT, user_prompt)

    # 비용 기록
    if cost:
        session.cost_usd += cost
    session.model_used = model

    # 응답 파싱
    variables = [ExtractedVariable(**v) for v in data.get("variables", [])]
    deal_structure = data.get("deal_structure", "GENERAL")
    industry_type = data.get("industry_type", "GENERAL")
    detected_doc_type = data.get("detected_doc_type", "SPA")
    discovered = [DiscoveredBoolean(**b) for b in data.get("discovered_booleans", [])]

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
        "SPA Step 1 완료: session=%s, doc_type=%s, variables=%d, deal=%s, industry=%s, booleans=%d, cost=$%.4f",
        session_id,
        detected_doc_type,
        len(variables),
        deal_structure,
        industry_type,
        len(discovered),
        cost or 0.0,
    )

    return session_id, variables, deal_structure, industry_type, detected_doc_type, discovered, cost, model


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


async def analyze_step2_clauses(
    session_id: str,
    confirmed_variables: list[ExtractedVariable],
    deal_structure: str,
    industry_type: str,
    *,
    spa_text: str | None = None,
) -> tuple[list[AnalyzedClause], float | None, str | None]:
    """Step 2: 확정 변수를 기반으로 조항을 분해한다.

    Args:
        spa_text: 멀티워커 폴백용. 세션 유실 시 이 텍스트로 임시 세션 생성.

    Returns:
        (clauses, cost, model)
    """
    try:
        session = _get_session(session_id)
    except ValueError:
        if spa_text:
            session = AnalysisSession(session_id=session_id, spa_text=spa_text)
            _sessions[session_id] = session
            logger.info("멀티워커 폴백: session=%s 임시 생성", session_id)
        else:
            raise

    # 비용 한도 체크
    if session.cost_usd >= _MAX_COST_PER_SESSION:
        msg = f"세션 비용 한도 초과 (${session.cost_usd:.2f} / ${_MAX_COST_PER_SESSION:.2f})"
        raise ValueError(msg)

    # 변수 목록을 프롬프트에 포함
    var_summary = "\n".join(f"- {v.variable_key} ({v.input_type}): {v.question_label}" for v in confirmed_variables)

    user_prompt = f"""## 확정된 변수 목록
{var_summary}

## 거래 구조: {deal_structure}
## 산업 유형: {industry_type}

--- SPA 원문 시작 ---
{session.spa_text}
--- SPA 원문 끝 ---

위 SPA 원문을 조항별로 분해하고, 확정된 변수를 Jinja2 템플릿으로 변환하세요."""

    data, cost, model = await _call_llm_json(_STEP2_SYSTEM_PROMPT, user_prompt)

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

        clauses.append(AnalyzedClause(**rc))

    logger.info(
        "SPA Step 2 완료: session=%s, clauses=%d, cost=$%.4f, total_cost=$%.4f",
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
        db_clause = ContractClause(
            template_id=template.id,
            clause_order=order,
            title=clause.title,
            content=sanitized_content,
            is_boilerplate=clause.is_boilerplate,
            condition_expression=clause.condition_expression,
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
        "SPA Step 3 완료: template_id=%s, name=%s, clauses=%d, variables=%d, user=%s",
        template.id,
        template_name,
        len(clauses),
        len(variables),
        created_by_email,
    )

    return template
