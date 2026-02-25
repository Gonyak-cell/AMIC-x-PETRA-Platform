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

    def test_hash_format_is_bcrypt(self):
        hashed = hash_password("test")
        # bcrypt 형식: $2b$12$...
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60  # bcrypt always produces 60-char hash
