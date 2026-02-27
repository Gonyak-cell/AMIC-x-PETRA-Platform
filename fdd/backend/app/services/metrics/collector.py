"""메트릭 수집 — FDD-1804.

Prometheus 포맷 메트릭 수집 + FastAPI 미들웨어.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class Counter:
    """단조 증가 카운터."""

    name: str
    help: str
    labels: dict[str, int] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def inc(self, label: str = "", amount: int = 1) -> None:
        with self._lock:
            self.labels[label] = self.labels.get(label, 0) + amount

    def get(self, label: str = "") -> int:
        return self.labels.get(label, 0)

    def total(self) -> int:
        return sum(self.labels.values())


@dataclass
class Histogram:
    """히스토그램 (지정된 버킷 기준)."""

    name: str
    help: str
    buckets: tuple[float, ...] = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    _observations: list[float] = field(default_factory=list, repr=False)
    _labels: dict[str, list[float]] = field(default_factory=dict, repr=False)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def observe(self, value: float, label: str = "") -> None:
        with self._lock:
            self._observations.append(value)
            if label not in self._labels:
                self._labels[label] = []
            self._labels[label].append(value)

    def count(self, label: str = "") -> int:
        if label:
            return len(self._labels.get(label, []))
        return len(self._observations)

    def sum(self, label: str = "") -> float:
        if label:
            return sum(self._labels.get(label, []))
        return sum(self._observations)

    def avg(self, label: str = "") -> float:
        c = self.count(label)
        return self.sum(label) / c if c > 0 else 0.0

    def bucket_counts(self) -> dict[str, int]:
        result = {}
        for b in self.buckets:
            result[f"le_{b}"] = sum(1 for v in self._observations if v <= b)
        result["le_inf"] = len(self._observations)
        return result


@dataclass
class Gauge:
    """현재 값 게이지."""

    name: str
    help: str
    _value: float = 0.0
    _labels: dict[str, float] = field(default_factory=dict, repr=False)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def set(self, value: float, label: str = "") -> None:
        with self._lock:
            if label:
                self._labels[label] = value
            else:
                self._value = value

    def inc(self, amount: float = 1.0, label: str = "") -> None:
        with self._lock:
            if label:
                self._labels[label] = self._labels.get(label, 0.0) + amount
            else:
                self._value += amount

    def dec(self, amount: float = 1.0, label: str = "") -> None:
        self.inc(-amount, label)

    def get(self, label: str = "") -> float:
        if label:
            return self._labels.get(label, 0.0)
        return self._value


class MetricsCollector:
    """FDD 메트릭 수집기 (싱글턴)."""

    def __init__(self) -> None:
        self.api_requests_total = Counter(
            name="fdd_api_requests_total",
            help="Total API requests",
        )
        self.api_request_duration = Histogram(
            name="fdd_api_request_duration_seconds",
            help="API request duration in seconds",
        )
        self.jobs_total = Counter(
            name="fdd_jobs_total",
            help="Total jobs by status",
        )
        self.job_duration = Histogram(
            name="fdd_job_duration_seconds",
            help="Job duration in seconds",
            buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
        )
        self.errors_total = Counter(
            name="fdd_errors_total",
            help="Total errors by code",
        )
        self.active_deals = Gauge(
            name="fdd_active_deals",
            help="Number of active deals",
        )
        self.active_jobs = Gauge(
            name="fdd_active_jobs",
            help="Number of currently running jobs",
        )

    def to_prometheus(self) -> str:
        """Prometheus 텍스트 포맷으로 출력한다."""
        lines: list[str] = []

        # api_requests_total
        lines.append(f"# HELP {self.api_requests_total.name} {self.api_requests_total.help}")
        lines.append(f"# TYPE {self.api_requests_total.name} counter")
        for label, value in self.api_requests_total.labels.items():
            label_str = f'{{method="{label}"}}' if label else ""
            lines.append(f"{self.api_requests_total.name}{label_str} {value}")

        # api_request_duration
        lines.append(f"# HELP {self.api_request_duration.name} {self.api_request_duration.help}")
        lines.append(f"# TYPE {self.api_request_duration.name} histogram")
        lines.append(f"{self.api_request_duration.name}_count {self.api_request_duration.count()}")
        lines.append(f"{self.api_request_duration.name}_sum {self.api_request_duration.sum():.6f}")
        for bucket_label, count in self.api_request_duration.bucket_counts().items():
            lines.append(f'{self.api_request_duration.name}_bucket{{{bucket_label.replace("_", "=")}}} {count}')

        # jobs_total
        lines.append(f"# HELP {self.jobs_total.name} {self.jobs_total.help}")
        lines.append(f"# TYPE {self.jobs_total.name} counter")
        for label, value in self.jobs_total.labels.items():
            lines.append(f'{self.jobs_total.name}{{status="{label}"}} {value}')

        # job_duration
        lines.append(f"# HELP {self.job_duration.name} {self.job_duration.help}")
        lines.append(f"# TYPE {self.job_duration.name} histogram")
        lines.append(f"{self.job_duration.name}_count {self.job_duration.count()}")
        lines.append(f"{self.job_duration.name}_sum {self.job_duration.sum():.6f}")

        # errors_total
        lines.append(f"# HELP {self.errors_total.name} {self.errors_total.help}")
        lines.append(f"# TYPE {self.errors_total.name} counter")
        for label, value in self.errors_total.labels.items():
            lines.append(f'{self.errors_total.name}{{code="{label}"}} {value}')

        # active_deals
        lines.append(f"# HELP {self.active_deals.name} {self.active_deals.help}")
        lines.append(f"# TYPE {self.active_deals.name} gauge")
        lines.append(f"{self.active_deals.name} {self.active_deals.get()}")

        # active_jobs
        lines.append(f"# HELP {self.active_jobs.name} {self.active_jobs.help}")
        lines.append(f"# TYPE {self.active_jobs.name} gauge")
        lines.append(f"{self.active_jobs.name} {self.active_jobs.get()}")

        return "\n".join(lines) + "\n"

    def to_dict(self) -> dict[str, Any]:
        """JSON 형식으로 메트릭을 반환한다."""
        return {
            "api_requests_total": dict(self.api_requests_total.labels),
            "api_request_duration": {
                "count": self.api_request_duration.count(),
                "sum": self.api_request_duration.sum(),
                "avg": self.api_request_duration.avg(),
            },
            "jobs_total": dict(self.jobs_total.labels),
            "job_duration": {
                "count": self.job_duration.count(),
                "sum": self.job_duration.sum(),
                "avg": self.job_duration.avg(),
            },
            "errors_total": dict(self.errors_total.labels),
            "active_deals": self.active_deals.get(),
            "active_jobs": self.active_jobs.get(),
        }


# 글로벌 싱글턴
metrics = MetricsCollector()
