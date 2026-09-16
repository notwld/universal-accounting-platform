"""Prometheus-style counters (MD §76). No scrape server required — export via /metrics."""

from collections import defaultdict
from threading import Lock

_lock = Lock()
_counters: dict[str, float] = defaultdict(float)


def incr(name: str, value: float = 1.0, **labels):
    key = name
    if labels:
        parts = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        key = f"{name}{{{parts}}}"
    with _lock:
        _counters[key] += value


def render_prometheus() -> str:
    lines = []
    with _lock:
        for key, value in sorted(_counters.items()):
            lines.append(f"{key} {value}")
    return "\n".join(lines) + ("\n" if lines else "")


# Convenience aliases matching MD naming
def auth_bootstrap_total():
    incr("auth_bootstrap_total")


def auth_jwt_verify_fail(reason: str):
    incr("auth_jwt_verify_fail_total", reason=reason)
