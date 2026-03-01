"""감사 로그 직렬화 단위 테스트 — _json_safe / _sanitize_for_json."""

from __future__ import annotations

import enum
import json
import uuid
from datetime import date, datetime
from decimal import Decimal

from app.services.audit_service import _json_safe, _sanitize_for_json

# ── 테스트용 Enum ────────────────────────────────────────


class _SampleEnum(enum.StrEnum):
    ALPHA = "ALPHA"
    BETA = "BETA"


class _PlainEnum(enum.Enum):
    X = 1
    Y = "hello"


# ── _json_safe 단위 테스트 ───────────────────────────────


class TestJsonSafe:
    """_json_safe 타입별 변환 검증."""

    def test_decimal_to_str(self) -> None:
        assert _json_safe(Decimal("50000000000.00")) == "50000000000.00"

    def test_decimal_zero(self) -> None:
        assert _json_safe(Decimal("0")) == "0"

    def test_decimal_negative(self) -> None:
        assert _json_safe(Decimal("-123.456")) == "-123.456"

    def test_uuid_to_str(self) -> None:
        uid = uuid.uuid4()
        result = _json_safe(uid)
        assert result == str(uid)
        assert isinstance(result, str)

    def test_datetime_to_isoformat(self) -> None:
        dt = datetime(2026, 3, 1, 14, 30, 0)
        assert _json_safe(dt) == "2026-03-01T14:30:00"

    def test_date_to_isoformat(self) -> None:
        d = date(2026, 3, 1)
        assert _json_safe(d) == "2026-03-01"

    def test_strenum_to_value(self) -> None:
        assert _json_safe(_SampleEnum.ALPHA) == "ALPHA"

    def test_plain_enum_to_value(self) -> None:
        assert _json_safe(_PlainEnum.X) == 1
        assert _json_safe(_PlainEnum.Y) == "hello"

    def test_str_passthrough(self) -> None:
        assert _json_safe("hello") == "hello"

    def test_int_passthrough(self) -> None:
        assert _json_safe(42) == 42

    def test_float_passthrough(self) -> None:
        assert _json_safe(3.14) == 3.14

    def test_bool_passthrough(self) -> None:
        assert _json_safe(True) is True
        assert _json_safe(False) is False

    def test_none_passthrough(self) -> None:
        assert _json_safe(None) is None

    def test_dict_recursive(self) -> None:
        data = {"price": Decimal("100.50"), "id": uuid.uuid4()}
        result = _json_safe(data)
        assert result["price"] == "100.50"
        assert isinstance(result["id"], str)

    def test_list_recursive(self) -> None:
        data = [Decimal("1.0"), uuid.uuid4(), "plain"]
        result = _json_safe(data)
        assert result[0] == "1.0"
        assert isinstance(result[1], str)
        assert result[2] == "plain"

    def test_tuple_to_list(self) -> None:
        data = (Decimal("9.99"), "text")
        result = _json_safe(data)
        assert isinstance(result, list)
        assert result[0] == "9.99"

    def test_nested_dict_in_list(self) -> None:
        data = [{"val": Decimal("5.0")}, {"val": Decimal("10.0")}]
        result = _json_safe(data)
        assert result[0]["val"] == "5.0"
        assert result[1]["val"] == "10.0"

    def test_result_is_json_serializable(self) -> None:
        """변환 결과가 json.dumps로 직렬화 가능한지 확인."""
        data = {
            "id": uuid.uuid4(),
            "amount": Decimal("999999.99"),
            "status": _SampleEnum.BETA,
            "created": datetime(2026, 1, 1, 12, 0),
            "date": date(2026, 6, 15),
            "nested": {"ids": [uuid.uuid4(), uuid.uuid4()]},
            "name": "한글 테스트",
            "empty": None,
        }
        result = _json_safe(data)
        # json.dumps가 예외 없이 성공해야 함
        serialized = json.dumps(result, ensure_ascii=False)
        assert "한글 테스트" in serialized
        assert "BETA" in serialized


# ── _sanitize_for_json 단위 테스트 ───────────────────────


class TestSanitizeForJson:
    """_sanitize_for_json 래퍼 함수 검증."""

    def test_none_returns_none(self) -> None:
        assert _sanitize_for_json(None) is None

    def test_empty_dict(self) -> None:
        assert _sanitize_for_json({}) == {}

    def test_mixed_types(self) -> None:
        data = {
            "price": Decimal("100.50"),
            "id": uuid.uuid4(),
            "status": _SampleEnum.ALPHA,
            "name": "테스트",
            "count": 3,
            "active": True,
            "notes": None,
        }
        result = _sanitize_for_json(data)
        assert result is not None
        assert result["price"] == "100.50"
        assert isinstance(result["id"], str)
        assert result["status"] == "ALPHA"
        assert result["name"] == "테스트"
        assert result["count"] == 3
        assert result["active"] is True
        assert result["notes"] is None

    def test_result_json_serializable(self) -> None:
        data = {
            "buyer_id": uuid.uuid4(),
            "tier": _SampleEnum.BETA,
            "amount": Decimal("1234567890.12"),
        }
        result = _sanitize_for_json(data)
        assert result is not None
        # json.dumps 성공 여부
        json.dumps(result)
