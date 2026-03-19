#!/usr/bin/env python3
"""임시 SI 기업 공공데이터 동기화 진행상황 모니터 서버.

사용법:
    cd "c:/Users/서지원/OneDrive/Documents/Coding/AMIC x PETRA Platform"
    python sync_status_server.py

브라우저에서 http://localhost:8888 접속
"""

from __future__ import annotations

import http.server
import json
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

# ── 설정 ──────────────────────────────────────────────────────────────
SSH_KEY = str(Path(__file__).parent / "ssh" / "amic-platform-prod_key.pem")
SSH_HOST = "azureuser@52.231.69.38"
CONTAINER = "amic-deal-mgmt-api"
PORT = 8888
REFRESH_INTERVAL = 30  # seconds

# ── 공유 상태 ──────────────────────────────────────────────────────────
state: dict = {
    "total": 113107,
    "corp_synced": 0,
    "fina_synced": 0,
    "last_updated": None,
    "error": None,
    "history": [],
}
state_lock = threading.Lock()

# ── DB 조회 Python 코드 (stdin으로 컨테이너에 전달) ─────────────────────
DB_QUERY_SCRIPT = b"""
import asyncio, sys
sys.path.insert(0, '/app')
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def q():
    e = create_async_engine(settings.DATABASE_URL)
    S = sessionmaker(e, class_=AsyncSession)
    async with S() as s:
        r = await s.execute(text(
            'SELECT COUNT(*), '
            'COUNT(corp_basic_synced_at), '
            'COUNT(fina_stat_synced_at) '
            'FROM si_companies'
        ))
        row = r.fetchone()
        print(f'{row[0]},{row[1]},{row[2]}', flush=True)
    await e.dispose()

asyncio.run(q())
"""


def query_db() -> tuple[int, int, int]:
    """SSH → docker exec -i → Python stdin 방식으로 DB 조회."""
    ssh_cmd = [
        "ssh",
        "-i",
        SSH_KEY,
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ConnectTimeout=20",
        "-o",
        "ServerAliveInterval=30",
        SSH_HOST,
        f"docker exec -i {CONTAINER} python",
    ]
    result = subprocess.run(
        ssh_cmd,
        input=DB_QUERY_SCRIPT,
        capture_output=True,
        timeout=60,
    )
    stdout = result.stdout.decode().strip()
    if result.returncode != 0 or not stdout:
        stderr = result.stderr.decode().strip()
        raise RuntimeError(
            stderr or f"returncode={result.returncode}, stdout='{stdout}'"
        )

    # 마지막 줄만 파싱 (SQLAlchemy 경고 제거)
    last_line = stdout.splitlines()[-1]
    parts = last_line.split(",")
    if len(parts) < 3:
        raise RuntimeError(f"응답 파싱 실패: '{last_line}'")
    return int(parts[0]), int(parts[1]), int(parts[2])


def monitor_loop() -> None:
    """30초마다 DB를 조회하여 state를 갱신한다."""
    # 첫 조회는 즉시
    time.sleep(1)
    while True:
        try:
            total, corp, fina = query_db()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with state_lock:
                state["total"] = total
                state["corp_synced"] = corp
                state["fina_synced"] = fina
                state["last_updated"] = now
                state["error"] = None
                state["history"].append({"time": now, "corp": corp, "fina": fina})
                if len(state["history"]) > 20:
                    state["history"].pop(0)
        except Exception as exc:
            with state_lock:
                state["error"] = str(exc)
        time.sleep(REFRESH_INTERVAL)


