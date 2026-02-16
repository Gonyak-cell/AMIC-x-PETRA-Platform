# > 마지막 수정: 2026-02-10 19:30:00
"""
Gunicorn 설정 파일

Production 환경에서 Auto-IM Generator API 서버를 실행하기 위한
Gunicorn 웹 서버 설정입니다.
"""

import multiprocessing

# 바인딩 주소 및 포트
bind = "0.0.0.0:8000"

# 워커 프로세스 수 (CPU 코어 수 * 2 + 1)
workers = multiprocessing.cpu_count() * 2 + 1

# 워커 클래스 (FastAPI를 위한 UvicornWorker)
worker_class = "uvicorn.workers.UvicornWorker"

# 동시 연결 수
worker_connections = 1000

# 요청 타임아웃 (초)
timeout = 120

# Graceful shutdown 타임아웃 (초)
graceful_timeout = 30

# Keep-alive 시간 (초)
keepalive = 5

# 워커 재시작 전 처리할 최대 요청 수
max_requests = 1000

# max_requests에 추가할 랜덤 지터 (재시작 분산)
max_requests_jitter = 100

# 액세스 로그 출력 (stdout)
accesslog = "-"

# 에러 로그 출력 (stderr)
errorlog = "-"

# 로그 레벨
loglevel = "info"

# 프로세스 이름
proc_name = "auto-im-generator"

# 코드 변경 시 자동 재시작 (production에서는 False)
reload = False
