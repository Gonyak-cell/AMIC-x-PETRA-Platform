# Auto-IM Generator — Multi-stage Docker Build (T-I21)
# > 마지막 수정: 2026-02-10 23:30:00

# ============================================================================
# Stage 1: Builder — 의존성 설치 + Playwright 브라우저
# ============================================================================
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium && \
    playwright install-deps chromium

# ============================================================================
# Stage 2: Runtime — 경량 실행 환경
# ============================================================================
FROM python:3.11-slim-bookworm

WORKDIR /app

# 런타임 시스템 의존성
# cairo, pango: WeasyPrint PDF 렌더링
# graphviz: 조직도 다이어그램
# fonts-noto-cjk: 한국어 폰트
# libpq5: PostgreSQL 클라이언트
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    graphviz \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Builder에서 Python 패키지 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright

# Non-root user 생성
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

# 애플리케이션 코드 복사
COPY . .

# 출력 디렉토리 생성 + Playwright cache 복사 to non-root user home
RUN mkdir -p /app/output && \
    cp -r /root/.cache/ms-playwright /home/appuser/.cache/ms-playwright 2>/dev/null || true && \
    chown -R appuser:appuser /app

# 환경 변수
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# FastAPI 실행
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
