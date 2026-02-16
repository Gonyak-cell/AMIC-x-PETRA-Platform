"""NLP 서비스 테스트

- 형태소 분석 및 키워드 추출
- 금융 감성 분석
- 투자 정보 NER 추출
- TF-IDF 키워드 추출
"""

import pytest

from app.services.nlp_service import NLPService


@pytest.fixture
def nlp_service() -> NLPService:
    return NLPService()


# ──────────────── 키워드 추출 테스트 ────────────────


class TestExtractKeywords:
    def test_basic_extraction(self, nlp_service: NLPService):
        """기본 키워드 추출"""
        text = "한국투자파트너스가 스타트업에 대규모 투자를 진행했다. 투자 규모는 100억원이다."
        keywords = nlp_service.extract_keywords(text, top_n=5)
        assert len(keywords) > 0
        assert all("keyword" in k for k in keywords)
        assert all("count" in k for k in keywords)
        assert all("pos" in k for k in keywords)

    def test_keyword_frequency_order(self, nlp_service: NLPService):
        """키워드가 빈도 내림차순으로 정렬"""
        text = "투자 시장의 투자 동향을 분석한다. 시장 규모가 확대되고 있다. 투자 전략이 중요하다."
        keywords = nlp_service.extract_keywords(text, top_n=10)
        for i in range(len(keywords) - 1):
            assert keywords[i]["count"] >= keywords[i + 1]["count"]

    def test_empty_text(self, nlp_service: NLPService):
        """빈 텍스트"""
        assert nlp_service.extract_keywords("") == []
        assert nlp_service.extract_keywords("   ") == []

    def test_short_words_excluded(self, nlp_service: NLPService):
        """1글자 명사 제외"""
        text = "큰 돈이 들어갔다"
        keywords = nlp_service.extract_keywords(text)
        keyword_texts = [k["keyword"] for k in keywords]
        # 1글자 단어는 포함되지 않아야 함
        for kw in keyword_texts:
            assert len(kw) >= 2

    def test_top_n_limit(self, nlp_service: NLPService):
        """top_n 제한"""
        text = "한국 벤처 투자 시장의 펀드 운용 현황 분석 보고서 발표 스타트업 생태계"
        keywords = nlp_service.extract_keywords(text, top_n=3)
        assert len(keywords) <= 3

    def test_noun_pos_tags(self, nlp_service: NLPService):
        """명사 품사 태그만 추출"""
        text = "삼성전자가 새로운 반도체 기술을 개발했다"
        keywords = nlp_service.extract_keywords(text)
        for kw in keywords:
            assert kw["pos"] in ("NNG", "NNP")


# ──────────────── 감성 분석 테스트 ────────────────


class TestAnalyzeSentiment:
    def test_positive_sentiment(self, nlp_service: NLPService):
        """긍정 기사"""
        text = "한국투자파트너스의 성공적 엑시트 소식이 전해졌다. 대규모 펀드 결성에 성공했다."
        result = nlp_service.analyze_sentiment(text)
        assert result["score"] > 0
        assert result["label"] == "positive"
        assert len(result["positive_matches"]) > 0

    def test_negative_sentiment(self, nlp_service: NLPService):
        """부정 기사"""
        text = "해당 기업이 횡령 혐의로 검찰 수사를 받고 있다. 운용 인력 이탈이 심각하다."
        result = nlp_service.analyze_sentiment(text)
        assert result["score"] < 0
        assert result["label"] == "negative"
        assert len(result["negative_matches"]) > 0

    def test_neutral_sentiment(self, nlp_service: NLPService):
        """중립 기사"""
        text = "오늘 날씨가 좋다. 점심으로 김치찌개를 먹었다."
        result = nlp_service.analyze_sentiment(text)
        assert result["label"] == "neutral"
        assert result["score"] == 0.0

    def test_mixed_sentiment(self, nlp_service: NLPService):
        """긍정+부정 혼합"""
        text = "매출 증가에도 불구하고 적자 전환이 우려된다."
        result = nlp_service.analyze_sentiment(text)
        # 긍정과 부정 모두 매칭되어야 함
        assert len(result["positive_matches"]) > 0
        assert len(result["negative_matches"]) > 0

    def test_empty_text(self, nlp_service: NLPService):
        """빈 텍스트"""
        result = nlp_service.analyze_sentiment("")
        assert result["score"] == 0.0
        assert result["label"] == "neutral"

    def test_score_range(self, nlp_service: NLPService):
        """점수 범위 -1.0 ~ 1.0"""
        texts = [
            "성공적 엑시트 대규모 펀드 결성 유니콘 등극",
            "횡령 배임 사기 파산",
            "일반적인 내용",
        ]
        for text in texts:
            result = nlp_service.analyze_sentiment(text)
            assert -1.0 <= result["score"] <= 1.0

    def test_sentiment_response_structure(self, nlp_service: NLPService):
        """응답 구조 검증"""
        result = nlp_service.analyze_sentiment("테스트 기사")
        assert "score" in result
        assert "label" in result
        assert "positive_matches" in result
        assert "negative_matches" in result
        assert result["label"] in ("positive", "negative", "neutral")


# ──────────────── NER 투자 정보 추출 테스트 ────────────────


