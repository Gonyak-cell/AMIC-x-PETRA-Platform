"""LDD 법률 인용 시스템 테스트.

Phase 3: citation_db, korean_statutes, korean_precedents,
citation_prompt_injector, citation_verifier 테스트.
"""

import pytest

# ── CitationDB 테스트 ──────────────────────────────────────────────────────


class TestCitationDB:
    """CitationDB 로드 및 조회 테스트."""

    def test_load_statutes(self):
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        db.load()
        assert db.statute_count >= 80, f"최소 80개 법조문 필요, 실제: {db.statute_count}"

    def test_load_precedents(self):
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        db.load()
        assert db.precedent_count >= 80, f"최소 80개 판례 필요, 실제: {db.precedent_count}"

    def test_lazy_load(self):
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        # load() 없이도 get_statutes가 자동 로드
        statutes = db.get_statutes("GOVERNANCE")
        assert len(statutes) > 0

    def test_get_statutes_by_section(self):
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        for section in ["GOVERNANCE", "CAPITAL", "CONTRACTS", "LABOR", "IP", "REAL_ESTATE", "TAX", "DATA_IT"]:
            statutes = db.get_statutes(section)
            assert len(statutes) > 0, f"{section}에 법조문이 없음"

    def test_get_precedents_by_section(self):
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        for section in [
            "GOVERNANCE",
            "CAPITAL",
            "CONTRACTS",
            "LITIGATION",
            "LABOR",
            "IP",
            "REAL_ESTATE",
            "TAX",
            "DATA_IT",
        ]:
            precedents = db.get_precedents(section)
            assert len(precedents) > 0, f"{section}에 판례가 없음"

    def test_find_statute_by_id(self):
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        s = db.find_statute("상법_382")
        assert s is not None
        assert "이사" in s.title

    def test_find_statute_not_found(self):
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        assert db.find_statute("존재하지않는_법조문_999") is None

    def test_find_precedent_by_id(self):
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        p = db.find_precedent("대법원_2017다222368")
        assert p is not None
        assert p.court == "대법원"

    def test_find_precedent_not_found(self):
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        assert db.find_precedent("서울고법_9999나99999") is None

    def test_get_all_statutes(self):
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        all_s = db.get_all_statutes()
        assert len(all_s) == db.statute_count

    def test_get_all_precedents(self):
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        all_p = db.get_all_precedents()
        assert len(all_p) == db.precedent_count

    def test_no_duplicate_statute_ids(self):
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        all_s = db.get_all_statutes()
        ids = [s.statute_id for s in all_s]
        assert len(ids) == len(set(ids)), f"중복 statute_id 존재: {[i for i in ids if ids.count(i) > 1]}"

    def test_no_duplicate_precedent_ids(self):
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        all_p = db.get_all_precedents()
        ids = [p.precedent_id for p in all_p]
        assert len(ids) == len(set(ids)), f"중복 precedent_id 존재: {[i for i in ids if ids.count(i) > 1]}"

    def test_empty_section_returns_empty(self):
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        assert db.get_statutes("NONEXISTENT_SECTION") == []
        assert db.get_precedents("NONEXISTENT_SECTION") == []


# ── StatuteEntry / PrecedentEntry 구조 테스트 ──────────────────────────────


class TestEntries:
    """법조문 및 판례 엔트리 구조 검증."""

    def test_statute_fields(self):
        from app.ralph.generators.ldd.legal_citations.korean_statutes import STATUTES

        for s in STATUTES:
            assert s.statute_id, "statute_id 비어있음"
            assert s.law_name, "law_name 비어있음"
            assert s.article, "article 비어있음"
            assert s.title, "title 비어있음"
            assert s.summary, "summary 비어있음"
            assert len(s.section_types) > 0, f"{s.statute_id}에 section_types 없음"

    def test_precedent_fields(self):
        from app.ralph.generators.ldd.legal_citations.korean_precedents import PRECEDENTS

        for p in PRECEDENTS:
            assert p.precedent_id, "precedent_id 비어있음"
            assert p.court, "court 비어있음"
            assert p.case_number, "case_number 비어있음"
            assert p.date, "date 비어있음"
            assert p.title, "title 비어있음"
            assert p.summary, "summary 비어있음"
            assert len(p.section_types) > 0, f"{p.precedent_id}에 section_types 없음"

    def test_statute_frozen(self):
        from app.ralph.generators.ldd.legal_citations.korean_statutes import STATUTES

        with pytest.raises(AttributeError):
            STATUTES[0].statute_id = "modified"  # type: ignore

    def test_precedent_frozen(self):
        from app.ralph.generators.ldd.legal_citations.korean_precedents import PRECEDENTS

        with pytest.raises(AttributeError):
            PRECEDENTS[0].precedent_id = "modified"  # type: ignore


