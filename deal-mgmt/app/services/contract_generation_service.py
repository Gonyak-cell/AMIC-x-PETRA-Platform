"""계약서 자동 생성 서비스 — 조항 조립 + Jinja2 렌더링 + LLM 스무딩."""

from __future__ import annotations

import ast
import dataclasses
import functools
import html as html_mod
import logging
import operator
import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from jinja2 import BaseLoader, StrictUndefined, TemplateSyntaxError, UndefinedError
from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import DocumentNotFoundError
from app.models.contract_clause import ContractClause
from app.models.contract_template import ContractTemplate
from app.models.enums import ContractTemplateStatus, LegalDocStatus
from app.models.legal_document import LegalDocument
from app.models.template_variable import TemplateVariable
from app.ralph.llm_client import RalphLLMClient

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True, slots=True)
class ContractGenerationResult:
    """generate_contract_html 파이프라인 결과."""

    legal_document: LegalDocument
    clauses_used: int
    clauses_skipped: int
    llm_smoothed: bool
    llm_cost: float | None
    timing: dict[str, float]


# ── Jinja2 샌드박스 환경 ──────────────────────────────────────────────────

_jinja_env = SandboxedEnvironment(loader=BaseLoader(), autoescape=True, undefined=StrictUndefined)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _number_format(value: Any) -> str:
    """숫자를 천단위 구분 포맷으로 변환한다. Decimal 정밀도를 보존한다."""
    from decimal import Decimal, InvalidOperation

    try:
        d = Decimal(str(value))
        if d == d.to_integral_value():
            return f"{int(d):,}"
        return f"{d:,.2f}"
    except (ValueError, TypeError, InvalidOperation):
        return str(value)


def _currency_format(value: Any) -> str:
    """금액을 원화 포맷으로 변환한다. Decimal 정밀도를 보존한다."""
    from decimal import Decimal, InvalidOperation

    try:
        d = Decimal(str(value))
        if d == d.to_integral_value():
            return f"금 {int(d):,}원"
        return f"금 {d:,.2f}원"
    except (ValueError, TypeError, InvalidOperation):
        return str(value)


def _date_format(value: str) -> str:
    """YYYY-MM-DD를 YYYY년 MM월 DD일로 변환한다."""
    if not value or not isinstance(value, str):
        return str(value)
    cleaned = str(value)[:10]
    if not _DATE_RE.match(cleaned):
        return str(value)
    parts = cleaned.split("-")
    return f"{parts[0]}년 {parts[1]}월 {parts[2]}일"


_jinja_env.filters["number_format"] = _number_format
_jinja_env.filters["currency_format"] = _currency_format
_jinja_env.filters["date_format"] = _date_format


# ── 조건식 안전 평가 ────────────────────────────────────────────────────────

_SAFE_OPS: dict[type, Any] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.Gt: operator.gt,
    ast.LtE: operator.le,
    ast.GtE: operator.ge,
    ast.In: lambda left, right: left in right,
    ast.NotIn: lambda left, right: left not in right,
}

_FORBIDDEN_RE = re.compile(
    r"\b(import|exec|eval|open)\b|__",
    re.IGNORECASE,
)


@functools.lru_cache(maxsize=256)
def _parse_expression(expression: str) -> ast.Expression:
    """조건식을 파싱하고 결과를 캐싱한다."""
    return ast.parse(expression, mode="eval")


@functools.lru_cache(maxsize=256)
def _compile_template(source: str) -> Any:
    """Jinja2 템플릿을 컴파일하고 결과를 캐싱한다."""
    return _jinja_env.from_string(source)


def clear_template_cache() -> None:
    """Jinja2 템플릿 및 조건식 파싱 캐시를 초기화한다. 템플릿 수정 후 호출."""
    global _llm_client
    _compile_template.cache_clear()
    _parse_expression.cache_clear()
    _llm_client = None


def _normalize_boolean_vars(variables: dict[str, Any]) -> dict[str, Any]:
    """문자열 'true'/'false'를 Python bool로 변환한다."""
    normalized = dict(variables)
    for key, val in normalized.items():
        if isinstance(val, str) and val.lower() in ("true", "false"):
            normalized[key] = val.lower() == "true"
    return normalized


