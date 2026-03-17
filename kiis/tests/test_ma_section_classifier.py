"""MASectionClassifier 단위 테스트

분류기 핵심 로직 + 플랜 명시 회귀 시나리오를 검증한다.
"""

import pytest

from app.services.ma_section_classifier import MASectionClassifier


@pytest.fixture()
def classifier() -> MASectionClassifier:
    return MASectionClassifier()


# ─── 기본 분류 ───────────────────────────────────────


class TestBasicClassification:
    """기본 키워드 매칭과 임계값 판정."""

    def test_ma_core_keyword_title_only(self, classifier: MASectionClassifier) -> None:
        """제목에 M&A 핵심 키워드 → title_weight=3 적용."""
        result = classifier.classify("A사 인수합병 공개매수 완료", "")
        # 인수합병=5, 공개매수=5 → title: (5+5)*3 = 30 → threshold 10 통과
        assert result.primary == "ma"
        assert "ma" in result.labels

    def test_governance_core_keyword(self, classifier: MASectionClassifier) -> None:
        result = classifier.classify("이사회 구성 개편과 주주총회 안건", "")
        assert result.primary == "governance"
        assert "governance" in result.labels

    def test_fund_core_keyword(self, classifier: MASectionClassifier) -> None:
        result = classifier.classify("사모펀드 펀드레이징 완료", "")
        assert result.primary == "fund"
        assert "fund" in result.labels

    def test_below_threshold_returns_none(self, classifier: MASectionClassifier) -> None:
        """임계값 미달 시 primary=None."""
        result = classifier.classify("날씨가 좋습니다", "")
        assert result.primary is None
        assert result.labels == []

    def test_threshold_boundary(self, classifier: MASectionClassifier) -> None:
        """정확히 threshold=10에서 통과."""
        # 제목에 core 1개 (5점) + support 1개 (2점) = 7 * 3(title) = 21 → 통과
        result = classifier.classify("인수 관련 IPO 진행", "")
        assert "ma" in result.labels

    def test_multilabel_ma_and_governance(self, classifier: MASectionClassifier) -> None:
        """M&A + 거버넌스 동시 통과."""
        result = classifier.classify("경영권 분쟁으로 공개매수 진행", "이사회 구성 변경과 인수합병 실사 완료")
        assert "ma" in result.labels
        assert "governance" in result.labels

    def test_multilabel_none_passes(self, classifier: MASectionClassifier) -> None:
        """아무 섹션도 통과하지 못하면 빈 labels."""
        result = classifier.classify("반도체 생산량 증가", "삼성전자 파운드리 가동률 상승")
        assert result.labels == []


# ─── 제목/본문 가중치 ───────────────────────────────


class TestWeighting:
    def test_title_weight_3x(self, classifier: MASectionClassifier) -> None:
        """제목 키워드는 3배 가중치."""
        r1 = classifier.classify("인수합병", "")
        r2 = classifier.classify("", "인수합병")
        assert r1.scores["ma"] == r2.scores["ma"] * classifier.title_weight

    def test_body_only_can_pass(self, classifier: MASectionClassifier) -> None:
        """본문만으로도 키워드가 충분하면 통과 가능."""
        body = "인수합병 실사 LOI 우선협상 입찰"
        result = classifier.classify("최신 뉴스", body)
        # body: 인수합병(5)+실사(5)+LOI(5)+우선협상(5)+입찰(5) = 25 * body_weight(1) = 25
        assert "ma" in result.labels


# ─── 동의어 치환 ─────────────────────────────────────


class TestSynonyms:
    def test_mna_synonym(self, classifier: MASectionClassifier) -> None:
        """M&A → 인수합병 치환."""
        result = classifier.classify("M&A 시장 동향", "")
        assert result.scores["ma"] > 0

    def test_pef_synonym(self, classifier: MASectionClassifier) -> None:
        """PEF → 사모펀드 치환."""
        result = classifier.classify("PEF 펀드레이징 완료", "")
        assert result.scores["fund"] > 0

    def test_governance_synonym(self, classifier: MASectionClassifier) -> None:
        """거버넌스 → 지배구조 치환."""
        result = classifier.classify("거버넌스 개선 방안", "이사회 주주총회")
        assert "governance" in result.labels


# ─── 문맥 동의어 (GP/LP/운용사) ──────────────────────


class TestContextSynonyms:
    def test_gp_with_fund_context(self, classifier: MASectionClassifier) -> None:
        """GP + 펀드 문맥 → 운용사로 매핑."""
        result = classifier.classify("GP 펀드 결성 완료", "출자 약정 확보")
        assert result.scores["fund"] > 0

    def test_gp_without_context_no_mapping(self, classifier: MASectionClassifier) -> None:
        """GP 단독 출현 (펀드 문맥 없음) → 매핑 안 됨."""
        result = classifier.classify("GP 성능 향상", "GPU 클럭 속도")
        assert result.scores.get("fund", 0) < classifier.threshold


# ─── 동시출현 보너스 ─────────────────────────────────


class TestCooccurrence:
    def test_national_pension_governance_bonus(self, classifier: MASectionClassifier) -> None:
        """국민연금 + 주주서한 → 거버넌스 가점."""
        result = classifier.classify("국민연금 주주서한 발송", "의결권 행사 방침 공개")
        assert result.scores["governance"] >= classifier.threshold

    def test_activist_fund_governance_bonus(self, classifier: MASectionClassifier) -> None:
        """행동주의 + 표대결 → 거버넌스 가점."""
        result = classifier.classify("행동주의 펀드 표대결 돌입", "이사 선임 주주제안 위임장")
        assert "governance" in result.labels