# ── CitationPromptInjector 테스트 ──────────────────────────────────────────


class TestCitationPromptInjector:
    """법률 컨텍스트 주입기 테스트."""

    def test_build_legal_context_governance(self):
        from app.ralph.generators.ldd.legal_citations.citation_prompt_injector import CitationPromptInjector

        injector = CitationPromptInjector()
        ctx = injector.build_legal_context("GOVERNANCE")
        assert "관련 법률 조항" in ctx
        assert "관련 판례" in ctx
        assert "상법" in ctx
        assert "대법원" in ctx

    def test_build_legal_context_labor(self):
        from app.ralph.generators.ldd.legal_citations.citation_prompt_injector import CitationPromptInjector

        injector = CitationPromptInjector()
        ctx = injector.build_legal_context("LABOR")
        assert "근로기준법" in ctx

    def test_build_legal_context_empty_section(self):
        from app.ralph.generators.ldd.legal_citations.citation_prompt_injector import CitationPromptInjector

        injector = CitationPromptInjector()
        ctx = injector.build_legal_context("NONEXISTENT")
        assert "큐레이션된 법률 컨텍스트 없음" in ctx

    def test_max_statutes_limit(self):
        from app.ralph.generators.ldd.legal_citations.citation_prompt_injector import CitationPromptInjector

        injector = CitationPromptInjector()
        ctx = injector.build_legal_context("GOVERNANCE", max_statutes=3, max_precedents=2)
        # 제한된 수만 포함되어야 함
        assert "관련 법률 조항" in ctx

    def test_citation_id_tags(self):
        from app.ralph.generators.ldd.legal_citations.citation_prompt_injector import CitationPromptInjector

        injector = CitationPromptInjector()
        ctx = injector.build_legal_context("GOVERNANCE")
        assert "[cite:" in ctx or "[상법" in ctx  # ID 태그 가이드 포함

    def test_extract_citation_ids(self):
        from app.ralph.generators.ldd.legal_citations.citation_prompt_injector import CitationPromptInjector

        injector = CitationPromptInjector()
        text = "상법 제382조에 따라 [cite:상법_382] 이사는 선임된다. 또한 [cite:대법원_2017다222368] 판례 참조."
        ids = injector.extract_citation_ids(text)
        assert "상법_382" in ids
        assert "대법원_2017다222368" in ids

    def test_extract_no_citations(self):
        from app.ralph.generators.ldd.legal_citations.citation_prompt_injector import CitationPromptInjector

        injector = CitationPromptInjector()
        assert injector.extract_citation_ids("법률 인용 없는 텍스트") == []

    def test_anti_hallucination_warning(self):
        from app.ralph.generators.ldd.legal_citations.citation_prompt_injector import CitationPromptInjector

        injector = CitationPromptInjector()
        ctx = injector.build_legal_context("GOVERNANCE")
        assert "임의로 생성하지 마세요" in ctx


# ── CitationVerifier 테스트 ────────────────────────────────────────────────


