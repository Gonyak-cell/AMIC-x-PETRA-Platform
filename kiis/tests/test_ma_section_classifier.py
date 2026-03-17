"""MASectionClassifier v2 단위 테스트

자본시장법 기반 법률/실무 용어 배점표 + 동의어 사전 검증.
"""

import pytest

from app.services.ma_section_classifier import MASectionClassifier


@pytest.fixture()
def classifier() -> MASectionClassifier:
    return MASectionClassifier()


# ─── 기본 분류 ───────────────────────────────────────


class TestBasicClassification:
    def test_ma_core_keyword(self, classifier: MASectionClassifier) -> None:
        """M&A 핵심 키워드 (주식매매계약, 공개매수) → 통과."""
        result = classifier.classify("주식매매계약 체결 공개매수 진행", "")
        assert result.primary == "ma"
        assert "ma" in result.labels

    def test_governance_core_keyword(self, classifier: MASectionClassifier) -> None:
        """거버넌스 핵심 (주주행동주의, 다중대표소송) → 통과."""
        result = classifier.classify("주주행동주의 확산 다중대표소송 제기", "")
        assert result.primary == "governance"
        assert "governance" in result.labels

    def test_fund_core_keyword(self, classifier: MASectionClassifier) -> None:
        """펀드 핵심 (사모펀드, 바이아웃) → 통과."""
        result = classifier.classify("사모펀드 바이아웃 딜 성사", "")
        assert result.primary == "fund"
        assert "fund" in result.labels

    def test_below_threshold(self, classifier: MASectionClassifier) -> None:
        result = classifier.classify("날씨가 좋습니다", "")
        assert result.primary is None
        assert result.labels == []

    def test_multilabel_ma_and_governance(self, classifier: MASectionClassifier) -> None:
        """M&A + 거버넌스 동시 통과."""
        result = classifier.classify("공개매수 주주행동주의 위임장 대결", "분할합병 다중대표소송 이사회")
        assert "ma" in result.labels
        assert "governance" in result.labels


# ─── 동의어 치환 ─────────────────────────────────────


class TestSynonymMapping:
    def test_spa_to_stock_purchase(self, classifier: MASectionClassifier) -> None:
        """SPA → 주식매매계약 치환."""
        result = classifier.classify("SPA 체결 완료", "")
        assert result.scores["ma"] > 0

    def test_mou_to_yanghaegakseo(self, classifier: MASectionClassifier) -> None:
        """MOU → 양해각서 치환."""
        result = classifier.classify("MOU 체결", "인수 실사 진행")
        assert result.scores["ma"] > 0

    def test_dd_to_silsa(self, classifier: MASectionClassifier) -> None:
        """DD → 실사 치환."""
        result = classifier.classify("DD 착수", "")
        assert result.scores["ma"] > 0

    def test_pef_to_samopund(self, classifier: MASectionClassifier) -> None:
        """PEF → 사모펀드 치환."""
        result = classifier.classify("PEF 결성 바이아웃", "")
        assert result.scores["fund"] > 0

    def test_proxy_fight_to_wiminjang(self, classifier: MASectionClassifier) -> None:
        """프록시 파이트 → 위임장 대결 치환."""
        result = classifier.classify("프록시 파이트 개시", "다중대표소송 주주행동주의")
        assert "governance" in result.labels

    def test_vc_to_venture_capital(self, classifier: MASectionClassifier) -> None:
        """VC → 벤처캐피탈 치환."""
        result = classifier.classify("VC 투자 활발", "사모펀드 펀드레이징")
        assert result.scores["fund"] > 0

    def test_buyout_english(self, classifier: MASectionClassifier) -> None:
        """Buy-out → 바이아웃 치환."""
        result = classifier.classify("Buy-out 사모펀드 결성", "")
        assert result.scores["fund"] > 0

    def test_exit_to_exit(self, classifier: MASectionClassifier) -> None:
        """Exit → 엑시트 치환."""
        result = classifier.classify("Exit 전략 수립", "사모펀드 무한책임사원")
        assert result.scores["fund"] > 0

    def test_imsi_jusong_to_jujuchonghoe(self, classifier: MASectionClassifier) -> None:
        """임시주총 → 주주총회 치환."""
        result = classifier.classify("임시주총 소집", "주주행동주의 위임장 대결")
        assert result.scores["governance"] > 0