# ── HTML 템플릿 ────────────────────────────────────────────────────────
HTML = """\
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="30">
<title>SI 기업 동기화 현황</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f1f5f9;color:#1e293b;padding:2rem}}
h1{{font-size:1.375rem;font-weight:700;margin-bottom:.25rem}}
.sub{{color:#64748b;font-size:.85rem;margin-bottom:1.75rem}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1.25rem;margin-bottom:1.25rem}}
.card{{background:#fff;border-radius:.875rem;padding:1.375rem;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.card h2{{font-size:.9rem;font-weight:600;color:#475569;margin-bottom:.875rem;text-transform:uppercase;letter-spacing:.04em}}
.big{{font-size:2.25rem;font-weight:700;line-height:1}}
.big.green{{color:#059669}}.big.blue{{color:#2563eb}}
.denom{{font-size:.95rem;color:#94a3b8;margin-left:.25rem}}
.bar-track{{background:#e2e8f0;border-radius:999px;height:10px;margin:.75rem 0 .5rem}}
.bar-fill{{height:100%;border-radius:999px;transition:width .6s ease}}
.bar-fill.green{{background:linear-gradient(90deg,#059669,#10b981)}}
.bar-fill.blue{{background:linear-gradient(90deg,#2563eb,#3b82f6)}}
.meta{{font-size:.78rem;color:#94a3b8}}
.err{{background:#fef2f2;border:1px solid #fecaca;color:#dc2626;padding:.875rem 1rem;border-radius:.5rem;margin-bottom:1.25rem;font-size:.85rem}}
table{{width:100%;border-collapse:collapse;font-size:.8rem}}
th{{text-align:left;padding:.45rem .5rem;border-bottom:2px solid #e2e8f0;color:#64748b;font-weight:600}}
td{{padding:.4rem .5rem;border-bottom:1px solid #f1f5f9}}
.badge{{display:inline-block;padding:.1rem .45rem;border-radius:999px;font-size:.72rem;font-weight:600;margin-right:.25rem}}
.g{{background:#dcfce7;color:#15803d}}.b{{background:#dbeafe;color:#1d4ed8}}
.refresh{{font-size:.73rem;color:#94a3b8;text-align:right;margin-top:.875rem}}
</style>
</head>
<body>
<h1>SI 기업 공공데이터 포털 동기화 현황</h1>
<p class="sub">30초마다 자동 갱신 &nbsp;·&nbsp; 마지막 조회: {last_updated}</p>

{error_block}

<div class="grid">
  <div class="card">
    <h2>기업기본정보</h2>
    <span class="big green">{corp_synced:,}</span><span class="denom">/ {total:,}</span>
    <div class="bar-track"><div class="bar-fill green" style="width:{corp_pct:.2f}%"></div></div>
    <div class="meta">{corp_pct:.1f}% 완료 &nbsp;·&nbsp; 남은 건수 {corp_remaining:,}건</div>
  </div>
  <div class="card">
    <h2>재무정보</h2>
    <span class="big blue">{fina_synced:,}</span><span class="denom">/ {total:,}</span>
    <div class="bar-track"><div class="bar-fill blue" style="width:{fina_pct:.2f}%"></div></div>
    <div class="meta">{fina_pct:.1f}% 완료 &nbsp;·&nbsp; 남은 건수 {fina_remaining:,}건</div>
  </div>
</div>

<div class="card">
  <h2>업데이트 이력</h2>
  <table>
    <tr><th>시각</th><th>기업기본정보</th><th>재무정보</th><th>증가량</th></tr>
    {history_rows}
  </table>
</div>

<p class="refresh">이 페이지는 30초마다 자동 새로고침됩니다.</p>
</body>
</html>"""


def build_html() -> str:
    with state_lock:
        s = dict(state)
        history = list(state["history"])

    corp = s["corp_synced"]
    fina = s["fina_synced"]
    total = s["total"] or 1
    corp_pct = corp / total * 100
    fina_pct = fina / total * 100

    error_block = ""
    if s["error"]:
        error_block = f'<div class="err">⚠ DB 조회 오류: {s["error"]}</div>'

    rows = []
    rev = list(reversed(history))
    for i, h in enumerate(rev[:12]):
        delta_html = ""
        if i < len(rev) - 1:
            prev = rev[i + 1]
            dc = h["corp"] - prev["corp"]
            df = h["fina"] - prev["fina"]
            if dc > 0:
                delta_html += f'<span class="badge g">+{dc:,} 기본</span>'
            if df > 0:
                delta_html += f'<span class="badge b">+{df:,} 재무</span>'
        rows.append(
            f"<tr><td>{h['time']}</td>"
            f"<td>{h['corp']:,}</td>"
            f"<td>{h['fina']:,}</td>"
            f"<td>{delta_html or '–'}</td></tr>"
        )

    return HTML.format(
        last_updated=s["last_updated"] or "조회 중...",
        error_block=error_block,
        corp_synced=corp,
        fina_synced=fina,
        total=s["total"],
        corp_pct=corp_pct,
        fina_pct=fina_pct,
        corp_remaining=s["total"] - corp,
        fina_remaining=s["total"] - fina,
        history_rows="\n    ".join(rows)
        if rows
        else "<tr><td colspan='4'>데이터 수집 중...</td></tr>",
    )


# ── HTTP 핸들러 ────────────────────────────────────────────────────────
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/status":
            with state_lock:
                data = json.dumps(state).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            html = build_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: N802
        pass  # 접근 로그 억제


if __name__ == "__main__":
    print("=" * 55)
    print("  SI 기업 동기화 모니터 서버")
    print("=" * 55)
    print(f"  브라우저: http://localhost:{PORT}")
    print(f"  SSH 키:   {SSH_KEY}")
    print("  종료: Ctrl+C")
    print()

    threading.Thread(target=monitor_loop, daemon=True).start()

    try:
        with http.server.HTTPServer(("", PORT), Handler) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버 종료.")
