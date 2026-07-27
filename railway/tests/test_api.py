from fastapi.testclient import TestClient

from railway.app.main import app


def test_health_exposes_configuration_state_without_secrets() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "service": "eye-of-loki-intelligence",
        "version": "5.0.0",
        "model": "gemini-3.5-flash-lite",
        "gemini_configured": False,
        "search_configured": False,
        "auth_configured": False,
        "capabilities": ["discovery", "verification", "hunt", "portfolio"],
    }


def test_recon_refuses_requests_until_shared_secret_is_configured() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/recon",
            json={
                "contests": [
                    {
                        "id": 1,
                        "slug": "example",
                        "title": "Example",
                        "organizer": "Example",
                        "prize": "Tickets",
                        "url": "https://example.com/contest",
                        "deadline": "2026-08-01",
                    }
                ]
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "EYE_OF_LOKI_SHARED_SECRET is not configured"
    )


def test_discovery_refuses_requests_until_shared_secret_is_configured() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/discover",
            json={"known_urls": [], "known_titles": [], "round": 0},
        )

    assert response.status_code == 503
