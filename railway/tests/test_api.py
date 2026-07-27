from fastapi.testclient import TestClient

from railway.app.main import app


def test_health_exposes_configuration_state_without_secrets() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "service": "eye-of-loki-intelligence",
        "version": "2.0.0",
        "model": "gpt-5.6-sol",
        "openai_configured": False,
        "auth_configured": False,
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