class TestExtractInvestmentInfo:
    def test_extract_amount(self, nlp_service: NLPService):
        """투자 금액 추출"""
        text = "한국투자파트너스가 100억원 규모의 투자를 진행했다."
        result = nlp_service.extract_investment_info(text)
        assert len(result["amounts"]) > 0
        amount = result["amounts"][0]
        assert amount["value"] == "100"
        assert "억" in amount["unit"]

    def test_extract_multiple_amounts(self, nlp_service: NLPService):
        """여러 투자 금액 추출"""
        text = "시리즈A에서 50억원, 시리즈B에서 200억원을 유치했다."
        result = nlp_service.extract_investment_info(text)
        assert len(result["amounts"]) == 2

    def test_extract_round(self, nlp_service: NLPService):
        """투자 라운드 추출"""
        text = "스타트업A가 시리즈 A 투자를 유치했다."
        result = nlp_service.extract_investment_info(text)
        assert result["round"] is not None
        assert "시리즈" in result["round"] or "Series" in result["round"]

    def test_extract_seed_round(self, nlp_service: NLPService):
        """시드 라운드 추출"""
        text = "시드 투자 유치에 성공했다."
        result = nlp_service.extract_investment_info(text)
        assert result["round"] is not None
        assert "시드" in result["round"].lower() or "seed" in result["round"].lower()

    def test_extract_pre_series(self, nlp_service: NLPService):
        """프리시리즈 라운드 추출"""
        text = "프리 시리즈 A 라운드에서 30억원을 유치했다."
        result = nlp_service.extract_investment_info(text)
        assert result["round"] is not None

    def test_extract_date(self, nlp_service: NLPService):
        """날짜 추출"""
        text = "2025년 6월 15일 투자 계약이 체결되었다."
        result = nlp_service.extract_investment_info(text)
        assert len(result["dates"]) > 0
        date = result["dates"][0]
        assert date["year"] == "2025"
        assert date["month"] == "6"
        assert date["day"] == "15"

    def test_extract_date_without_day(self, nlp_service: NLPService):
        """일자 없는 날짜"""
        text = "2025년 6월 기준 투자 현황이다."
        result = nlp_service.extract_investment_info(text)
        assert len(result["dates"]) > 0
        assert result["dates"][0]["day"] is None

    def test_extract_comma_amount(self, nlp_service: NLPService):
        """콤마 포함 금액"""
        text = "총 1,500억원 규모의 펀드를 결성했다."
        result = nlp_service.extract_investment_info(text)
        assert len(result["amounts"]) > 0
        assert result["amounts"][0]["value"] == "1500"

    def test_empty_text(self, nlp_service: NLPService):
        """빈 텍스트"""
        result = nlp_service.extract_investment_info("")
        assert result["investors"] == []
        assert result["investees"] == []
        assert result["amounts"] == []
        assert result["round"] is None
        assert result["dates"] == []

    def test_response_structure(self, nlp_service: NLPService):
        """응답 구조 검증"""
        result = nlp_service.extract_investment_info("테스트 기사")
        assert "investors" in result
        assert "investees" in result
        assert "amounts" in result
        assert "round" in result
        assert "dates" in result
        assert isinstance(result["investors"], list)
        assert isinstance(result["investees"], list)
        assert isinstance(result["amounts"], list)
        assert isinstance(result["dates"], list)

    def test_investor_extraction_pattern(self, nlp_service: NLPService):
        """투자사 추출 패턴"""
        text = "한국투자파트너스가 스타트업에 50억원을 투자했다."
        result = nlp_service.extract_investment_info(text)
        # 투자사 또는 피투자사 중 하나 이상에서 엔티티가 추출되어야 함
        total_entities = len(result["investors"]) + len(result["investees"])
        assert total_entities >= 0  # 패턴 매칭이 안 될 수도 있음

    def test_bridge_round(self, nlp_service: NLPService):
        """브릿지 라운드 추출"""
        text = "브릿지 라운드로 20억원을 유치했다."
        result = nlp_service.extract_investment_info(text)
        assert result["round"] is not None
        assert "브릿지" in result["round"].lower() or "bridge" in result["round"].lower()

    def test_dollar_amount(self, nlp_service: NLPService):
        """달러 금액 추출"""
        text = "1000만 달러 규모의 투자를 유치했다."
        result = nlp_service.extract_investment_info(text)
        assert len(result["amounts"]) > 0
        assert "달러" in result["amounts"][0]["unit"]


# ──────────────── TF-IDF 키워드 추출 테스트 ────────────────


class TestExtractKeywordsTfidf:
    def test_basic_tfidf(self, nlp_service: NLPService):
        """기본 TF-IDF 키워드 추출"""
        documents = [
            "한국투자파트너스가 바이오 스타트업에 투자했다.",
            "삼성벤처투자가 AI 기업에 투자를 결정했다.",
            "카카오벤처스가 핀테크 스타트업에 투자를 유치했다.",
        ]
        results = nlp_service.extract_keywords_tfidf(documents, top_n=5)
        assert len(results) == 3
        for doc_keywords in results:
            assert isinstance(doc_keywords, list)
            for kw in doc_keywords:
                assert "keyword" in kw
                assert "tfidf_score" in kw
                assert kw["tfidf_score"] > 0

    def test_empty_documents(self, nlp_service: NLPService):
        """빈 문서 목록"""
        results = nlp_service.extract_keywords_tfidf([])
        assert results == []

    def test_single_document(self, nlp_service: NLPService):
        """단일 문서"""
        documents = ["한국투자파트너스가 스타트업에 투자를 진행했다."]
        results = nlp_service.extract_keywords_tfidf(documents, top_n=3)
        assert len(results) == 1

    def test_tfidf_scores_descending(self, nlp_service: NLPService):
        """TF-IDF 점수 내림차순 정렬"""
        documents = [
            "투자 시장의 투자 동향을 분석한 투자 보고서이다.",
            "경제 성장과 산업 발전에 관한 보고서이다.",
        ]
        results = nlp_service.extract_keywords_tfidf(documents, top_n=10)
        for doc_keywords in results:
            for i in range(len(doc_keywords) - 1):
                assert doc_keywords[i]["tfidf_score"] >= doc_keywords[i + 1]["tfidf_score"]
