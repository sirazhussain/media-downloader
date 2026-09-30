"""API-level tests using FastAPI's TestClient. No real network calls."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_health_returns_ok() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_info_rejects_garbage_url_with_envelope() -> None:
    response = client.post("/api/v1/media/info", json={"url": "not a url"})
    assert response.status_code in (400, 422)
    body = response.json()
    assert "error" in body
    assert body["error"]["code"]
    assert body["error"]["message"]


def test_info_rejects_unsupported_domain() -> None:
    response = client.post(
        "/api/v1/media/info", json={"url": "https://vimeo.com/12345"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNSUPPORTED_PLATFORM"


def test_info_rejects_localhost_ssrf() -> None:
    response = client.post(
        "/api/v1/media/info", json={"url": "http://localhost:8000/secret"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SSRF_BLOCKED"


def test_info_rejects_missing_url_field() -> None:
    response = client.post("/api/v1/media/info", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_download_rejects_bad_scheme() -> None:
    response = client.post(
        "/api/v1/media/download",
        json={"url": "ftp://example.com/video.mp4", "format_id": "18"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_URL"


def test_download_rejects_missing_format_id() -> None:
    response = client.post(
        "/api/v1/media/download",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_download_rejects_private_ip_literal() -> None:
    response = client.post(
        "/api/v1/media/download",
        json={"url": "http://192.168.1.1/video.mp4", "format_id": "18"},
    )
    assert response.status_code == 400
    assert "error" in response.json()


def test_unknown_route_returns_json_404() -> None:
    response = client.get("/api/v1/nope")
    assert response.status_code == 404
