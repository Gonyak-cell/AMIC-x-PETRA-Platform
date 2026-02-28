"""공공데이터 시드 진행 상황 실시간 모니터링 대시보드.

로컬에서 실행하면 SSH로 프로덕션 서버에 접속하여 DB/로그 통계를 수집하고,
브라우저에서 실시간 그래프로 확인할 수 있다.

Usage:
    python scripts/seed-monitor.py
    # 브라우저에서 http://localhost:8080 접속
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

# ── 설정 ──
SSH_KEY = str(Path(__file__).resolve().parent.parent / "ssh" / "amic-platform-prod_key.pem")
SSH_HOST = "azureuser@52.231.69.38"
SSH_OPTS = ["-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10"]
COMPOSE = "docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.ssl.yml"
POLL_INTERVAL = 30  # 초
PORT = 8080
DAILY_API_LIMIT = 100_000  # 운영계정 일일 한도 (API별)

# ── 상태 저장소 ──
state: dict = {
    "last_updated": None,
    "error": None,
    "total_companies": 0,
    "revenue_count": 0,
    "corp_basic_count": 0,
    "revenue_api_calls": 0,
    "corp_basic_api_calls": 0,
    "revenue_process_alive": False,
    "corp_basic_process_alive": False,
    "history": [],  # [{ts, revenue_count, corp_basic_count, revenue_api, corp_api}]
}


def ssh_cmd(cmd: str) -> str:
    """SSH로 프로덕션 서버에 명령 실행."""
    result = subprocess.run(
        ["ssh", "-i", SSH_KEY, *SSH_OPTS, SSH_HOST, cmd],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout.strip()


def collect_stats() -> None:
    """프로덕션 서버에서 통계를 수집하여 state에 저장."""
    global state
    try:
        # 1) DB 통계
        db_result = ssh_cmd(
            f"cd /opt/amic-platform && {COMPOSE} exec -T deal-mgmt-db "
            "psql -U deal_mgmt_user -d deal_mgmt -t -A -F'|' -c "
            "\"SELECT "
            "(SELECT COUNT(*) FROM si_companies) as total, "
            "(SELECT COUNT(*) FROM si_companies WHERE revenue IS NOT NULL) as rev, "
            "(SELECT COUNT(*) FROM si_companies WHERE corp_basic_synced_at IS NOT NULL) as corp\""
        )
        if "|" in db_result:
            parts = db_result.strip().split("|")
            state["total_companies"] = int(parts[0])
            state["revenue_count"] = int(parts[1])
            state["corp_basic_count"] = int(parts[2])

        # 2) 로그 파일 API 호출 수
        log_result = ssh_cmd(
            'echo "rev:$(grep -c "HTTP/1.1 200" /tmp/seed-revenue-20260228.log 2>/dev/null || echo 0)";'
            'echo "corp:$(grep -c "HTTP/1.1 200" /tmp/seed-corp-20260228.log 2>/dev/null || echo 0)"'
        )
        for line in log_result.splitlines():
            if line.startswith("rev:"):
                state["revenue_api_calls"] = int(line.split(":")[1])
            elif line.startswith("corp:"):
                state["corp_basic_api_calls"] = int(line.split(":")[1])

        # 3) 프로세스 생존 확인
        ps_result = ssh_cmd("ps aux | grep python | grep seed_ | grep -v grep")
        state["revenue_process_alive"] = "seed_revenue" in ps_result
        state["corp_basic_process_alive"] = "seed_corp_basic" in ps_result

        # 4) 타임스탬프 & 히스토리
        now = datetime.now().strftime("%H:%M:%S")
        state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state["error"] = None
        state["history"].append({
            "ts": now,
            "revenue_count": state["revenue_count"],
            "corp_basic_count": state["corp_basic_count"],
            "revenue_api": state["revenue_api_calls"],
            "corp_api": state["corp_basic_api_calls"],
        })
        # 히스토리 최대 500건 유지 (약 4시간분)
        if len(state["history"]) > 500:
            state["history"] = state["history"][-500:]

    except Exception as exc:
        state["error"] = str(exc)
        state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def poll_loop() -> None:
    """주기적으로 통계를 수집하는 백그라운드 루프."""
    while True:
        collect_stats()
        time.sleep(POLL_INTERVAL)


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Seed Monitor — AMIC Platform</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Pretendard', -apple-system, sans-serif; background: #0f1117; color: #e4e4e7; }
  .header { padding: 24px 32px; border-bottom: 1px solid #27272a; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
  .header h1 { font-size: 20px; font-weight: 600; }
  .header .badge { font-size: 12px; padding: 4px 10px; border-radius: 12px; }
  .badge-live { background: #16a34a22; color: #4ade80; border: 1px solid #16a34a44; animation: pulse 2s infinite; }
  .badge-dead { background: #dc262622; color: #f87171; border: 1px solid #dc262644; }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }
  .updated { margin-left: auto; font-size: 13px; color: #71717a; }
  .countdown { font-size: 12px; color: #525252; margin-left: 8px; }
  .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; padding: 24px 32px; }
  .card { background: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 20px; }
  .card-label { font-size: 13px; color: #a1a1aa; margin-bottom: 8px; }
  .card-value { font-size: 28px; font-weight: 700; }
  .card-sub { font-size: 13px; color: #71717a; margin-top: 4px; }
  .pct { color: #4ade80; font-size: 18px; }
  .charts { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 0 32px 24px; }
  .chart-card { background: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 20px; }
  .chart-card h3 { font-size: 15px; margin-bottom: 12px; color: #a1a1aa; }
  .progress-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 0 32px 24px; }
  .progress-bar-wrap { background: #27272a; border-radius: 8px; height: 32px; overflow: hidden; position: relative; }
  .progress-bar { height: 100%; border-radius: 8px; transition: width 1s ease; display: flex; align-items: center; padding-left: 12px; font-size: 13px; font-weight: 600; min-width: 40px; }
  .bar-revenue { background: linear-gradient(90deg, #2563eb, #3b82f6); }
  .bar-corp { background: linear-gradient(90deg, #16a34a, #4ade80); }
  .quota-section { padding: 0 32px 24px; }
  .quota-card { background: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 20px; }
  .quota-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 12px; }
  .quota-bar-wrap { background: #27272a; border-radius: 6px; height: 24px; overflow: hidden; }
  .quota-bar { height: 100%; border-radius: 6px; transition: width 1s ease; }
  .quota-bar.safe { background: #16a34a; }
  .quota-bar.warn { background: #eab308; }
  .quota-bar.danger { background: #dc2626; }
  .error-banner { background: #dc262622; border: 1px solid #dc262644; color: #f87171; padding: 12px 32px; font-size: 14px; }
</style>
</head>
<body>

<div class="header">
  <h1>Seed Progress Monitor</h1>
  <span id="badge-rev" class="badge badge-dead">매출액: —</span>
  <span id="badge-corp" class="badge badge-dead">기본정보: —</span>
  <span class="updated" id="updated">—</span>
  <span class="countdown" id="countdown"></span>
</div>

<div id="error-banner" class="error-banner" style="display:none"></div>

<div class="grid">
  <div class="card">
    <div class="card-label">전체 기업</div>
    <div class="card-value" id="total">—</div>
    <div class="card-sub">jurir_no 보유 기업</div>
  </div>
  <div class="card">
    <div class="card-label">매출액 수집</div>
    <div class="card-value"><span id="rev-count">—</span> <span class="pct" id="rev-pct"></span></div>
    <div class="card-sub" id="rev-api">API 호출: —</div>
  </div>
  <div class="card">
    <div class="card-label">기본정보 수집</div>
    <div class="card-value"><span id="corp-count">—</span> <span class="pct" id="corp-pct"></span></div>
    <div class="card-sub" id="corp-api">API 호출: —</div>
  </div>
  <div class="card">
    <div class="card-label">예상 완료</div>
    <div class="card-value" id="eta" style="font-size:20px">계산중...</div>
    <div class="card-sub" id="eta-sub"></div>
  </div>
</div>

<div class="progress-row">
  <div>
    <div style="font-size:13px;color:#a1a1aa;margin-bottom:6px">매출액 진행률</div>
    <div class="progress-bar-wrap">
      <div class="progress-bar bar-revenue" id="bar-rev" style="width:0%">0%</div>
    </div>
  </div>
  <div>
    <div style="font-size:13px;color:#a1a1aa;margin-bottom:6px">기본정보 진행률</div>
    <div class="progress-bar-wrap">
      <div class="progress-bar bar-corp" id="bar-corp" style="width:0%">0%</div>
    </div>
  </div>
</div>

<div class="charts">
  <div class="chart-card">
    <h3>DB 적재 추이</h3>
    <canvas id="chartDB"></canvas>
  </div>
  <div class="chart-card">
    <h3>API 호출 추이</h3>
    <canvas id="chartAPI"></canvas>
  </div>
</div>

<div class="quota-section">
  <div class="quota-card">
    <h3 style="font-size:15px;color:#a1a1aa">일일 API 한도 (100,000건/서비스)</h3>
    <div class="quota-grid">
      <div>
        <div style="font-size:13px;color:#71717a;margin-bottom:6px">매출액 API — <span id="rev-quota-text">0%</span></div>
        <div class="quota-bar-wrap">
          <div class="quota-bar safe" id="rev-quota-bar" style="width:0%"></div>
        </div>
      </div>
      <div>
        <div style="font-size:13px;color:#71717a;margin-bottom:6px">기본정보 API — <span id="corp-quota-text">0%</span></div>
        <div class="quota-bar-wrap">
          <div class="quota-bar safe" id="corp-quota-bar" style="width:0%"></div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
const DAILY_LIMIT = 100000;
const POLL_MS = 15000;
let chartDB = null, chartAPI = null;
let nextPoll = 0;

function initCharts() {
  if (typeof Chart === 'undefined') { setTimeout(initCharts, 200); return; }
  const commonOpts = {
    responsive: true,
    animation: { duration: 500 },
    scales: {
      x: { ticks: { color: '#71717a', maxTicksLimit: 15 }, grid: { color: '#27272a' } },
      y: { ticks: { color: '#71717a' }, grid: { color: '#27272a' } }
    },
    plugins: { legend: { labels: { color: '#a1a1aa' } } }
  };
  chartDB = new Chart(document.getElementById('chartDB'), {
    type: 'line',
    data: { labels: [], datasets: [
      { label: '매출액', data: [], borderColor: '#3b82f6', backgroundColor: '#3b82f622', fill: true, tension: 0.3, pointRadius: 2 },
      { label: '기본정보', data: [], borderColor: '#4ade80', backgroundColor: '#4ade8022', fill: true, tension: 0.3, pointRadius: 2 }
    ]},
    options: commonOpts
  });
  chartAPI = new Chart(document.getElementById('chartAPI'), {
    type: 'line',
    data: { labels: [], datasets: [
      { label: '매출액 API', data: [], borderColor: '#f59e0b', tension: 0.3, pointRadius: 2 },
      { label: '기본정보 API', data: [], borderColor: '#a78bfa', tension: 0.3, pointRadius: 2 }
    ]},
    options: commonOpts
  });
  console.log('[Monitor] Charts initialized');
  poll();
}

function fmt(n) { return n != null ? n.toLocaleString('ko-KR') : '—'; }

function updateUI(d) {
  console.log('[Monitor] updateUI', d.revenue_count, d.corp_basic_count);
  const errEl = document.getElementById('error-banner');
  if (d.error) { errEl.style.display = 'block'; errEl.textContent = d.error; }
  else { errEl.style.display = 'none'; }

  const bRev = document.getElementById('badge-rev');
  const bCorp = document.getElementById('badge-corp');
  bRev.className = 'badge ' + (d.revenue_process_alive ? 'badge-live' : 'badge-dead');
  bRev.textContent = '매출액: ' + (d.revenue_process_alive ? '실행중' : '중지');
  bCorp.className = 'badge ' + (d.corp_basic_process_alive ? 'badge-live' : 'badge-dead');
  bCorp.textContent = '기본정보: ' + (d.corp_basic_process_alive ? '실행중' : '중지');
  document.getElementById('updated').textContent = d.last_updated || '—';

  const total = d.total_companies || 1;
  document.getElementById('total').textContent = fmt(total);
  document.getElementById('rev-count').textContent = fmt(d.revenue_count);
  document.getElementById('corp-count').textContent = fmt(d.corp_basic_count);
  const revPct = (d.revenue_count / total * 100).toFixed(1);
  const corpPct = (d.corp_basic_count / total * 100).toFixed(1);
  document.getElementById('rev-pct').textContent = revPct + '%';
  document.getElementById('corp-pct').textContent = corpPct + '%';
  document.getElementById('rev-api').textContent = 'API: ' + fmt(d.revenue_api_calls);
  document.getElementById('corp-api').textContent = 'API: ' + fmt(d.corp_basic_api_calls);

  document.getElementById('bar-rev').style.width = Math.max(parseFloat(revPct), 1) + '%';
  document.getElementById('bar-rev').textContent = revPct + '%';
  document.getElementById('bar-corp').style.width = Math.max(parseFloat(corpPct), 1) + '%';
  document.getElementById('bar-corp').textContent = corpPct + '%';

  // ETA
  const hist = d.history || [];
  if (hist.length >= 4) {
    const span = Math.min(hist.length, 20);
    const old = hist[hist.length - span], now = hist[hist.length - 1];
    const secs = span * 30;
    const revRate = (now.revenue_count - old.revenue_count) / secs * 3600;
    const corpRate = (now.corp_basic_count - old.corp_basic_count) / secs * 3600;
    const revRemain = total - d.revenue_count;
    const corpRemain = total - d.corp_basic_count;
    const revHrs = revRate > 0 ? (revRemain / revRate).toFixed(1) : '—';
    const corpHrs = corpRate > 0 ? (corpRemain / corpRate).toFixed(1) : '—';
    document.getElementById('eta').textContent = '매출 ' + revHrs + 'h / 기본 ' + corpHrs + 'h';
    document.getElementById('eta-sub').textContent = '속도: 매출 ' + fmt(Math.round(revRate)) + '/h, 기본 ' + fmt(Math.round(corpRate)) + '/h';
  }

  // quota
  const revQ = (d.revenue_api_calls / DAILY_LIMIT * 100).toFixed(1);
  const corpQ = (d.corp_basic_api_calls / DAILY_LIMIT * 100).toFixed(1);
  document.getElementById('rev-quota-text').textContent = fmt(d.revenue_api_calls) + ' / ' + fmt(DAILY_LIMIT) + ' (' + revQ + '%)';
  document.getElementById('corp-quota-text').textContent = fmt(d.corp_basic_api_calls) + ' / ' + fmt(DAILY_LIMIT) + ' (' + corpQ + '%)';
  const rqB = document.getElementById('rev-quota-bar');
  const cqB = document.getElementById('corp-quota-bar');
  rqB.style.width = Math.min(parseFloat(revQ), 100) + '%';
  cqB.style.width = Math.min(parseFloat(corpQ), 100) + '%';
  rqB.className = 'quota-bar ' + (revQ > 90 ? 'danger' : revQ > 70 ? 'warn' : 'safe');
  cqB.className = 'quota-bar ' + (corpQ > 90 ? 'danger' : corpQ > 70 ? 'warn' : 'safe');

  // charts
  if (chartDB && chartAPI) {
    const labels = hist.map(h => h.ts);
    chartDB.data.labels = labels;
    chartDB.data.datasets[0].data = hist.map(h => h.revenue_count);
    chartDB.data.datasets[1].data = hist.map(h => h.corp_basic_count);
    chartDB.update('none');
    chartAPI.data.labels = labels;
    chartAPI.data.datasets[0].data = hist.map(h => h.revenue_api);
    chartAPI.data.datasets[1].data = hist.map(h => h.corp_api);
    chartAPI.update('none');
  }
}

async function poll() {
  try {
    const r = await fetch('/api/stats?' + Date.now());
    const d = await r.json();
    updateUI(d);
  } catch (e) {
    console.error('[Monitor] fetch error', e);
    document.getElementById('error-banner').style.display = 'block';
    document.getElementById('error-banner').textContent = 'fetch error: ' + e.message;
  }
  nextPoll = Date.now() + POLL_MS;
}

// countdown ticker
setInterval(() => {
  const left = Math.max(0, Math.ceil((nextPoll - Date.now()) / 1000));
  document.getElementById('countdown').textContent = '(갱신 ' + left + 's)';
}, 1000);

// main loop
window.addEventListener('load', () => { initCharts(); setInterval(poll, POLL_MS); });
</script>
</body>
</html>"""


