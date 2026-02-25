"""
텔레그램 메시지 유틸리티 — 분할, 포맷팅, 이스케이프.
"""

from __future__ import annotations

MAX_TELEGRAM_LENGTH = 4096


def split_message(text: str, max_length: int = MAX_TELEGRAM_LENGTH) -> list[str]:
    """텔레그램 메시지 길이 제한에 맞게 텍스트를 분할한다."""
    if len(text) <= max_length:
        return [text]

    parts: list[str] = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break

        chunk = text[:max_length]
        # 줄바꿈 → 공백 → 강제 분할 순으로 분할 지점 탐색
        split_at = chunk.rfind("\n")
        if split_at == -1 or split_at < max_length // 2:
            split_at = chunk.rfind(" ")
        if split_at == -1 or split_at < max_length // 2:
            split_at = max_length

        parts.append(text[:split_at])
        # 분할 지점의 줄바꿈 1개만 제거 (빈 줄 보존)
        remaining = text[split_at:]
        if remaining.startswith("\n"):
            remaining = remaining[1:]
        text = remaining

    return parts


def truncate_output(text: str, max_chars: int = 3000) -> str:
    """긴 셸 출력을 뒤에서부터 잘라 가장 관련있는 부분을 보여준다."""
    if len(text) <= max_chars:
        return text

    truncated = text[-max_chars:]
    return f"... (앞부분 {len(text) - max_chars}자 생략)\n\n{truncated}"


def format_cost_info(
    cost_usd: float | None,
    input_tokens: int | None,
    output_tokens: int | None,
    duration: float,
) -> str:
    """비용 정보를 한 줄로 포맷팅한다."""
    parts = [f"⏱ {duration:.1f}s"]

    if cost_usd is not None:
        parts.append(f"💰 ${cost_usd:.4f}")

    if input_tokens is not None and output_tokens is not None:
        parts.append(f"📊 {input_tokens:,}→{output_tokens:,} tokens")

    return " | ".join(parts)
