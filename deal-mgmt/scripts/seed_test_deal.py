"""수동 검증용 시드 스크립트 — 각 단계 gate 충족 데이터 일괄 생성.

Usage:
    # 기본: 전체 8단계를 순차 진행하면서 시드 데이터 생성
    python scripts/seed_test_deal.py

    # 특정 단계까지만 진행
    python scripts/seed_test_deal.py --target BIDDING

    # 기존 거래에 시드 데이터 추가 (이미 생성된 거래 ID)
    python scripts/seed_test_deal.py --txn-id <uuid>

환경변수:
    API_BASE_URL: API 서버 주소 (기본: http://localhost:8003)
    JWT_TOKEN: 인증 토큰 (미설정 시 로컬 개발 모드)
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.request import Request, urlopen

# ── 설정 ──────────────────────────────────────────────────────
DEFAULT_BASE_URL = "http://localhost:8003"

PHASE_ORDER = [
    "ENGAGEMENT",
    "PREPARATION",
    "MARKETING",
    "BIDDING",
    "MAIN_DUE_DILIGENCE",
    "NEGOTIATION",
    "CLOSING",
    "POST_CLOSING",
]

FULL_TXN = {
    "name": "시드 테스트 딜 (자동 생성)",
    "deal_type": "SE",
    "side": "SELL",
    "target_company_name": "시드 대상기업 주식회사",
    "client_name": "시드 의뢰기업",
    "lead_advisor_email": "advisor@example.com",
    "deal_captain_email": "captain@example.com",
    "industry": "Technology",
    "deal_structure": "SHARE_ACQUISITION",
    "estimated_deal_value": 50_000_000_000,
}


# ── HTTP 유틸 ────────────────────────────────────────────────


def _api(
    method: str,
    path: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    token: str | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any]:
    """urllib 기반 API 호출. 외부 의존성 없이 동작."""
    url = f"{base_url}{path}"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, headers=headers, method=method)

    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        print(f"  ✗ {method} {path} → {exc}")
        raise


def _post(path: str, body: dict[str, Any], **kw: Any) -> dict[str, Any] | list[Any]:
    return _api("POST", path, body=body, **kw)


def _get(path: str, **kw: Any) -> dict[str, Any] | list[Any]:
    return _api("GET", path, **kw)


def _patch(path: str, body: dict[str, Any], **kw: Any) -> dict[str, Any] | list[Any]:
    return _api("PATCH", path, body=body, **kw)


# ── 시드 함수들 ──────────────────────────────────────────────


def create_transaction(base_url: str, token: str | None) -> str:
    """거래 생성 + ACTIVE 전환."""
    print("\n=== 거래 생성 ===")
    result = _post("/api/v1/transactions", FULL_TXN, base_url=base_url, token=token)
    txn_id = result["id"]  # type: ignore[index]
    print(f"  ✓ Transaction 생성: {txn_id}")

    _post(
        f"/api/v1/transactions/{txn_id}/workflow/status",
        {"to_status": "ACTIVE"},
        base_url=base_url,
        token=token,
    )
    print("  ✓ DRAFT → ACTIVE 전환")
    return txn_id


def seed_bidding_gate(txn_id: str, base_url: str, token: str | None) -> str:
    """BIDDING 진입: Short List buyer + NDA 체결."""
    print("\n--- BIDDING 게이트 시드 ---")

    # 전략적 매수자 3명 추가
    buyer_ids: list[str] = []
    for i, name in enumerate(["알파 캐피탈", "베타 인더스트리", "감마 홀딩스"], 1):
        buyer_type = "STRATEGIC" if i <= 2 else "FINANCIAL_SPONSOR"
        tier = "TIER_1" if i <= 2 else "TIER_2"
        result = _post(
            f"/api/v1/transactions/{txn_id}/buyers",
            {"company_name": name, "buyer_type": buyer_type, "tier": tier},
            base_url=base_url,
            token=token,
        )
        bid = result["id"]  # type: ignore[index]
        buyer_ids.append(bid)
        print(f"  ✓ 매수자 생성: {name} ({buyer_type}, {tier})")

    # 처음 2명 NDA 체결
    for bid in buyer_ids[:2]:
        _patch(
            f"/api/v1/transactions/{txn_id}/buyers/{bid}",
            {"status": "CONTACTED"},
            base_url=base_url,
            token=token,
        )
        _patch(
            f"/api/v1/transactions/{txn_id}/buyers/{bid}",
            {"status": "NDA_SIGNED"},
            base_url=base_url,
            token=token,
        )
    print(f"  ✓ NDA 체결: {buyer_ids[0]}, {buyer_ids[1]}")

    return buyer_ids[0]  # 첫 번째 buyer 반환 (이후 bid 생성용)


def seed_dd_gate(txn_id: str, buyer_id: str, base_url: str, token: str | None) -> None:
    """MAIN_DUE_DILIGENCE 진입: IOI 입찰 생성."""
    print("\n--- MAIN_DD 게이트 시드 ---")
    _post(
        f"/api/v1/transactions/{txn_id}/bids",
        {
            "buyer_candidate_id": buyer_id,
            "bid_type": "IOI",
            "amount": 50_000_000_000,
            "valuation_method": "EV_EBITDA",
            "multiple": 8.5,
            "conditions": "실사 완료 조건부",
        },
        base_url=base_url,
        token=token,
    )
    print("  ✓ IOI 입찰 생성: 500억원 (EV/EBITDA 8.5x)")


def seed_negotiation_gate(txn_id: str, base_url: str, token: str | None) -> None:
    """NEGOTIATION 진입: DD 체크리스트 생성 + 완료."""
    print("\n--- NEGOTIATION 게이트 시드 ---")

    dd_items = [
        ("FDD_FINANCIAL_STATEMENTS", "재무제표 분석"),
        ("FDD_TAX", "세무 검토"),
        ("LDD_CORPORATE", "법인 구조 검토"),
        ("TDD_CORPORATE_TAX", "법인세 검토"),
    ]

    for workstream, title in dd_items:
        result = _post(
            f"/api/v1/transactions/{txn_id}/dd-checklist",
            {"workstream": workstream, "title": title},
            base_url=base_url,
            token=token,
        )
        item_id = result["id"]  # type: ignore[index]
        _patch(
            f"/api/v1/transactions/{txn_id}/dd-checklist/{item_id}",
            {"status": "COMPLETED"},
            base_url=base_url,
            token=token,
        )
        print(f"  ✓ DD 완료: {title}")

    print("  ✓ DD 완료율: 4/4 (100%)")


def seed_closing_gate(txn_id: str, base_url: str, token: str | None) -> None:
    """CLOSING 진입: SPA 계약 + Closing 체크리스트 전체 COMPLETED."""
    print("\n--- CLOSING 게이트 시드 ---")

    # SPA 계약 생성
    _post(
        f"/api/v1/transactions/{txn_id}/contracts",
        {
            "contract_type": "SPA",
            "title": "주식양수도계약서 최종본",
            "counterparty_name": "알파 캐피탈",
        },
        base_url=base_url,
        token=token,
    )
    print("  ✓ SPA 계약 생성")

    # 부트스트랩 Closing 체크리스트 전체 COMPLETED
    items = _get(f"/api/v1/transactions/{txn_id}/closing", base_url=base_url, token=token)
    completed = 0
    for item in items:  # type: ignore[union-attr]
        if item["status"] != "COMPLETED":  # type: ignore[index]
            _patch(
                f"/api/v1/transactions/{txn_id}/closing/{item['id']}",  # type: ignore[index]
                {"status": "COMPLETED"},
                base_url=base_url,
                token=token,
            )
            completed += 1
    print(f"  ✓ Closing 체크리스트 {completed}건 COMPLETED 처리")


def advance_phase(txn_id: str, to_phase: str, base_url: str, token: str | None) -> None:
    """단계 전환."""
    result = _post(
        f"/api/v1/transactions/{txn_id}/workflow/advance",
        {"to_phase": to_phase},
        base_url=base_url,
        token=token,
    )
    print(f"  ✓ → {result['phase']} 전환 성공")  # type: ignore[index]


# ── 메인 ─────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="MA 워크플로우 시드 스크립트")
    parser.add_argument("--target", default="POST_CLOSING", choices=PHASE_ORDER, help="목표 단계")
    parser.add_argument("--txn-id", default=None, help="기존 거래 ID (미설정 시 새로 생성)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API 서버 주소")
    parser.add_argument("--token", default=None, help="JWT 토큰")
    args = parser.parse_args()

    target_idx = PHASE_ORDER.index(args.target)

    # 거래 생성 또는 기존 ID 사용
    if args.txn_id:
        txn_id = args.txn_id
        print(f"\n=== 기존 거래 사용: {txn_id} ===")
    else:
        txn_id = create_transaction(args.base_url, args.token)

    buyer_id: str | None = None

    # 순차 진행
    current_idx = 0  # ENGAGEMENT
    while current_idx < target_idx:
        next_phase = PHASE_ORDER[current_idx + 1]
        next_idx = current_idx + 1

        print(f"\n{'=' * 50}")
        print(f"  {PHASE_ORDER[current_idx]} → {next_phase}")
        print(f"{'=' * 50}")

        # 게이트 시드 데이터
        if next_phase == "BIDDING":
            buyer_id = seed_bidding_gate(txn_id, args.base_url, args.token)
        elif next_phase == "MAIN_DUE_DILIGENCE":
            if buyer_id is None:
                print("  ⚠ buyer_id 없음 — BIDDING 시드 필요")
                sys.exit(1)
            seed_dd_gate(txn_id, buyer_id, args.base_url, args.token)
        elif next_phase == "NEGOTIATION":
            seed_negotiation_gate(txn_id, args.base_url, args.token)
        elif next_phase == "CLOSING":
            seed_closing_gate(txn_id, args.base_url, args.token)

        advance_phase(txn_id, next_phase, args.base_url, args.token)
        current_idx = next_idx

    print(f"\n{'=' * 50}")
    print(f"  ✅ 시드 완료: {PHASE_ORDER[current_idx]} 단계 도달")
    print(f"  Transaction ID: {txn_id}")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    main()
