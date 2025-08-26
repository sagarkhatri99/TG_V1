import httpx
import pytest

def test_health_check():
    response = httpx.get("http://localhost:8000/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "2.0.0"}
