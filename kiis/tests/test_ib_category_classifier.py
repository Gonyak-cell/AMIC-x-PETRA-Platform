"""IB 카테고리 분류기 테스트

Rule-based 키워드 매칭 분류 + 도메인 매핑 검증.
"""

from app.models.ib_article import CATEGORY_DOMAIN_MAP, IBCategory
from app.services.ib_insight_service import classify_article_rule_based


def test_deal_progress_classification() -> None:
    """딜 진행 카테고리 분류"""
    category, domain, confidence = classify_article_rule_based(
        "A캐피탈, B사 인수 추진… 실사 돌입",
        "양사 간 LOI 체결 후 본실사에 착수했다.",
    )
    assert category == IBCategory.DEAL_PROGRESS
    assert domain == "fact"
    assert confidence > 0.0


def test_sourcing_history_classification() -> None:
    """소싱 내역 카테고리 분류"""
    category, domain, confidence = classify_article_rule_based(
        "C운용, 시리즈B 투자 집행 완료",
        "500억원 규모의 리드 투자로 공동 투자에 참여했다.",
    )
    assert category == IBCategory.SOURCING_HISTORY
    assert domain == "fact"
    assert confidence > 0.0


def test_investment_style_classification() -> None:
    """투자 성향 카테고리 분류"""
    category, domain, confidence = classify_article_rule_based(
        "D자산운용의 투자 철학과 바이아웃 전략",
        "핸즈온 운용 스타일을 지향하며 성장투자에 집중한다.",
    )
    assert category == IBCategory.INVESTMENT_STYLE
    assert domain == "opinion"
    assert confidence > 0.0


def test_reputation_classification() -> None:
    """GP 평판 카테고리 분류"""
    category, domain, confidence = classify_article_rule_based(
        "E자산운용, 업계 평가 갈린다",
        "트랙레코드와 LP 신뢰 측면에서 시장 평판이 논란이다.",
    )
    assert category == IBCategory.REPUTATION
    assert domain == "opinion"
    assert confidence > 0.0


def test_personnel_evaluation_classification() -> None:
    """운용인력 평가 카테고리 분류"""
    category, domain, confidence = classify_article_rule_based(
        "F운용 CIO, 경쟁사로 이직 확정",
        "핵심 인력 유출로 Key Man 리스크 우려가 커진다.",
    )
    assert category == IBCategory.PERSONNEL_EVALUATION
    assert domain == "opinion"
    assert confidence > 0.0


def test_unclassifiable_returns_none() -> None:
    """분류 불가 기사"""
    category, domain, confidence = classify_article_rule_based(
        "오늘의 날씨",
        "맑은 날씨가 이어질 전망입니다.",
    )
    assert category is None
    assert domain is None
    assert confidence == 0.0


def test_category_domain_map_consistency() -> None:
    """카테고리-도메인 매핑 일관성"""
    # Fact 카테고리
    assert CATEGORY_DOMAIN_MAP[IBCategory.DEAL_PROGRESS] == "fact"
    assert CATEGORY_DOMAIN_MAP[IBCategory.SOURCING_HISTORY] == "fact"
    # Opinion 카테고리
    assert CATEGORY_DOMAIN_MAP[IBCategory.INVESTMENT_STYLE] == "opinion"
    assert CATEGORY_DOMAIN_MAP[IBCategory.REPUTATION] == "opinion"
    assert CATEGORY_DOMAIN_MAP[IBCategory.PERSONNEL_EVALUATION] == "opinion"


def test_lead_text_none_handled() -> None:
    """lead_text가 None인 경우 분류"""
    category, domain, confidence = classify_article_rule_based(
        "인수 추진 실사 LOI 체결",
        None,
    )
    assert category == IBCategory.DEAL_PROGRESS
    assert domain == "fact"
    assert confidence > 0.0
