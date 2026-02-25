"""핸들러 유닛 테스트."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bot.handlers.file_ops import _is_blocked, _resolve_path


class TestFileBlocking:
    def test_blocks_env_file(self):
        assert _is_blocked(Path("/project/.env")) is True

    def test_blocks_git_dir(self):
        assert _is_blocked(Path("/project/.git/config")) is True

    def test_blocks_pem_file(self):
        assert _is_blocked(Path("/project/key.pem")) is True

    def test_allows_normal_file(self):
        assert _is_blocked(Path("/project/src/main.py")) is False

    def test_allows_readme(self):
        assert _is_blocked(Path("/project/README.md")) is False


class TestResolvePath:
    def test_blocks_outside_project(self, tmp_path):
        project_root = tmp_path / "project"
        project_root.mkdir()
        _, error = _resolve_path("../../etc/passwd", str(project_root), project_root)
        assert error is not None
        assert "프로젝트 루트 밖" in error

    def test_blocks_env_file(self, tmp_path):
        project_root = tmp_path / "project"
        project_root.mkdir()
        env_file = project_root / ".env"
        env_file.touch()
        _, error = _resolve_path(".env", str(project_root), project_root)
        assert error is not None
        assert "보안" in error

    def test_resolves_valid_file(self, tmp_path):
        project_root = tmp_path / "project"
        project_root.mkdir()
        test_file = project_root / "main.py"
        test_file.write_text("print('hello')")
        resolved, error = _resolve_path("main.py", str(project_root), project_root)
        assert error is None
        assert resolved == test_file

    def test_file_not_found(self, tmp_path):
        project_root = tmp_path / "project"
        project_root.mkdir()
        _, error = _resolve_path("nonexistent.py", str(project_root), project_root)
        assert error is not None
        assert "찾을 수 없습니다" in error
