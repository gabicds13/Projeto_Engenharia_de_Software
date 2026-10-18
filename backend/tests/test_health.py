"""Testes dos health checks e do correlation id (Requisito 7.1, 7.2)."""
from __future__ import annotations


def test_health_liveness(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_readiness(client):
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


def test_correlation_id_header_is_returned(client):
    r = client.get("/health")
    assert "X-Correlation-ID" in r.headers
    assert r.headers["X-Correlation-ID"]


def test_correlation_id_is_echoed_when_provided(client):
    r = client.get("/health", headers={"X-Correlation-ID": "abc-123"})
    assert r.headers["X-Correlation-ID"] == "abc-123"
