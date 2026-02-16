"""FastAPI 애플리케이션 진입점.

> 마지막 수정: 2026-02-10 16:29:08

uvicorn src.api.main:app --reload 으로 실행.
"""

from src.api import create_app

app = create_app()
