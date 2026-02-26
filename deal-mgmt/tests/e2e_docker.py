"""E2E Docker test — full MA workflow lifecycle with Risk/Compliance gates."""

from datetime import UTC, datetime, timedelta

import httpx
from jose import jwt

SECRET = "dev-shared-jwt-secret-change-in-production"
token = jwt.encode(
    {
        "sub": "test-user-001",
        "email": "tester@example.com",
        "name": "E2E Tester",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    },
    SECRET,
    algorithm="HS256",
)

BASE = "http://localhost:8000/api/v1"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

passed = 0
failed = 0


def check(label, resp, expected_status):
    global passed, failed
    ok = resp.status_code == expected_status
    mark = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"  [{mark}] {label}: {resp.status_code} (expected {expected_status})")
    if not ok:
        print(f"    Body: {resp.text[:200]}")
    return ok


# 1. Create Transaction
print("=== 1. Create Transaction ===")
resp = httpx.post(
    f"{BASE}/transactions",
    headers=headers,
    json={
        "name": "E2E 테스트 딜",
        "code_name": "E2E-001",
        "side": "SELL",
        "target_company_name": "테스트기업",
        "client_name": "의뢰기업",
        "lead_advisor_email": "advisor@example.com",
        "industry": "제조업",
        "deal_structure": "M&A",
        "estimated_deal_value": 100000000,
    },
)
check("Create Transaction", resp, 201)
txn = resp.json()
txn_id = txn["id"]
print(f"  Phase: {txn['phase']}, Status: {txn['status']}")

# 2. List Transactions
print("\n=== 2. List Transactions ===")
resp = httpx.get(f"{BASE}/transactions", headers=headers)
check("List Transactions", resp, 200)
print(f"  Total: {resp.json()['total']}")

# 3. Status: DRAFT -> ACTIVE
print("\n=== 3. Status DRAFT -> ACTIVE ===")
resp = httpx.post(
    f"{BASE}/transactions/{txn_id}/workflow/status",
    headers=headers,
    json={"to_status": "ACTIVE", "reason": "E2E Test"},
)
check("DRAFT -> ACTIVE", resp, 200)

# 4-7. Advance through phases
for step, (from_p, to_p) in enumerate(
    [
        ("ENGAGEMENT", "PREPARATION"),
        ("PREPARATION", "MARKETING"),
        ("MARKETING", "BIDDING_DD"),
        ("BIDDING_DD", "NEGOTIATION"),
    ],
    start=4,
):
    print(f"\n=== {step}. Advance {from_p} -> {to_p} ===")
    resp = httpx.post(
        f"{BASE}/transactions/{txn_id}/workflow/advance",
        headers=headers,
        json={"to_phase": to_p},
    )
    check(f"{from_p} -> {to_p}", resp, 200)
    if resp.status_code == 200:
        print(f"  New Phase: {resp.json()['phase']}")

# 8. Create Critical Risk
print("\n=== 8. Create Risk Item (CRITICAL) ===")
resp = httpx.post(
    f"{BASE}/transactions/{txn_id}/risks",
    headers=headers,
    json={
        "category": "REGULATORY",
        "title": "FTC 승인 필요",
        "severity": "CRITICAL",
        "likelihood": "HIGH",
    },
)
check("Create Critical Risk", resp, 201)
risk_id = resp.json()["id"]

# 9. Try CLOSING (should FAIL)
print("\n=== 9. Advance NEGOTIATION -> CLOSING (expect BLOCKED) ===")
resp = httpx.post(
    f"{BASE}/transactions/{txn_id}/workflow/advance",
    headers=headers,
    json={"to_phase": "CLOSING"},
)
check("CLOSING blocked by risk", resp, 422)

# 10. Mitigate Risk
print("\n=== 10. Mitigate Critical Risk ===")
resp = httpx.patch(
    f"{BASE}/transactions/{txn_id}/risks/{risk_id}",
    headers=headers,
    json={"status": "MITIGATED", "mitigation_strategy": "FTC 사전 합의 완료"},
)
check("Mitigate Risk", resp, 200)

# 11. Create NON_COMPLIANT item
print("\n=== 11. Create Compliance Item -> NON_COMPLIANT ===")
resp = httpx.post(
    f"{BASE}/transactions/{txn_id}/compliance",
    headers=headers,
    json={"category": "ANTITRUST", "requirement": "공정위 기업결합 신고"},
)
check("Create Compliance", resp, 201)
comp_id = resp.json()["id"]

resp = httpx.patch(
    f"{BASE}/transactions/{txn_id}/compliance/{comp_id}",
    headers=headers,
    json={"status": "NON_COMPLIANT"},
)
check("Mark NON_COMPLIANT", resp, 200)

# 12. Try CLOSING (should FAIL)
print("\n=== 12. Advance NEGOTIATION -> CLOSING (expect BLOCKED) ===")
resp = httpx.post(
    f"{BASE}/transactions/{txn_id}/workflow/advance",
    headers=headers,
    json={"to_phase": "CLOSING"},
)
check("CLOSING blocked by compliance", resp, 422)

# 13. Resolve Compliance
print("\n=== 13. Resolve Compliance ===")
resp = httpx.patch(
    f"{BASE}/transactions/{txn_id}/compliance/{comp_id}",
    headers=headers,
    json={"status": "APPROVED"},
)
check("Resolve Compliance", resp, 200)

# 14. Advance to CLOSING (should SUCCEED)
print("\n=== 14. Advance NEGOTIATION -> CLOSING (expect SUCCESS) ===")
resp = httpx.post(
    f"{BASE}/transactions/{txn_id}/workflow/advance",
    headers=headers,
    json={"to_phase": "CLOSING"},
)
check("NEGOTIATION -> CLOSING", resp, 200)
if resp.status_code == 200:
    print(f"  New Phase: {resp.json()['phase']}")

# 15. Dashboard Stats
print("\n=== 15. Dashboard Stats ===")
resp = httpx.get(f"{BASE}/dashboard/stats", headers=headers)
check("Dashboard Stats", resp, 200)

# 16. Risk Summary
print("\n=== 16. Risk Summary ===")
resp = httpx.get(f"{BASE}/transactions/{txn_id}/risks/summary", headers=headers)
check("Risk Summary", resp, 200)
if resp.status_code == 200:
    s = resp.json()
    print(f"  Total: {s['total']}, Critical: {s.get('critical_count', 0)}")

# 17. Compliance Summary
print("\n=== 17. Compliance Summary ===")
resp = httpx.get(f"{BASE}/transactions/{txn_id}/compliance/summary", headers=headers)
check("Compliance Summary", resp, 200)
if resp.status_code == 200:
    s = resp.json()
    print(f"  Total: {s['total']}, Rate: {s.get('compliance_rate', 'N/A')}%")

# Final
print(f"\n{'=' * 50}")
print(f"E2E RESULT: {passed} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED!")
else:
    print("SOME TESTS FAILED!")
    exit(1)
