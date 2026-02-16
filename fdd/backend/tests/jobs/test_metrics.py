"""메트릭 수집 테스트 — FDD-1804."""

import pytest

from app.services.metrics.collector import Counter, Gauge, Histogram, MetricsCollector


# ── Counter ────────────────────────────────────────────


def test_counter_inc():
    c = Counter(name="test", help="test counter")
    c.inc("GET")
    c.inc("GET")
    c.inc("POST")
    assert c.get("GET") == 2
    assert c.get("POST") == 1
    assert c.total() == 3


def test_counter_inc_amount():
    c = Counter(name="test", help="test")
    c.inc("err", amount=5)
    assert c.get("err") == 5


def test_counter_get_missing():
    c = Counter(name="test", help="test")
    assert c.get("nonexistent") == 0


# ── Histogram ──────────────────────────────────────────


def test_histogram_observe():
    h = Histogram(name="test", help="test histogram")
    h.observe(0.1)
    h.observe(0.5)
    h.observe(1.5)
    assert h.count() == 3
    assert abs(h.sum() - 2.1) < 0.001


def test_histogram_avg():
    h = Histogram(name="test", help="test")
    h.observe(1.0)
    h.observe(3.0)
    assert h.avg() == 2.0


def test_histogram_avg_empty():
    h = Histogram(name="test", help="test")
    assert h.avg() == 0.0


def test_histogram_buckets():
    h = Histogram(name="test", help="test", buckets=(0.1, 1.0, 10.0))
    h.observe(0.05)
    h.observe(0.5)
    h.observe(5.0)
    buckets = h.bucket_counts()
    assert buckets["le_0.1"] == 1
    assert buckets["le_1.0"] == 2
    assert buckets["le_10.0"] == 3
    assert buckets["le_inf"] == 3


def test_histogram_labels():
    h = Histogram(name="test", help="test")
    h.observe(1.0, "GET")
    h.observe(2.0, "POST")
    h.observe(3.0, "GET")
    assert h.count("GET") == 2
    assert h.sum("GET") == 4.0


# ── Gauge ──────────────────────────────────────────────


def test_gauge_set():
    g = Gauge(name="test", help="test gauge")
    g.set(42.0)
    assert g.get() == 42.0


def test_gauge_inc_dec():
    g = Gauge(name="test", help="test")
    g.inc(5.0)
    g.inc(3.0)
    g.dec(2.0)
    assert g.get() == 6.0


def test_gauge_labels():
    g = Gauge(name="test", help="test")
    g.set(10.0, "running")
    g.set(5.0, "pending")
    assert g.get("running") == 10.0
    assert g.get("pending") == 5.0
    assert g.get("missing") == 0.0


# ── MetricsCollector ───────────────────────────────────


def test_metrics_collector_init():
    m = MetricsCollector()
    assert m.api_requests_total is not None
    assert m.jobs_total is not None
    assert m.errors_total is not None


def test_metrics_to_dict():
    m = MetricsCollector()
    m.api_requests_total.inc("GET")
    m.active_deals.set(5)
    d = m.to_dict()
    assert d["api_requests_total"]["GET"] == 1
    assert d["active_deals"] == 5.0


def test_metrics_to_prometheus():
    m = MetricsCollector()
    m.api_requests_total.inc("GET", 10)
    m.errors_total.inc("9001", 2)
    output = m.to_prometheus()
    assert "fdd_api_requests_total" in output
    assert "fdd_errors_total" in output
    assert "# HELP" in output
    assert "# TYPE" in output


# ── Metrics API endpoints ──────────────────────────────


def test_metrics_endpoint(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "fdd_api_requests_total" in resp.text


def test_metrics_json_endpoint(client):
    resp = client.get("/metrics/json")
    assert resp.status_code == 200
    data = resp.json()
    assert "api_requests_total" in data
    assert "jobs_total" in data
