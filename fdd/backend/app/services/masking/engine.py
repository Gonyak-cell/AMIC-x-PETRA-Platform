"""민감정보 마스킹 엔진 — FDD-1403.

금액/텍스트/계정명 마스킹 + Report IR 전체 마스킹.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


class DistributionMode(str, Enum):
    """외부배포본 모드 — FDD-1402."""

    INTERNAL = "INTERNAL"
    EXTERNAL_BUYER = "EXTERNAL_BUYER"
    EXTERNAL_SELLER = "EXTERNAL_SELLER"
    REDACTED = "REDACTED"


class AmountMaskMode(str, Enum):
    """금액 마스킹 방식."""

    HIDE = "hide"
    RANGE = "range"
    X_MASK = "x_mask"


@dataclass
class MaskingConfig:
    """마스킹 설정."""

    mode: DistributionMode = DistributionMode.INTERNAL
    amount_mode: AmountMaskMode = AmountMaskMode.X_MASK
    mask_company_names: bool = True
    mask_person_names: bool = True
    mask_account_names: bool = False
    custom_company_aliases: dict[str, str] = field(default_factory=dict)
    excluded_sections: list[str] = field(default_factory=list)


# 기본 모드별 설정
MODE_DEFAULTS: dict[DistributionMode, MaskingConfig] = {
    DistributionMode.INTERNAL: MaskingConfig(mode=DistributionMode.INTERNAL),
    DistributionMode.EXTERNAL_BUYER: MaskingConfig(
        mode=DistributionMode.EXTERNAL_BUYER,
        amount_mode=AmountMaskMode.X_MASK,
        mask_company_names=True,
        mask_person_names=True,
        excluded_sections=["methodology", "scope"],
    ),
    DistributionMode.EXTERNAL_SELLER: MaskingConfig(
        mode=DistributionMode.EXTERNAL_SELLER,
        amount_mode=AmountMaskMode.X_MASK,
        mask_company_names=True,
        mask_person_names=True,
        excluded_sections=["methodology", "scope"],
    ),
    DistributionMode.REDACTED: MaskingConfig(
        mode=DistributionMode.REDACTED,
        amount_mode=AmountMaskMode.HIDE,
        mask_company_names=True,
        mask_person_names=True,
        mask_account_names=True,
    ),
}


class MaskingEngine:
    """민감정보 마스킹 엔진."""

    def __init__(self, config: MaskingConfig | None = None):
        self.config = config or MaskingConfig()
        self._company_counter = 0
        self._company_map: dict[str, str] = {}
        self._person_counter = 0
        self._person_map: dict[str, str] = {}

    @classmethod
    def for_mode(cls, mode: DistributionMode) -> MaskingEngine:
        """배포 모드에 맞는 기본 설정으로 엔진을 생성한다."""
        return cls(config=MODE_DEFAULTS.get(mode, MaskingConfig(mode=mode)))

    def mask_amount(self, amount: Decimal) -> str:
        """금액을 마스킹한다."""
        if self.config.mode == DistributionMode.INTERNAL:
            return str(amount)

        if self.config.amount_mode == AmountMaskMode.HIDE:
            return "[금액 숨김]"
        elif self.config.amount_mode == AmountMaskMode.RANGE:
            return self._amount_to_range(amount)
        else:
            return self._amount_to_x(amount)

    def mask_text(self, text: str, entity_type: str) -> str:
        """텍스트를 엔티티 유형에 따라 마스킹한다."""
        if self.config.mode == DistributionMode.INTERNAL:
            return text

        if entity_type == "company" and self.config.mask_company_names:
            return self._get_company_alias(text)
        elif entity_type == "person" and self.config.mask_person_names:
            return self._get_person_alias(text)
        elif entity_type == "account" and self.config.mask_account_names:
            return f"[계정{self._get_hash_suffix(text)}]"
        return text

    def mask_dict(self, data: dict[str, Any], sensitive_keys: set[str] | None = None) -> dict[str, Any]:
        """딕셔너리의 민감 필드를 마스킹한다."""
        if self.config.mode == DistributionMode.INTERNAL:
            return data

        if sensitive_keys is None:
            sensitive_keys = {"company_name", "person_name", "account_name", "amount", "email", "phone"}

        result = {}
        for key, value in data.items():
            if key in sensitive_keys:
                if isinstance(value, Decimal):
                    result[key] = self.mask_amount(value)
                elif isinstance(value, str):
                    result[key] = "[마스킹됨]"
                else:
                    result[key] = "[마스킹됨]"
            elif isinstance(value, dict):
                result[key] = self.mask_dict(value, sensitive_keys)
            elif isinstance(value, list):
                result[key] = [
                    self.mask_dict(item, sensitive_keys) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def mask_report_ir(self, report_ir: dict[str, Any]) -> dict[str, Any]:
        """Report IR 전체를 마스킹한다."""
        if self.config.mode == DistributionMode.INTERNAL:
            return report_ir

        masked = dict(report_ir)
        masked["distribution_mode"] = self.config.mode.value

        if "sections" in masked:
            masked["sections"] = [
                self._mask_section(section) for section in masked["sections"]
            ]

        return masked

    def is_internal(self) -> bool:
        """내부용 모드인지 확인한다."""
        return self.config.mode == DistributionMode.INTERNAL

    def get_masking_summary(self) -> dict[str, Any]:
        """마스킹 적용 요약을 반환한다."""
        return {
            "mode": self.config.mode.value,
            "amount_mode": self.config.amount_mode.value,
            "companies_masked": len(self._company_map),
            "persons_masked": len(self._person_map),
            "mask_company_names": self.config.mask_company_names,
            "mask_person_names": self.config.mask_person_names,
            "mask_account_names": self.config.mask_account_names,
        }

    # ── Private helpers ───────────────────────────────────

    def _amount_to_x(self, amount: Decimal) -> str:
        """금액을 X로 마스킹한다. 예: 1,234,567 → X,XXX,XXX"""
        abs_amount = abs(amount)
        formatted = f"{abs_amount:,.0f}"
        masked = re.sub(r"\d", "X", formatted)
        if amount < 0:
            masked = f"-{masked}"
        return masked

    def _amount_to_range(self, amount: Decimal) -> str:
        """금액을 범위로 마스킹한다. 예: 1,234,567 → 1M~2M"""
        abs_amount = abs(int(amount))
        if abs_amount < 1_000:
            return "1K 미만"
        elif abs_amount < 1_000_000:
            lower = (abs_amount // 1_000) * 1_000
            upper = lower + 1_000
            return f"{lower // 1_000}K~{upper // 1_000}K"
        elif abs_amount < 1_000_000_000:
            lower = (abs_amount // 1_000_000) * 1_000_000
            upper = lower + 1_000_000
            return f"{lower // 1_000_000}M~{upper // 1_000_000}M"
        else:
            lower = (abs_amount // 1_000_000_000) * 1_000_000_000
            upper = lower + 1_000_000_000
            return f"{lower // 1_000_000_000}B~{upper // 1_000_000_000}B"

    def _get_company_alias(self, name: str) -> str:
        """회사명에 일관된 별칭을 부여한다."""
        if name in self.config.custom_company_aliases:
            return self.config.custom_company_aliases[name]
        if name not in self._company_map:
            self._company_counter += 1
            self._company_map[name] = f"[회사{chr(64 + self._company_counter)}]"
        return self._company_map[name]

    def _get_person_alias(self, name: str) -> str:
        """인물명에 일관된 별칭을 부여한다."""
        if name not in self._person_map:
            self._person_counter += 1
            self._person_map[name] = f"[인물{self._person_counter}]"
        return self._person_map[name]

    def _get_hash_suffix(self, text: str) -> str:
        """텍스트의 짧은 해시를 반환한다."""
        return hashlib.md5(text.encode()).hexdigest()[:4].upper()

    def _mask_section(self, section: dict[str, Any]) -> dict[str, Any]:
        """Report IR의 단일 섹션을 마스킹한다."""
        section_id = section.get("id", "")
        if section_id in self.config.excluded_sections:
            return section

        masked = dict(section)
        if "blocks" in masked:
            masked["blocks"] = [self._mask_block(block) for block in masked["blocks"]]
        return masked

    def _mask_block(self, block: dict[str, Any]) -> dict[str, Any]:
        """Report IR의 단일 블록을 마스킹한다."""
        masked = dict(block)
        block_type = masked.get("type", "")

        if block_type == "table" and "rows" in masked:
            masked["rows"] = [self._mask_table_row(row) for row in masked["rows"]]
        elif block_type == "kpi" and "value" in masked:
            try:
                val = Decimal(str(masked["value"]))
                masked["value"] = self.mask_amount(val)
            except Exception:
                masked["value"] = "[마스킹됨]"
        elif block_type == "text" and "content" in masked:
            masked["content"] = self._mask_text_content(masked["content"])
        elif block_type == "claim":
            if "amount" in masked:
                try:
                    val = Decimal(str(masked["amount"]))
                    masked["amount"] = self.mask_amount(val)
                except Exception:
                    masked["amount"] = "[마스킹됨]"

        return masked

    def _mask_table_row(self, row: dict[str, Any] | list) -> dict[str, Any] | list:
        """테이블 행의 금액 셀을 마스킹한다."""
        if isinstance(row, list):
            return [self._mask_cell(cell) for cell in row]
        if isinstance(row, dict):
            return {k: self._mask_cell(v) for k, v in row.items()}
        return row

    def _mask_cell(self, value: Any) -> Any:
        """셀 값이 숫자이면 마스킹한다."""
        if isinstance(value, Decimal):
            return self.mask_amount(value)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                return self.mask_amount(Decimal(str(value)))
            except Exception:
                return value
        return value

    def _mask_text_content(self, text: str) -> str:
        """텍스트 내용에서 금액 패턴을 마스킹한다."""
        if self.config.mode == DistributionMode.REDACTED:
            # 숫자 패턴 전체 마스킹
            return re.sub(r"[\d,]+(\.\d+)?", "X,XXX", text)
        return text