def evaluate_condition(expression: str | None, variables: dict[str, Any]) -> bool:
    """조건식을 AST 기반 화이트리스트로 안전하게 평가한다.

    None이면 항상 True (무조건 포함).
    """
    if not expression:
        return True

    if _FORBIDDEN_RE.search(expression):
        logger.warning("조건식에 금지 토큰 발견: %s", expression)
        return False

    try:
        tree = _parse_expression(expression)
    except SyntaxError:
        logger.warning("조건식 구문 오류: %s", expression)
        return False

    return _eval_node(tree.body, variables)


def _eval_node(node: ast.AST, ctx: dict[str, Any]) -> Any:
    """AST 노드를 재귀적으로 평가한다."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return ctx.get(node.id)
    if isinstance(node, ast.List):
        return [_eval_node(el, ctx) for el in node.elts]
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, ctx)
        for op_node, comparator in zip(node.ops, node.comparators, strict=True):
            op_func = _SAFE_OPS.get(type(op_node))
            if op_func is None:
                logger.warning("조건식에 미지원 연산자: %s", type(op_node).__name__)
                return False
            right = _eval_node(comparator, ctx)
            try:
                if not op_func(left, right):
                    return False
            except TypeError:
                return False
            left = right
        return True
    if isinstance(node, ast.BoolOp):
        values = [_eval_node(v, ctx) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _eval_node(node.operand, ctx)
    return False


# ── 서비스 함수 ─────────────────────────────────────────────────────────────


async def get_template_with_details(
    db: AsyncSession,
    template_id: uuid.UUID,
) -> ContractTemplate:
    """템플릿 + 조항 + 변수를 한번에 조회한다."""
    q = (
        select(ContractTemplate)
        .options(
            selectinload(ContractTemplate.clauses),
            selectinload(ContractTemplate.variables),
        )
        .where(ContractTemplate.id == template_id)
    )
    result = await db.execute(q)
    template = result.scalar_one_or_none()
    if not template:
        raise DocumentNotFoundError("계약서 템플릿을 찾을 수 없습니다.")
    return template


async def list_active_templates(
    db: AsyncSession,
) -> list[ContractTemplate]:
    """활성 상태의 템플릿 목록을 조회한다."""
    q = (
        select(ContractTemplate)
        .where(ContractTemplate.status == ContractTemplateStatus.ACTIVE)
        .order_by(ContractTemplate.doc_type)
    )
    result = await db.execute(q)
    return list(result.scalars().all())


def validate_variables(
    template_vars: list[TemplateVariable],
    user_vars: dict[str, Any],
) -> list[str]:
    """필수 변수 누락을 검증한다. 누락된 변수 키 목록을 반환."""
    missing: list[str] = []
    for tv in template_vars:
        if tv.is_required and tv.variable_key not in user_vars:
            # 조건부 표시 변수는 조건이 충족되지 않으면 건너뜀
            if tv.visible_condition:
                if not evaluate_condition(tv.visible_condition, user_vars):
                    continue
            missing.append(tv.variable_key)
    return missing


def assemble_clauses(
    clauses: list[ContractClause],
    variables: dict[str, Any],
) -> tuple[list[dict[str, str]], int]:
    """조건 필터링 + Jinja2 렌더링을 수행한다.

    Returns:
        (렌더링된 조항 목록, 건너뛴 조항 수)
    """
    assembled: list[dict[str, str]] = []
    skipped = 0
    safe_vars = _normalize_boolean_vars(variables)

    # relationship order_by가 있지만, 방어적 정렬로 순서를 보장 (단위 테스트 등에서 미정렬 입력 대응)
    for clause in sorted(clauses, key=lambda c: c.clause_order):
        if not evaluate_condition(clause.condition_expression, safe_vars):
            skipped += 1
            continue

        if not clause.content or not clause.content.strip():
            logger.warning("빈 content 조항 건너뜀 (clause %s): %s", clause.clause_order, clause.title)
            skipped += 1
            continue

        try:
            tpl = _compile_template(clause.content)
            rendered = tpl.render(**safe_vars)
        except TemplateSyntaxError:
            logger.warning("Jinja 구문 오류 (clause %s): %s", clause.clause_order, clause.title)
            rendered = clause.content
        except UndefinedError as exc:
            logger.warning("Jinja 미정의 변수 (clause %s): %s — %s", clause.clause_order, clause.title, exc)
            rendered = clause.content

        assembled.append(
            {
                "order": str(clause.clause_order),
                "title": clause.title,
                "content": rendered,
                "is_boilerplate": str(clause.is_boilerplate),
            }
        )

    return assembled, skipped


def build_html(
    assembled: list[dict[str, str]],
    doc_type: str,
    title: str,
) -> str:
    """조립된 조항들을 HTML 문서로 합성한다."""
    if not assembled:
        logger.warning("조립된 조항이 0개입니다 (doc_type=%s, title=%s)", doc_type, title)

    safe_title = html_mod.escape(title)
    safe_doc_type = html_mod.escape(doc_type)
    sections: list[str] = []

    for i, clause in enumerate(assembled, 1):
        safe_clause_title = html_mod.escape(clause["title"])
        sections.append(
            f'<section class="contract-clause" data-clause-order="{clause["order"]}">\n'
            f"  <h2>제{i}조 ({safe_clause_title})</h2>\n"
            f"  {clause['content']}\n"
            f"</section>"
        )

    body = "\n\n".join(sections)

    return (
        f'<div class="contract-document" data-doc-type="{safe_doc_type}">\n'
        f'  <div class="contract-header">\n'
        f"    <h1>{safe_title}</h1>\n"
        f"  </div>\n"
        f'  <div class="contract-body">\n'
        f"    {body}\n"
        f"  </div>\n"
        f"</div>"
    )


# ── LLM 스무딩 ──────────────────────────────────────────────────────────────

_SMOOTHING_SYSTEM_PROMPT = """당신은 한국 M&A 법률 문서 전문가입니다.
아래 계약서 초안의 조항 번호, 교차 참조, 용어 일관성을 다듬어 주세요.

