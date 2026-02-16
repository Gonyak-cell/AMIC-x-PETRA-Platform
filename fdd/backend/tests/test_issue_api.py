"""Issue API 테스트 — Sprint 6."""

from datetime import date
from decimal import Decimal

import pytest

from app.models.deal import Deal, DealType, DealStatus
from app.models.issue import Issue, IssueCategory, IssueSeverity, IssueStatus


@pytest.fixture
def sample_deal(db):
    """샘플 Deal."""
    deal = Deal(
        name="Test Deal for Issues",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency="KRW",
        reference_date=date(2025, 12, 31),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        status=DealStatus.ACTIVE,
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


@pytest.fixture
def sample_issues(db, sample_deal):
    """샘플 Issue 여러 개."""
    issues = [
        Issue(
            deal_id=sample_deal.id,
            category=IssueCategory.ANOMALY,
            severity=IssueSeverity.HIGH,
            status=IssueStatus.OPEN,
            title="High Risk Anomaly",
            description="연말 대규모 전표",
            risk_score=Decimal("75.00"),
            detection_method="zscore",
        ),
        Issue(
            deal_id=sample_deal.id,
            category=IssueCategory.DATA_QUALITY,
            severity=IssueSeverity.MEDIUM,
            status=IssueStatus.OPEN,
            title="Data Quality Issue",
            description="중복 전표 의심",
            detection_method="manual",
        ),
        Issue(
            deal_id=sample_deal.id,
            category=IssueCategory.ANOMALY,
            severity=IssueSeverity.LOW,
            status=IssueStatus.RESOLVED,
            title="Resolved Issue",
            description="해결된 이슈",
            detection_method="keyword",
        ),
    ]
    for issue in issues:
        db.add(issue)
    db.commit()
    for issue in issues:
        db.refresh(issue)
    return issues


class TestIssueListAPI:
    """Issue 목록 조회 API 테스트."""

    def test_list_issues_empty(self, client, sample_deal):
        """이슈 없을 때 빈 목록 반환."""
        response = client.get(f"/api/v1/deals/{sample_deal.id}/issues")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_issues_with_data(self, client, sample_deal, sample_issues):
        """이슈 목록 조회."""
        response = client.get(f"/api/v1/deals/{sample_deal.id}/issues")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_list_issues_filter_severity(self, client, sample_deal, sample_issues):
        """심각도 필터."""
        response = client.get(
            f"/api/v1/deals/{sample_deal.id}/issues",
            params={"severity": "HIGH"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["severity"] == "HIGH"

    def test_list_issues_filter_status(self, client, sample_deal, sample_issues):
        """상태 필터."""
        response = client.get(
            f"/api/v1/deals/{sample_deal.id}/issues",
            params={"status": "OPEN"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_list_issues_filter_category(self, client, sample_deal, sample_issues):
        """카테고리 필터."""
        response = client.get(
            f"/api/v1/deals/{sample_deal.id}/issues",
            params={"category": "ANOMALY"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_list_issues_pagination(self, client, sample_deal, sample_issues):
        """페이지네이션."""
        response = client.get(
            f"/api/v1/deals/{sample_deal.id}/issues",
            params={"limit": 1, "offset": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 1
        assert data["limit"] == 1
        assert data["offset"] == 0


class TestIssueDetailAPI:
    """Issue 상세 조회 API 테스트."""

    def test_get_issue_success(self, client, sample_deal, sample_issues):
        """이슈 상세 조회 성공."""
        issue = sample_issues[0]
        response = client.get(f"/api/v1/deals/{sample_deal.id}/issues/{issue.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == issue.title
        assert data["category"] == issue.category.value

    def test_get_issue_not_found(self, client, sample_deal):
        """존재하지 않는 이슈."""
        import uuid

        fake_id = uuid.uuid4()
        response = client.get(f"/api/v1/deals/{sample_deal.id}/issues/{fake_id}")
        assert response.status_code == 404


class TestIssueCreateAPI:
    """Issue 생성 API 테스트."""

    def test_create_issue_success(self, client, sample_deal):
        """수동 이슈 생성 성공."""
        payload = {
            "category": "DATA_QUALITY",
            "severity": "MEDIUM",
            "title": "New Manual Issue",
            "description": "수동으로 생성한 이슈입니다.",
        }
        response = client.post(
            f"/api/v1/deals/{sample_deal.id}/issues",
            json=payload,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Manual Issue"
        assert data["status"] == "OPEN"
        assert data["detection_method"] == "manual"

    def test_create_issue_with_source(self, client, sample_deal):
        """소스 정보 포함 이슈 생성."""
        payload = {
            "category": "ANOMALY",
            "severity": "HIGH",
            "title": "Issue with Source",
            "description": "소스 정보 포함",
            "source_type": "GL",
            "source_id": "GL-12345",
            "source_detail": {"amount": "1000000"},
        }
        response = client.post(
            f"/api/v1/deals/{sample_deal.id}/issues",
            json=payload,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["source_type"] == "GL"
        assert data["source_id"] == "GL-12345"


class TestIssueUpdateAPI:
    """Issue 상태 변경 API 테스트."""

    def test_update_issue_status(self, client, sample_deal, sample_issues):
        """이슈 상태 변경."""
        issue = sample_issues[0]
        payload = {
            "status": "RESOLVED",
            "resolution_note": "확인 결과 정상 전표",
            "resolved_by": "analyst@company.com",
        }
        response = client.put(
            f"/api/v1/deals/{sample_deal.id}/issues/{issue.id}",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "RESOLVED"
        assert data["resolution_note"] == "확인 결과 정상 전표"
        assert data["resolved_at"] is not None

    def test_update_issue_false_positive(self, client, sample_deal, sample_issues):
        """오탐으로 마킹."""
        issue = sample_issues[0]
        payload = {
            "status": "FALSE_POSITIVE",
            "resolution_note": "오탐으로 확인됨",
        }
        response = client.put(
            f"/api/v1/deals/{sample_deal.id}/issues/{issue.id}",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FALSE_POSITIVE"


class TestIssueSummaryAPI:
    """Issue 요약 API 테스트."""

    def test_get_summary(self, client, sample_deal, sample_issues):
        """이슈 요약 조회."""
        response = client.get(f"/api/v1/deals/{sample_deal.id}/issues/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert "by_severity" in data
        assert "by_status" in data
        assert "by_category" in data

    def test_summary_empty_deal(self, client, sample_deal):
        """이슈 없는 Deal 요약."""
        response = client.get(f"/api/v1/deals/{sample_deal.id}/issues/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestAnomalyDetectionAPI:
    """이상치 탐지 API 테스트."""

    def test_detect_anomalies_no_entries(self, client, sample_deal):
        """GL 전표 없을 때."""
        payload = {"threshold": "50.0"}
        response = client.post(
            f"/api/v1/deals/{sample_deal.id}/issues/detect-anomalies",
            json=payload,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["detected_count"] == 0
        assert data["issues_created"] == 0
        assert "engine_version" in data
