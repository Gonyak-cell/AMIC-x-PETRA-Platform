"""Tests for hashing utilities - ensuring reproducibility (FDD-101 AC)."""

from app.utils.hashing import canonical_json, combine_hashes, hash_json, hash_strings


class TestCanonicalJson:
    def test_key_order_independent(self):
        """Same data with different key order → same canonical JSON."""
        a = {"b": 2, "a": 1}
        b = {"a": 1, "b": 2}
        assert canonical_json(a) == canonical_json(b)

    def test_no_whitespace(self):
        result = canonical_json({"key": "value"})
        assert " " not in result


class TestHashJson:
    def test_deterministic(self):
        data = {
            "cash": {"include": ["1110"], "exclude": []},
            "nwc": {"include": ["1200"]},
        }
        assert hash_json(data) == hash_json(data)

    def test_different_data_different_hash(self):
        a = {"cash": {"include": ["1110"]}}
        b = {"cash": {"include": ["1120"]}}
        assert hash_json(a) != hash_json(b)


class TestHashStrings:
    def test_order_independent(self):
        assert hash_strings(["abc", "def"]) == hash_strings(["def", "abc"])


class TestCombineHashes:
    def test_deterministic(self):
        h1 = "a" * 64
        h2 = "b" * 64
        assert combine_hashes(h1, h2) == combine_hashes(h1, h2)