# ─── 문맥 동의어 (GP/LP) ────────────────────────────


class TestContextSynonyms:
    def test_gp_with_fund_context(self, classifier: MASectionClassifier) -> None:
        """GP + 펀드 문맥 → 무한책임사원 매핑 (핵심 +5)."""
        result = classifier.classify("GP 펀드 결성 완료", "사모펀드 출자 약정")
        assert result.scores["fund"] > 0

    def test_lp_with_fund_context(self, classifier: MASectionClassifier) -> None:
        """LP + 출자 문맥 → 유한책임사원 매핑 (핵심 +5)."""
        result = classifier.classify("LP 출자 확정 사모펀드", "")
        assert result.scores["fund"] > 0

    def test_gp_without_context(self, classifier: MASectionClassifier) -> None:
        """GP 단독 (펀드 문맥 없음) → 매핑 안 됨."""
        result = classifier.classify("GP 성능 향상", "GPU 클럭 속도")
        assert result.scores.get("fund", 0) < classifier.threshold


# ─── 제목/본문 가중치 ───────────────────────────────


class TestWeighting:
    def test_title_3x(self, classifier: MASectionClassifier) -> None:
        """제목 키워드 3배 가중치."""
        r1 = classifier.classify("공개매수", "")  # title: 5*3 = 15
        r2 = classifier.classify("", "공개매수")  # body: 5*1 = 5
        assert r1.scores["ma"] == r2.scores["ma"] * classifier.title_weight

    def test_body_only_accumulation(self, classifier: MASectionClassifier) -> None:
        """본문 키워드 축적으로도 임계값 통과 가능."""
        body = "주식매매계약 체결 후 공개매수 경영권 양수도"
        result = classifier.classify("최신 뉴스", body)
        # body: 핵심3개 * 5점 * 1배 = 15 → threshold 10 통과
        assert "ma" in result.labels


# ─── Step 4: 동시출현 보너스 ─────────────────────────


class TestCooccurrence:
    def test_national_pension_stewardship(self, classifier: MASectionClassifier) -> None:
        """국민연금 + 스튜어드십 코드 → 거버넌스 +3."""
        result = classifier.classify("주주행동주의 국민연금 스튜어드십 코드 적용", "다중대표소송")
        assert "governance" in result.labels

    def test_institutional_investor_shareholder_letter(self, classifier: MASectionClassifier) -> None:
        """기관투자자 + 주주서한 → 거버넌스 +3."""
        result = classifier.classify("기관투자자 주주서한 발송 주주행동주의", "위임장 대결")
        assert "governance" in result.labels

    def test_hedge_fund_board_entry(self, classifier: MASectionClassifier) -> None:
        """헤지펀드 + 이사회 진입 → 펀드 +3, 거버넌스 +3."""
        result = classifier.classify("헤지펀드 이사회 진입 시도 주주행동주의", "사모펀드 지분 매집")
        # 거버넌스와 펀드 둘 다 보너스
        assert result.scores["governance"] > 0
        assert result.scores["fund"] > 0


# ─── Step 4: 드롭 규칙 ──────────────────────────────


