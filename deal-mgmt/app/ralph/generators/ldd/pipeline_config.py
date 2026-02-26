"""LDD 멀티 LLM 7단계 파이프라인 설정."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LDDPipelineConfig:
    """LDD 7단계 멀티 LLM 파이프라인 설정.

    모든 멀티 LLM Stage는 기본 OFF (opt-in).
    단일 LLM 모드와 하위 호환.
    """

    # ── Stage 활성화 ──
    stage3_risk_dual: bool = True
    """Stage 3: 듀얼 리스크 분석 (매수인 관점 + 독립 평가)."""

    stage4_gap_detection: bool = True
    """Stage 4: 누락 탐지 (체크리스트 + 자유 탐색 합집합)."""

    stage5_jurisdiction: bool = False
    """Stage 5: 관할권 교차 분석 (크로스보더 M&A 시만 활성화)."""

    stage6_narrative: bool = False
    """Stage 6: 6블록 서술 생성 (항목당 1-3페이지 심층 분석). 기본 OFF — 비용 ~$2-4 추가."""

    stage7_qa: bool = True
    """Stage 7: 최종 QA (독립 팩트체크)."""

    # ── 불일치 처리 정책 ──
    risk_gap_auto_resolve: int = 1
    """리스크 등급 gap≤N이면 자동 해결 (높은 쪽 채택 + 양측 근거 병기)."""

    risk_gap_human_review: int = 2
    """리스크 등급 gap≥N이면 변호사 필수 검토."""

    # ── 비용 관리 ──
    max_cost_usd: float = 15.0
    """전체 세션 비용 한도 (USD)."""

    max_iterations: int = 3
    """Ralph Loop 최대 반복 횟수."""

    # ── 누락 탐지 설정 ──
    gap_similarity_threshold: float = 0.6
    """Jaccard similarity > 이 값이면 중복으로 판정."""

    # ── 거래 컨텍스트 (런타임 주입) ──
    deal_type: str = ""
    """거래 유형 (예: 'M&A', 'JV', '사업양수도')."""

    industry: str = ""
    """대상 산업 (예: '식품', 'IT', '금융')."""

    is_cross_border: bool = False
    """크로스보더 거래 여부."""

    deal_summary: str = ""
    """거래 요약 (Stage 4 자유 탐색 프롬프트용)."""

    # ── 법무법인 스타일 ──
    law_firm_mode: bool = False
    """LAW_FIRM 리포트 타입: 3단 서술 + A/B/C/D 불확실성 라벨링 활성화."""

    # ── 리스크 등급 수치화 ──
    level_map: dict[str, int] = field(default_factory=lambda: {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
    })