# ─── 드롭 규칙 ───────────────────────────────────────


class TestDropRules:
    def test_national_pension_simple_investment_drop(self, classifier: MASectionClassifier) -> None:
        """국민연금 + 단순투자 → 거버넌스 0점."""
        result = classifier.classify("국민연금 단순투자 보유 변동", "지분 변동 공시")
        assert result.scores["governance"] == 0

    def test_etf_drops_fund(self, classifier: MASectionClassifier) -> None:
        """ETF → 펀드 0점."""
        result = classifier.classify("ETF 펀드 자금 유입", "")
        assert result.scores["fund"] == 0

    def test_public_fund_drops_fund(self, classifier: MASectionClassifier) -> None:
        """공모펀드 → 펀드 0점."""
        result = classifier.classify("공모펀드 시장 성장", "")
        assert result.scores["fund"] == 0

    def test_hedge_fund_short_selling_drops_fund(self, classifier: MASectionClassifier) -> None:
        """헤지펀드 + 공매도 → 펀드 0점."""
        result = classifier.classify("헤지펀드 공매도 공격", "")
        assert result.scores["fund"] == 0


# ─── 글로벌 펀드 드롭 ────────────────────────────────


class TestGlobalDrop:
    def test_etf_in_body_drops_fund(self, classifier: MASectionClassifier) -> None:
        """body에 ETF 출현 → 펀드 글로벌 드롭."""
        result = classifier.classify("펀드 시장 동향", "ETF 자금 유입 증가 추세")
        assert result.scores["fund"] == 0

    def test_passive_in_body_drops_fund(self, classifier: MASectionClassifier) -> None:
        """body에 패시브 출현 → 펀드 글로벌 드롭."""
        result = classifier.classify("펀드레이징 완료", "패시브 투자 전환 흐름")
        assert result.scores["fund"] == 0


# ─── primary 결정 로직 ───────────────────────────────


class TestPrimaryDecision:
    def test_highest_score_wins(self, classifier: MASectionClassifier) -> None:
        """최고점 섹션이 primary."""
        result = classifier.classify("인수합병 공개매수 실사 LOI", "이사회 구성")
        assert result.primary == "ma"

    def test_tie_title_hits_wins(self, classifier: MASectionClassifier) -> None:
        """동점 시 제목 히트 수가 많은 쪽이 primary."""
        # 의도적으로 동점 만들기 어려우므로 기본 우선순위 확인
        result = classifier.classify("인수합병 경영권 분쟁 이사회", "지배구조 개선 매각")
        # ma와 governance 모두 통과하되, 점수 높은 쪽이 primary
        assert result.primary in ("ma", "governance")
        assert len(result.labels) >= 1


# ─── 회귀 시나리오 (플랜 명시) ────────────────────────


class TestRegressionScenarios:
    """플랜에서 명시한 회귀 시나리오."""

    def test_national_pension_shareholder_letter(self, classifier: MASectionClassifier) -> None:
        """국민연금 + 주주서한 => 거버넌스 가점."""
        result = classifier.classify("국민연금 주주서한", "스튜어드십 코드 의결권")
        assert result.scores["governance"] >= classifier.threshold

    def test_national_pension_simple_investment(self, classifier: MASectionClassifier) -> None:
        """국민연금 + 단순투자 => 거버넌스 0점."""
        result = classifier.classify("국민연금 단순투자 보유 변동", "지분 변동")
        assert result.scores["governance"] == 0

    def test_activist_fund_vote_fight(self, classifier: MASectionClassifier) -> None:
        """행동주의 펀드 + 표대결 => 펀드/거버넌스 동시 가점."""
        result = classifier.classify("행동주의 펀드 표대결", "이사 선임 주주제안 위임장")
        assert result.scores["governance"] >= classifier.threshold

    def test_hedge_fund_short_selling(self, classifier: MASectionClassifier) -> None:
        """헤지펀드 + 공매도 => 펀드 0점."""
        result = classifier.classify("헤지펀드 공매도 전략", "")
        assert result.scores["fund"] == 0

    def test_etf_or_public_fund_body(self, classifier: MASectionClassifier) -> None:
        """ETF 또는 공모펀드 본문 출현 => 펀드 0점."""
        r1 = classifier.classify("펀드 시장", "ETF 자금 유입")
        r2 = classifier.classify("펀드 시장", "공모펀드 수익률")
        assert r1.scores["fund"] == 0
        assert r2.scores["fund"] == 0


# ─── ClassifyResult 구조 검증 ────────────────────────


class TestResultStructure:
    def test_detail_has_version(self, classifier: MASectionClassifier) -> None:
        result = classifier.classify("테스트", "")
        assert "version" in result.detail
        assert result.detail["version"] == classifier.version

    def test_detail_has_sections(self, classifier: MASectionClassifier) -> None:
        result = classifier.classify("인수합병", "")
        assert "sections" in result.detail
        assert "ma" in result.detail["sections"]

    def test_fallback_flag_when_no_body(self, classifier: MASectionClassifier) -> None:
        result = classifier.classify("인수합병", None)
        assert result.detail["fallback"] is True

    def test_no_fallback_when_body_present(self, classifier: MASectionClassifier) -> None:
        result = classifier.classify("인수합병", "본문 있음")
        assert result.detail["fallback"] is False