class MonitorHandler(SimpleHTTPRequestHandler):
    """로컬 모니터링 HTTP 핸들러."""

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
        elif self.path == "/api/stats":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps(state, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        """콘솔 로그 최소화."""
        pass


def main() -> None:
    """모니터링 서버 시작."""
    print("=" * 50)
    print("  Seed Progress Monitor")
    print("=" * 50)
    print(f"  대시보드: http://localhost:{PORT}")
    print(f"  폴링 간격: {POLL_INTERVAL}초")
    print(f"  SSH 대상: {SSH_HOST}")
    print("=" * 50)
    print()

    # 초기 데이터 수집
    print("  초기 데이터 수집 중...")
    collect_stats()
    if state["error"]:
        print(f"  ⚠ 경고: {state['error']}")
    else:
        print(f"  전체 기업: {state['total_companies']:,}")
        print(f"  매출액: {state['revenue_count']:,}")
        print(f"  기본정보: {state['corp_basic_count']:,}")
    print()

    # 백그라운드 폴링 시작
    t = threading.Thread(target=poll_loop, daemon=True)
    t.start()
    print(f"  서버 시작: http://localhost:{PORT}")
    print("  종료: Ctrl+C")
    print()

    server = HTTPServer(("0.0.0.0", PORT), MonitorHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  모니터링 종료.")
        server.shutdown()


if __name__ == "__main__":
    main()
