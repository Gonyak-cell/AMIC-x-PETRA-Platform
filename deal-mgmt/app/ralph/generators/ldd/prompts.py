"""LDD(법률실사) 보고서 AI 분석 프롬프트 — 한국법 특화."""

from __future__ import annotations

# ── 시스템 프롬프트 ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
당신은 한국 M&A 법률실사(Legal Due Diligence) 전문가입니다.
대형 로펌(김앤장, 세종, 태평양, 광장)급 LDD 보고서를 작성하는 수준의 분석을 수행합니다.

핵심 원칙:
1. 사실관계 기반: 제공된 실사자료만을 근거로 분석하며, 자료에 없는 내용은 추측하지 않음
2. Deal Impact 구체화: 추상적 진술이 아닌, 가격·구조·일정에 미치는 구체적 영향 기술
3. Actionable 권고: "주의 필요" 같은 모호한 표현 대신 계약 조항, 진술보장, 추가 실사 등 구체적 행동 권고
4. Issue Level 엄격 판정:
   - CRITICAL: 거래 중단 또는 근본적 재구조화 필요 (예: 해제불가 담보권, 대규모 미신고 세금)
   - HIGH: 가격 조정 또는 계약 조건 변경 필요 (예: CoC 조항으로 주요 계약 해지 가능)
   - MEDIUM: 진술보장/면책 반영 필요하나 거래 구조에는 무영향 (예: 경미한 노무 분쟁)
   - LOW: 모니터링 수준, 거래에 실질적 영향 없음 (예: 등기 지연)
5. RFI 번호 체계: {section_prefix}-NNN 형식 (예: CORP-001, CONTRACT-015)
"""

# ── 항목 분석 프롬프트 ───────────────────────────────────────────────────────────

ITEM_ANALYSIS_PROMPT = """\
## 분석 대상

**항목**: {item_id} — {item_name}
**섹션**: {section_type} ({section_title})

## 제공된 실사자료

{source_materials}

## 이전 반복 피드백 (있는 경우)

{feedback}

## 분석 지침

위 실사자료를 검토하여 아래 JSON 형식으로 분석 결과를 반환하세요.

```json
{{
  "status": "OK | ISSUE | NA | PENDING",
  "issue_level": "CRITICAL | HIGH | MEDIUM | LOW | null",
  "risk_color": "RED | AMBER | GREEN",
  "description": "사실관계 서술 (관련 문서명, 조항, 날짜 구체적 기재)",
  "deal_impact": "거래에 미치는 영향 (가격/구조/일정 관점, 구체적 금액·비율 포함)",
  "recommendation": "권고사항 (계약 반영/추가 실사/진술보장 등 구체적 행동)",
  "rfi_required": true/false,
  "rfi_number": "{rfi_prefix}-NNN 또는 빈 문자열",
  "confidence": 0.0-1.0,
  "evidence_refs": ["파일명1", "파일명2"]
}}
```

### 판정 기준
- 자료가 충분하고 이슈 없음 → status: "OK", risk_color: "GREEN"
- 이슈 발견 → status: "ISSUE", issue_level에 따라 risk_color 결정
  - CRITICAL → "RED"
  - HIGH → "AMBER"
  - MEDIUM → "AMBER"
  - LOW → "GREEN"
- 해당 없음 → status: "NA"
- 자료 부족으로 판단 불가 → status: "PENDING", rfi_required: true

JSON만 반환하고 다른 텍스트는 포함하지 마세요.
"""

# ── Executive Summary 프롬프트 ──────────────────────────────────────────────────

EXECUTIVE_SUMMARY_PROMPT = """\
## 법률실사 분석 결과 요약

아래 10개 섹션의 분석 결과를 바탕으로 Executive Summary를 작성하세요.

{section_summaries}

## 작성 지침

1. **거래 개요**: 대상회사, 거래 유형, 실사 범위 1-2문장
2. **핵심 이슈**: Critical/High 이슈만 발견일자 순 정리 (최대 5개)
3. **Red Flag**: 거래 진행에 즉시 영향을 미치는 이슈
4. **조건선행 요건**: Closing 전 충족 필요 사항
5. **전체 의견**: 거래 진행 가능 여부에 대한 법률적 의견

형식: 마크다운 (# 제목, - 목록)

분량: 1-2페이지 (A4 기준)
"""

# ── 교차 검증 프롬프트 ─────────────────────────────────────────────────────────

CROSS_VALIDATION_PROMPT = """\
## 교차 검증

아래 LDD 보고서 전체를 검토하여 일관성 문제를 식별하세요.

{full_report}

## 검증 항목

1. **수치 일관성**: Executive Summary의 이슈 카운트 vs 본문 항목 수
2. **교차 참조 정합성**: 계약 섹션의 CoC 조항이 인허가 섹션의 CoC 영향과 일치하는지
3. **Issue Level 일관성**: 유사한 심각도의 이슈에 동일한 level이 부여되었는지
4. **누락 항목**: PENDING 상태로 남은 항목이 있는지
5. **RFI 번호 중복**: 동일 번호 사용 여부
6. **법률 용어 일관성**: 동일 개념에 다른 용어가 혼용되지 않는지

JSON 형식으로 반환:
```json
{{
  "issues": [
    {{
      "type": "inconsistency | missing | duplicate | terminology",
      "severity": "critical | warning | info",
      "description": "설명",
      "affected_sections": ["GOVERNANCE", "CONTRACTS"],
      "suggestion": "수정 제안"
    }}
  ],
  "overall_consistency_score": 0.0-5.0
}}
```
"""

# ── 섹션 재분석 프롬프트 (피드백 반영) ──────────────────────────────────────────

REFINEMENT_PROMPT = """\
## 재분석 요청

이전 분석 결과에 대해 아래 피드백이 있습니다.

### 이전 분석
{previous_analysis}

### 품질 평가 피드백
{gate_feedback}

### 개선 지침
- 피드백에서 지적된 사항을 구체적으로 반영하세요
- description, deal_impact, recommendation의 구체성을 높이세요
- 근거 자료(evidence_refs)가 부족하면 추가하세요
- issue_level이 과하거나 부족한 경우 재판정하세요

동일한 JSON 형식으로 개선된 분석을 반환하세요.
"""

# ── 소스 자료 포매팅 ─────────────────────────────────────────────────────────

def format_source_materials(
    parsed_files: list[dict],
    max_chars_per_file: int = 2000,
    max_total_chars: int = 15000,
) -> str:
    """파싱된 파일 목록을 LLM 입력용 텍스트로 포매팅한다."""
    parts: list[str] = []
    total = 0

    for f in parsed_files:
        name = f.get("name", "unknown")
        text = f.get("text", "")[:max_chars_per_file]
        tables_info = ""
        if f.get("tables"):
            tables_info = f"\n  [표 {len(f['tables'])}개]"
            for t in f["tables"][:2]:
                headers = t.get("headers", [])
                if headers:
                    tables_info += f"\n  헤더: {', '.join(str(h) for h in headers[:5] if h is not None)}"

        entry = f"### 📄 {name}{tables_info}\n{text}\n"
        if total + len(entry) > max_total_chars:
            parts.append(f"\n... (이하 {len(parsed_files) - len(parts)}개 파일 생략)")
            break
        parts.append(entry)
        total += len(entry)

    return "\n".join(parts) if parts else "(관련 실사자료 없음)"
