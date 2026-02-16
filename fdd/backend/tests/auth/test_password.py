"""비밀번호 해싱 유닛 테스트."""

from app.auth.password import hash_password, verify_password


class TestPassword:
    def test_hash_and_verify_correct(self):
        hashed = hash_password("mypassword123")
        assert verify_password("mypassword123", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("mypassword123")
        assert verify_password("wrongpassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2  # salt가 다르므로 해시값도 달라야 함

    def test_hash_format_contains_salt_and_key(self):
        hashed = hash_password("test")
        parts = hashed.split(":")
        assert len(parts) == 2
        assert len(parts[0]) == 64  # 32 bytes hex = 64 chars
        assert len(parts[1]) == 64  # SHA-256 = 32 bytes hex = 64 chars
