"""message_utils.py 유닛 테스트."""

from bot.message_utils import format_cost_info, split_message, truncate_output


class TestSplitMessage:
    def test_short_message_not_split(self):
        assert split_message("hello") == ["hello"]

    def test_exact_limit(self):
        text = "a" * 4096
        assert split_message(text) == [text]

    def test_splits_at_newline(self):
        text = "a" * 4000 + "\n" + "b" * 200
        parts = split_message(text, max_length=4096)
        assert len(parts) == 2
        assert parts[0] == "a" * 4000
        assert parts[1] == "b" * 200

    def test_splits_at_space(self):
        text = "word " * 1000  # 5000 chars
        parts = split_message(text, max_length=100)
        assert all(len(p) <= 100 for p in parts)
        assert "".join(parts).replace(" ", "") == "word" * 1000

    def test_force_split(self):
        text = "x" * 5000  # 연속 문자열 — 줄바꿈/공백 없음
        parts = split_message(text, max_length=4096)
        assert len(parts) == 2


class TestTruncateOutput:
    def test_short_text_unchanged(self):
        assert truncate_output("hello", 100) == "hello"

    def test_long_text_truncated(self):
        text = "a" * 5000
        result = truncate_output(text, max_chars=3000)
        assert "생략" in result
        assert len(result) < 5000

    def test_keeps_tail(self):
        text = "START" + "x" * 5000 + "END"
        result = truncate_output(text, max_chars=100)
        assert result.endswith("END")


class TestFormatCostInfo:
    def test_with_all_info(self):
        result = format_cost_info(0.0123, 1000, 500, 2.5)
        assert "$0.0123" in result
        assert "2.5s" in result
        assert "1,000" in result

    def test_with_no_cost(self):
        result = format_cost_info(None, None, None, 1.0)
        assert "1.0s" in result
        assert "$" not in result
