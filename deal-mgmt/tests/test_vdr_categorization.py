"""VDR 자동 분류 서비스 순수 함수 단위 테스트 (DB 없음)."""

from __future__ import annotations

import pytest

from app.models.enums import VdrFolderCategory
from app.services.vdr_categorization_service import auto_route, score_document, suggest_category

# ── score_document ────────────────────────────────────────────


class TestScoreDocument:
    def test_score_financial_xlsx_returns_high_score(self) -> None:
        """재무제표.xlsx → FINANCIAL 80점 이상."""
        scores = score_document(
            filename="재무제표_2024.xlsx",
            extension=".xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_size_bytes=512_000,
        )
        assert len(scores) > 0
        top_cat, top_score = scores[0]
        assert top_cat == VdrFolderCategory.FINANCIAL
        assert top_score >= 80  # 키워드 60 + 확장자 20

    def test_score_tax_hwp_matched(self) -> None:
        """.hwp 파일은 TAX 카테고리에 확장자 점수 부여."""
        scores = score_document(
            filename="세무조사결과.hwp",
            extension=".hwp",
            mime_type="application/haansofthwp",
            file_size_bytes=50_000,
        )
        score_map = dict(scores)
        assert VdrFolderCategory.TAX in score_map
        assert score_map[VdrFolderCategory.TAX] >= 80

    def test_score_regex_ip_patent_number(self) -> None:
        """출원번호 패턴이 파일명에 있으면 IP 카테고리 정규식 점수 부여."""
        scores = score_document(
            filename="특허출원_10-2024-0123456.pdf",
            extension=".pdf",
            mime_type="application/pdf",
            file_size_bytes=100_000,
        )
        score_map = dict(scores)
        assert VdrFolderCategory.IP in score_map
        # 키워드 60 + 정규식 20 = 80점 이상
        assert score_map[VdrFolderCategory.IP] >= 80

    def test_score_excludes_zero_scores(self) -> None:
        """점수가 0인 카테고리는 결과에서 제외된다."""
        scores = score_document(
            filename="unknown_random_file.pdf",
            extension=".pdf",
            mime_type="application/pdf",
            file_size_bytes=1_000,
        )
        for _, score in scores:
            assert score > 0

    def test_score_descending_order(self) -> None:
        """결과는 내림차순으로 정렬되어야 한다."""
        scores = score_document(
            filename="재무상태표_세금계산서.xlsx",
            extension=".xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_size_bytes=200_000,
        )
        if len(scores) >= 2:
            for i in range(len(scores) - 1):
                assert scores[i][1] >= scores[i + 1][1]

    def test_score_corporate_regex_bizno(self) -> None:
        """사업자등록번호 패턴 → CORPORATE 정규식 점수."""
        scores = score_document(
            filename="123-45-67890_법인등록.pdf",
            extension=".pdf",
            mime_type="application/pdf",
            file_size_bytes=50_000,
        )
        score_map = dict(scores)
        assert VdrFolderCategory.CORPORATE in score_map

    def test_score_dwg_routes_to_real_estate(self) -> None:
        """.dwg 파일은 REAL_ESTATE 카테고리에 확장자 점수 부여."""
        scores = score_document(
            filename="건축도면.dwg",
            extension=".dwg",
            mime_type="image/vnd.dwg",
            file_size_bytes=5_000_000,
        )
        score_map = dict(scores)
        assert VdrFolderCategory.REAL_ESTATE in score_map
        assert score_map[VdrFolderCategory.REAL_ESTATE] >= 20


# ── auto_route ────────────────────────────────────────────────