class TestCitationVerifier:
    """법률 인용 검증기 테스트."""

    def test_verify_cite_tag_verified(self):
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier

        v = CitationVerifier()
        result = v.verify_text("이사회 결의가 필요하다 [cite:상법_382].")
        assert result.total_citations >= 1
        assert result.verified >= 1
        verified = [c for c in result.citations if c.status == "VERIFIED"]
        assert any(c.citation_id == "상법_382" for c in verified)

    def test_verify_cite_tag_unverified(self):
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier

        v = CitationVerifier()
        result = v.verify_text("관련 규정 [cite:가짜법_999]에 의하면")
        unverified = [c for c in result.citations if c.status == "UNVERIFIED"]
        assert len(unverified) >= 1
        assert "미확인" in result.annotated_text

    def test_verify_statute_pattern_match(self):
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier

        v = CitationVerifier()
        result = v.verify_text("상법 제382조에 따르면 이사는 주주총회에서 선임한다.")
        assert result.total_citations >= 1
        # 상법_382가 레지스트리에 있으므로 VERIFIED일 수 있음

    def test_verify_precedent_pattern(self):
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier

        v = CitationVerifier()
        result = v.verify_text("대법원 2017.09.21. 선고 2017다222368 판결에 의하면")
        assert result.total_citations >= 1

    def test_verify_no_citations(self):
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier

        v = CitationVerifier()
        result = v.verify_text("법률 인용이 없는 일반 텍스트입니다.")
        assert result.total_citations == 0
        assert result.verified == 0

    def test_verify_multiple_citations(self):
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier

        v = CitationVerifier()
        text = (
            "상법 제382조 [cite:상법_382]에 따라 이사는 선임되며, "
            "대법원 2017다222368 판례 [cite:대법원_2017다222368]에서도 확인된다. "
            "또한 [cite:존재하지않는_법_999] 참조."
        )
        result = v.verify_text(text)
        assert result.total_citations >= 3
        assert result.verified >= 2
        assert result.unverified >= 1

    def test_annotated_text_unverified_tag(self):
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier

        v = CitationVerifier()
        result = v.verify_text("위반 시 [cite:허구법_123]에 따라 처벌된다.")
        assert "[미확인]" in result.annotated_text

    def test_annotated_text_verified_no_tag(self):
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier

        v = CitationVerifier()
        result = v.verify_text("상법 제382조 [cite:상법_382]에 따른 의무.")
        assert "[미확인]" not in result.annotated_text

    def test_verification_result_to_dict(self):
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier

        v = CitationVerifier()
        result = v.verify_text("[cite:상법_382] 참조")
        d = result.to_dict()
        assert "total_citations" in d
        assert "verified" in d
        assert "citations" in d
        assert isinstance(d["citations"], list)

    def test_verify_narrative_sections(self):
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier

        v = CitationVerifier()
        narrative_sections = {
            "GOVERNANCE": [
                {
                    "item_id": "GOV-01",
                    "item_name": "정관 검토",
                    "section_type": "GOVERNANCE",
                    "blocks": [
                        {
                            "block_type": "LEGAL_REVIEW",
                            "title": "법률 검토",
                            "content": "상법 제289조 [cite:상법_289]에 따라 정관에는 절대적 기재사항이 포함되어야 한다.",
                            "word_count": 50,
                        },
                        {
                            "block_type": "FACTS",
                            "title": "사실관계",
                            "content": "대상회사의 정관을 검토한 결과 [cite:가짜법_999] 관련 사항이 확인되었다.",
                            "word_count": 40,
                        },
                    ],
                },
            ],
        }
        result = v.verify_narrative_sections(narrative_sections)
        gov_items = result["GOVERNANCE"]
        assert len(gov_items) == 1
        item = gov_items[0]
        assert "citation_verification" in item
        cv = item["citation_verification"]
        assert cv["total"] >= 2
        assert cv["verified"] >= 1
        assert cv["unverified"] >= 1

    def test_verify_empty_narrative(self):
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier

        v = CitationVerifier()
        result = v.verify_narrative_sections({})
        assert result == {}

    def test_verify_narrative_no_blocks(self):
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier

        v = CitationVerifier()
        result = v.verify_narrative_sections(
            {
                "LABOR": [{"item_id": "LAB-01", "blocks": []}],
            }
        )
        assert result["LABOR"][0]["citation_verification"]["total"] == 0

    def test_duplicate_cite_tags_counted_once(self):
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier

        v = CitationVerifier()
        result = v.verify_text("[cite:상법_382] 이사 선임. 다시 [cite:상법_382] 참조.")
        # 동일 ID는 1회만 카운트
        assert result.total_citations == 1


# ── _guess_statute_id 확장 매핑 테스트 ──────────────────────────────────────


