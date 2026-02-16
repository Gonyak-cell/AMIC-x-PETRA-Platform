import hashlib
import json
from typing import Any


def canonical_json(data: Any) -> str:
    """Produce a deterministic JSON string for hashing.

    Keys are sorted, no extra whitespace, ensure_ascii for byte-level consistency.
    """
    return json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def hash_json(data: Any) -> str:
    """SHA-256 hash of the canonical JSON representation of data."""
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def hash_strings(values: list[str]) -> str:
    """SHA-256 hash of a sorted list of strings (e.g., file hashes)."""
    combined = "|".join(sorted(values))
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def combine_hashes(*hashes: str) -> str:
    """Combine multiple hash strings into a single hash."""
    combined = "|".join(hashes)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()