규칙:
1. 조항 번호를 순서대로 재정렬하세요 (제1조, 제2조, ...).
2. "제X조에서 정한" 등의 교차 참조를 정확한 조항 번호로 수정하세요.
3. "매도인", "매수인", "대상회사" 등 정의된 용어를 일관되게 사용하세요.
4. 법률 한국어 문체를 유지하세요 (예: "~한다", "~하여야 한다").
5. HTML 태그 구조를 보존하세요 (h1, h2, p, ol, li, section, div).
6. 내용 자체를 추가하거나 삭제하지 마시오 — 번호/참조/용어만 조정하세요.
7. 전체 HTML을 그대로 반환하세요. 설명이나 메타 텍스트를 추가하지 마세요."""

# LLM 클라이언트 싱글턴 — TLS 핸드셰이크 재사용
_llm_client: RalphLLMClient | None = None


def _get_llm_client() -> RalphLLMClient:
    """LLM 클라이언트 싱글턴을 반환한다."""
    global _llm_client
    if _llm_client is None:
        _llm_client = RalphLLMClient.from_settings(settings)
    return _llm_client


async def smooth_with_llm(html: str, doc_type: str) -> tuple[str, float | None]:
    """LLM으로 조항 번호, 교차 참조, 용어 통일을 다듬는다.

    Returns:
        (다듬어진 HTML, LLM 호출 비용 USD)
    """
    llm = _get_llm_client()
    if not llm.is_available:
        logger.warning("LLM 프로바이더 없음 — 스무딩 건너뜀 (doc_type=%s)", doc_type)
        return html, None

    try:
        t0 = time.monotonic()
        user_prompt = f"계약서 유형: {doc_type}\n\n{html}"
        smoothed = await llm.call(_SMOOTHING_SYSTEM_PROMPT, user_prompt)
        elapsed = time.monotonic() - t0
        cost = llm.total_cost_usd

        # LLM 출력 구조 검증 (3단계)
        smoothed_text = smoothed.strip()
        original_sections = html.count("<section")
        smoothed_sections = smoothed_text.count("<section")
        original_h2 = html.count("<h2")
        smoothed_h2 = smoothed_text.count("<h2")

        # 1) 섹션 수 정확 일치
        if original_sections > 0 and smoothed_sections != original_sections:
            logger.warning(
                "LLM 스무딩이 섹션 수를 변경: 원본 %d → 스무딩 %d — 원본 유지 (LLM 비용: $%.4f)",
                original_sections,
                smoothed_sections,
                cost or 0.0,
            )
            return html, None

        # 2) h2(조항 제목) 수 보존
        if original_h2 > 0 and smoothed_h2 != original_h2:
            logger.warning(
                "LLM 스무딩이 조항 제목 수를 변경: 원본 %d → 스무딩 %d — 원본 유지 (LLM 비용: $%.4f)",
                original_h2,
                smoothed_h2,
                cost or 0.0,
            )
            return html, None

        # 3) 텍스트 길이 ±30% 허용 (교차 참조 수정 등 자연 변동)
        if len(html) > 0:
            ratio = len(smoothed_text) / len(html)
            if ratio < 0.7 or ratio > 1.3:
                logger.warning(
                    "LLM 스무딩이 텍스트 길이를 크게 변경: 원본 %d → 스무딩 %d (%.0f%%) — 원본 유지 (LLM 비용: $%.4f)",
                    len(html),
                    len(smoothed_text),
                    ratio * 100,
                    cost or 0.0,
                )
                return html, None

        logger.info("LLM 스무딩 완료: doc_type=%s, elapsed=%.1fs, cost=$%.4f", doc_type, elapsed, cost)
        return sanitize_html(smoothed_text), cost
    except TimeoutError:
        logger.warning(
            "LLM 스무딩 타임아웃 — 원본 유지 (cost=$%.4f)",
            llm.total_cost_usd,
        )
        return html, None
    except (ConnectionError, OSError) as exc:
        logger.error(
            "LLM 네트워크 에러: %s (cost=$%.4f)",
            exc,
            llm.total_cost_usd,
        )
        return html, None
    except Exception:
        logger.exception(
            "LLM 스무딩 미예상 에러 (cost=$%.4f)",
            llm.total_cost_usd,
        )
        return html, None


# ── 메인 파이프라인 ─────────────────────────────────────────────────────────


async def generate_contract_html(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    template_id: uuid.UUID,
    title: str,
    variables: dict[str, Any],
    *,
    use_llm: bool = True,
    created_by_email: str | None = None,
) -> ContractGenerationResult:
    """전체 계약서 생성 파이프라인."""
    t_start = time.monotonic()

    # 1. 템플릿 조회
    template = await get_template_with_details(db, template_id)
    t_template = time.monotonic()

    # 2. 변수 유효성 검증 (boolean 정규화 포함)
    safe_vars = _normalize_boolean_vars(variables)
    missing = validate_variables(template.variables, safe_vars)
    if missing:
        raise ValueError(f"필수 변수가 누락되었습니다: {', '.join(missing)}")
    t_validate = time.monotonic()

    # 3. 조항 조립 + Jinja2 렌더링
    assembled, skipped = assemble_clauses(template.clauses, safe_vars)
    clauses_used = len(assembled)
    t_assemble = time.monotonic()

    # 4. HTML 문서 합성
    html = build_html(assembled, template.doc_type.value, title)
    t_html = time.monotonic()

    # 5. LLM 스무딩 (선택)
    llm_smoothed = False
    llm_cost: float | None = None
    if use_llm:
        html, llm_cost = await smooth_with_llm(html, template.doc_type.value)
        llm_smoothed = llm_cost is not None
    t_llm = time.monotonic()

    # 비용 안전망: DB 커밋 전에 비용을 먼저 로깅 (커밋 실패 시에도 비용 추적 가능)
    if llm_cost is not None:
        logger.info("LLM 비용 발생 (커밋 전): template=%s, cost=$%.4f", template.name, llm_cost)

    # 6. LegalDocument 레코드 생성
    legal_doc = LegalDocument(
        transaction_id=transaction_id,
        doc_type=template.doc_type,
        title=title,
        parameters=_sanitize_param_values(variables),
        template_version=template.version,
        template_id=template.id,
        generated_html=html,
        status=LegalDocStatus.READY,
        created_by_email=created_by_email,
    )
    db.add(legal_doc)
    await db.flush()
    await db.refresh(legal_doc)

    logger.info(
        "계약서 생성 완료: doc_id=%s, template=%s(%s), clauses=%d, skipped=%d, "
        "llm=%s, cost=$%.4f, user=%s, timing=[tmpl=%.2f val=%.2f asm=%.2f html=%.2f llm=%.2f total=%.2f]s",
        legal_doc.id,
        template.name,
        template.doc_type.value,
        clauses_used,
        skipped,
        llm_smoothed,
        llm_cost or 0.0,
        created_by_email,
        t_template - t_start,
        t_validate - t_template,
        t_assemble - t_validate,
        t_html - t_assemble,
        t_llm - t_html,
        t_llm - t_start,
    )

    timing = {
        "template_lookup": t_template - t_start,
        "validation": t_validate - t_template,
        "assembly": t_assemble - t_validate,
        "html_build": t_html - t_assemble,
        "llm_smoothing": t_llm - t_html,
        "total": t_llm - t_start,
    }

    return ContractGenerationResult(
        legal_document=legal_doc,
        clauses_used=clauses_used,
        clauses_skipped=skipped,
        llm_smoothed=llm_smoothed,
        llm_cost=llm_cost,
        timing=timing,
    )


_DANGEROUS_TAG_RE = re.compile(
    r"<\s*/?\s*(script|iframe|object|embed|link|form|input|meta|base|svg)\b[^>]*>",
    re.IGNORECASE,
)
_EVENT_HANDLER_RE = re.compile(r"\s+on\w+\s*=\s*[\"']?[^\"'>]*[\"']?", re.IGNORECASE)
_JS_URL_RE = re.compile(r"(href|src|action)\s*=\s*[\"']\s*(javascript|data):", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _sanitize_tag_attributes(html: str) -> str:
    """HTML 태그 내부의 numeric entity(&#...)를 디코딩하여 위험 속성을 재검사한다."""

    def _clean_tag(match: re.Match[str]) -> str:
        tag = match.group(0)
        if "&#" not in tag:
            return tag
        decoded = html_mod.unescape(tag)
        if decoded == tag:
            return tag
        if _DANGEROUS_TAG_RE.search(decoded):
            return ""
        decoded = _EVENT_HANDLER_RE.sub("", decoded)
        decoded = _JS_URL_RE.sub(r'\1="', decoded)
        return decoded

    return _HTML_TAG_RE.sub(_clean_tag, html)


def sanitize_html(html: str) -> str:
    """위험한 HTML 태그, 이벤트 핸들러, javascript:/data: URL을 제거한다.

    HTML entity 인코딩(&#111;nclick 등)을 통한 우회도 2-pass로 방지한다.
    """
    cleaned = _DANGEROUS_TAG_RE.sub("", html)
    cleaned = _EVENT_HANDLER_RE.sub("", cleaned)
    cleaned = _JS_URL_RE.sub(r'\1="', cleaned)
    # Pass 2: entity-encoded 우회 방지
    cleaned = _sanitize_tag_attributes(cleaned)
    return cleaned


def _sanitize_param_values(variables: dict[str, Any]) -> dict[str, Any]:
    """파라미터 문자열 값에서 HTML 태그를 제거한다 (저장 XSS 방지)."""
    result: dict[str, Any] = {}
    for key, val in variables.items():
        if isinstance(val, str) and "<" in val:
            result[key] = re.sub(r"<[^>]+>", "", val)
        else:
            result[key] = val
    return result


async def save_html(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    doc_id: uuid.UUID,
    html: str,
    *,
    last_modified_at: str | None = None,
    last_modified_by_email: str | None = None,
) -> LegalDocument:
    """편집된 HTML을 LegalDocument에 저장한다 (OCC 원자적 갱신)."""
    sanitized = sanitize_html(html)
    now = datetime.now(UTC)

    stmt = (
        sa_update(LegalDocument)
        .where(
            LegalDocument.id == doc_id,
            LegalDocument.transaction_id == transaction_id,
        )
        .values(generated_html=sanitized, updated_at=now)
    )

    # OCC: updated_at 일치 조건을 WHERE에 포함하여 원자적 갱신
    if last_modified_at:
        expected = datetime.fromisoformat(last_modified_at)
        stmt = stmt.where(LegalDocument.updated_at == expected)

    result = await db.execute(stmt)

    if result.rowcount == 0:
        # rowcount=0이면 문서 미존재 또는 OCC 충돌 — 구분
        check_q = select(LegalDocument.id).where(
            LegalDocument.id == doc_id,
            LegalDocument.transaction_id == transaction_id,
        )
        check = await db.execute(check_q)
        if check.scalar_one_or_none() is None:
            raise DocumentNotFoundError("법률 문서를 찾을 수 없습니다.")
        raise ValueError("문서가 다른 사용자에 의해 수정되었습니다. 새로고침 후 다시 시도하세요.")

    if last_modified_by_email:
        logger.info("계약서 HTML 편집 저장: doc_id=%s, user=%s", doc_id, last_modified_by_email)

    # 갱신된 문서 반환 (커밋은 라우터에서 수행)
    q = select(LegalDocument).where(LegalDocument.id == doc_id)
    refresh_result = await db.execute(q)
    return refresh_result.scalar_one()