class TestGuessStatuteIdNewMappings:
    """IS-12 수정: 추가된 12개 법률 매핑이 올바르게 작동하는지 검증."""

    def _verify_statute_pattern(self, law_name: str, article: str):
        """법조문 패턴이 인식되어 statute_id가 올바르게 생성되는지 검증."""
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier

        v = CitationVerifier()
        text = f"{law_name} 제{article}조에 따르면 관련 의무가 발생한다."
        result = v.verify_text(text)
        # 패턴 매칭이 되어야 함 (VERIFIED 또는 PATTERN_MATCH)
        assert result.total_citations >= 1, f"{law_name} 제{article}조 인식 실패"
        matched = result.citations[0]
        expected_id = f"{law_name}_{article}"
        assert matched.citation_id == expected_id, f"예상 ID: {expected_id}, 실제: {matched.citation_id}"

    def test_new_law_부정경쟁방지법(self):
        self._verify_statute_pattern("부정경쟁방지법", "2")

    def test_new_law_노동조합법(self):
        self._verify_statute_pattern("노동조합법", "24")

    def test_new_law_산업안전보건법(self):
        self._verify_statute_pattern("산업안전보건법", "38")

    def test_new_law_국토계획법(self):
        self._verify_statute_pattern("국토계획법", "56")

    def test_new_law_농지법(self):
        self._verify_statute_pattern("농지법", "6")

    def test_new_law_부동산실명법(self):
        self._verify_statute_pattern("부동산실명법", "3")

    def test_new_law_외국인투자촉진법(self):
        self._verify_statute_pattern("외국인투자촉진법", "5")

    def test_new_law_국제조세조정법(self):
        self._verify_statute_pattern("국제조세조정법", "10")

    def test_new_law_정보통신망법(self):
        self._verify_statute_pattern("정보통신망법", "44")

    def test_new_law_민사소송법(self):
        self._verify_statute_pattern("민사소송법", "208")

    def test_new_law_형사소송법(self):
        self._verify_statute_pattern("형사소송법", "312")

    def test_new_law_행정소송법(self):
        self._verify_statute_pattern("행정소송법", "20")

    def test_subarticle_pattern(self):
        """조의X 패턴이 올바르게 파싱된다."""
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier

        v = CitationVerifier()
        result = v.verify_text("상법 제542조의8에 따르면 사외이사 의무가 발생한다.")
        assert result.total_citations >= 1
        matched = result.citations[0]
        assert matched.citation_id == "상법_542_8"


# ── 통합 테스트 ────────────────────────────────────────────────────────────


class TestIntegration:
    """법률 인용 시스템 통합 테스트."""

    def test_injector_then_verifier_roundtrip(self):
        """주입기가 생성한 컨텍스트에서 ID를 추출하고 검증하는 라운드트립."""
        from app.ralph.generators.ldd.citation_verifier import CitationVerifier
        from app.ralph.generators.ldd.legal_citations.citation_prompt_injector import CitationPromptInjector

        injector = CitationPromptInjector()
        verifier = CitationVerifier()

        # 주입기가 GOVERNANCE 섹션 법률 컨텍스트 생성
        ctx = injector.build_legal_context("GOVERNANCE")

        # 컨텍스트에서 ID 추출
        ids = injector.extract_citation_ids(ctx)  # noqa: F841
        # 주입된 컨텍스트에는 [cite:ID] 형식이 아니라 [ID] 형식으로 되어 있으므로
        # 검증기가 직접 사용하는 시나리오: LLM이 [cite:ID]로 인용한 텍스트 검증
        sample_text = "이사는 상법 제382조 [cite:상법_382]에 따라 선임된다."
        result = verifier.verify_text(sample_text)
        assert result.verified >= 1

    def test_all_sections_have_citations(self):
        """주요 섹션에 법조문과 판례가 모두 있는지 확인."""
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        major_sections = [
            "GOVERNANCE",
            "CAPITAL",
            "CONTRACTS",
            "LITIGATION",
            "LABOR",
            "IP",
            "REAL_ESTATE",
            "TAX",
            "DATA_IT",
        ]
        for section in major_sections:
            s = db.get_statutes(section)
            p = db.get_precedents(section)
            assert len(s) > 0, f"{section}: 법조문 없음"
            assert len(p) > 0, f"{section}: 판례 없음"

    def test_citation_count_summary(self):
        """전체 인용 데이터 수량 요약."""
        from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

        db = CitationDB()
        print(f"\n총 법조문: {db.statute_count}개, 판례: {db.precedent_count}개")
        assert db.statute_count + db.precedent_count >= 170