class TestAutoRoute:
    def test_auto_route_financial_xlsx(self) -> None:
        """재무제표.xlsx → FINANCIAL."""
        result = auto_route(
            "재무제표.xlsx", ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 0
        )
        assert result == VdrFolderCategory.FINANCIAL

    def test_auto_route_tiebreak_group1_wins_over_group3(self) -> None:
        """조직도 키워드 → HR(Group 1) > CORPORATE(Group 3) 우선."""
        result = auto_route("조직도_2024.pdf", ".pdf", "application/pdf", 0)
        # HR이 CORPORATE보다 우선 (tiebreak_group 1 < 3)
        assert result == VdrFolderCategory.HR

    def test_auto_route_no_match_returns_none(self) -> None:
        """매칭되지 않는 파일은 None 반환."""
        result = auto_route("aaabbbccc_xyz_random.pdf", ".pdf", "application/pdf", 0)
        assert result is None

    def test_auto_route_ip_patent(self) -> None:
        """특허 키워드 → IP."""
        result = auto_route("특허출원서.pdf", ".pdf", "application/pdf", 0)
        assert result == VdrFolderCategory.IP

    def test_auto_route_environment_esg(self) -> None:
        """ESG 키워드 → ENVIRONMENT."""
        result = auto_route("ESG_보고서_2024.pdf", ".pdf", "application/pdf", 0)
        assert result == VdrFolderCategory.ENVIRONMENT

    def test_auto_route_hr_payroll(self) -> None:
        """Payroll 키워드 → HR."""
        result = auto_route(
            "Payroll_202412.xlsx", ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 0
        )
        assert result == VdrFolderCategory.HR

    def test_auto_route_legal_eml(self) -> None:
        """.eml 파일 → LEGAL 카테고리에 확장자 점수."""
        result = auto_route("agreement_draft.eml", ".eml", "message/rfc822", 0)
        # agreement 키워드 + .eml 확장자 → LEGAL
        assert result == VdrFolderCategory.LEGAL

    def test_auto_route_hwp_tax(self) -> None:
        """.hwp + 세무 키워드 → TAX."""
        result = auto_route("납세증명서.hwp", ".hwp", "application/haansofthwp", 0)
        assert result == VdrFolderCategory.TAX


# ── suggest_category (하위 호환 래퍼) ────────────────────────


class TestSuggestCategory:
    def test_suggest_category_backward_compat_financial(self) -> None:
        """기존 API: 파일명만으로 FINANCIAL 추천."""
        result = suggest_category("재무제표.xlsx")
        assert result == VdrFolderCategory.FINANCIAL

    def test_suggest_category_backward_compat_none(self) -> None:
        """기존 API: 매칭 없으면 None 반환."""
        result = suggest_category("xyz_random_doc.pdf")
        assert result is None

    def test_suggest_category_corporate(self) -> None:
        """사업자등록증 → CORPORATE."""
        result = suggest_category("사업자등록증.pdf")
        assert result == VdrFolderCategory.CORPORATE

    def test_suggest_category_insurance(self) -> None:
        """보험 관련 파일 → INSURANCE."""
        result = suggest_category("화재보험계약서.pdf")
        assert result == VdrFolderCategory.INSURANCE


# ── 엣지 케이스 ────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_filename_does_not_crash(self) -> None:
        """빈 파일명이라도 None 반환 (예외 없음)."""
        result = auto_route("", "", "application/pdf", 0)
        assert result is None

    def test_case_insensitive_keyword_matching(self) -> None:
        """키워드 대소문자 무관 매칭."""
        result_lower = auto_route("financial_report.pdf", ".pdf", "application/pdf", 0)
        result_upper = auto_route("FINANCIAL_REPORT.pdf", ".pdf", "application/pdf", 0)
        assert result_lower == result_upper == VdrFolderCategory.FINANCIAL

    def test_multiple_categories_all_scored(self) -> None:
        """여러 카테고리 키워드가 있으면 각각 점수 부여."""
        # "재무" + "세무" 둘 다 포함 → FINANCIAL, TAX 모두 점수
        scores = score_document(
            filename="재무세무통합자료.xlsx",
            extension=".xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_size_bytes=0,
        )
        score_map = dict(scores)
        assert VdrFolderCategory.FINANCIAL in score_map
        assert VdrFolderCategory.TAX in score_map

    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("급여대장_2024.xlsx", VdrFolderCategory.HR),
            ("단체협약서.docx", VdrFolderCategory.HR),
            ("토지대장.pdf", VdrFolderCategory.REAL_ESTATE),
            ("배출시설현황.pdf", VdrFolderCategory.ENVIRONMENT),
            ("산재보험증서.pdf", VdrFolderCategory.INSURANCE),
            ("사업계획서.pptx", VdrFolderCategory.COMMERCIAL),
        ],
    )
    def test_parametrized_keyword_routing(self, filename: str, expected: VdrFolderCategory) -> None:
        """다양한 키워드 → 기대 카테고리 매핑."""
        ext = "." + filename.rsplit(".", 1)[-1]
        result = auto_route(filename, ext, "application/octet-stream", 0)
        assert result == expected