class TestDropRules:
    def test_national_pension_simple_investment(self, classifier: MASectionClassifier) -> None:
        """국민연금 + 단순투자 → 거버넌스 0점."""
        result = classifier.classify("국민연금 단순투자 지분 변동 주주총회", "의결권")
        assert result.scores["governance"] == 0

    def test_national_pension_portfolio_adjustment(self, classifier: MASectionClassifier) -> None:
        """국민연금 + 포트폴리오 조정 → 거버넌스 0점."""
        result = classifier.classify("국민연금 포트폴리오 조정 의결권", "주주총회")
        assert result.scores["governance"] == 0

    def test_hedge_fund_short_selling(self, classifier: MASectionClassifier) -> None:
        """헤지펀드 + 공매도 → 펀드 0점."""
        result = classifier.classify("헤지펀드 공매도 전략 사모펀드", "")
        assert result.scores["fund"] == 0

    def test_hedge_fund_returns(self, classifier: MASectionClassifier) -> None:
        """헤지펀드 + 수익률 → 펀드 0점."""
        result = classifier.classify("헤지펀드 수익률 분석", "사모펀드")
        assert result.scores["fund"] == 0

    def test_etf_drops_fund(self, classifier: MASectionClassifier) -> None:
        """ETF 출현 → 펀드 0점."""
        result = classifier.classify("ETF 사모펀드 펀드레이징", "")
        assert result.scores["fund"] == 0


# ─── 글로벌 펀드 드롭 ────────────────────────────────


class TestGlobalDrop:
    def test_etf_in_body(self, classifier: MASectionClassifier) -> None:
        """body에 ETF → 펀드 0점."""
        result = classifier.classify("사모펀드 바이아웃", "ETF 자금 유입 증가")
        assert result.scores["fund"] == 0

    def test_public_fund_in_body(self, classifier: MASectionClassifier) -> None:
        """body에 공모펀드 → 펀드 0점."""
        result = classifier.classify("사모펀드 결성", "공모펀드 수익률 비교")
        assert result.scores["fund"] == 0

    def test_retirement_pension_in_body(self, classifier: MASectionClassifier) -> None:
        """body에 퇴직연금 → 펀드 0점."""
        result = classifier.classify("사모펀드 바이아웃", "퇴직연금 운용 수익")
        assert result.scores["fund"] == 0

    def test_wrap_account_in_body(self, classifier: MASectionClassifier) -> None:
        """body에 랩어카운트 → 펀드 0점."""
        result = classifier.classify("사모펀드 펀드레이징", "랩어카운트 가입 증가")
        assert result.scores["fund"] == 0


# ─── primary 결정 ────────────────────────────────────


class TestPrimaryDecision:
    def test_highest_score_wins(self, classifier: MASectionClassifier) -> None:
        result = classifier.classify("주식매매계약 공개매수 분할합병", "소수주주권")
        assert result.primary == "ma"


# ─── 복합 문장 분류 (법률 실무) ──────────────────────


class TestLegalScenarios:
    def test_spa_signing(self, classifier: MASectionClassifier) -> None:
        """'주식매매계약(SPA)을 체결했다' → M&A 분류."""
        result = classifier.classify(
            "A사, B사 경영권 양수도 위한 SPA 체결",
            "포괄적 교환 방식으로 진행되며 실사 완료 후 공개매수를 통해 인수 절차가 마무리될 예정이다.",
        )
        assert result.primary == "ma"
        assert result.scores["ma"] >= classifier.threshold

    def test_shareholder_activism(self, classifier: MASectionClassifier) -> None:
        """'행동주의 펀드의 위임장 대결' → 거버넌스 분류."""
        result = classifier.classify(
            "주주행동주의 펀드, 프록시 파이트 선언", "다중대표소송 가능성을 언급하며 집중투표제 도입을 주주제안했다."
        )
        assert "governance" in result.labels

    def test_pef_fundraising(self, classifier: MASectionClassifier) -> None:
        """'PEF 1조원 블라인드펀드 결성' → 펀드 분류."""
        result = classifier.classify(
            "PEF 1조원 규모 블라인드펀드 결성", "무한책임사원(GP)으로서 운용보수와 성과보수 구조를 확정했다."
        )
        assert result.primary == "fund"


# ─── ClassifyResult 구조 ─────────────────────────────


class TestResultStructure:
    def test_version_2(self, classifier: MASectionClassifier) -> None:
        result = classifier.classify("테스트", "")
        assert result.detail["version"] == "2.0.0"

    def test_fallback_flag(self, classifier: MASectionClassifier) -> None:
        r1 = classifier.classify("테스트", None)
        r2 = classifier.classify("테스트", "본문 있음")
        assert r1.detail["fallback"] is True
        assert r2.detail["fallback"] is False
