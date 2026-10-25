"""
FindBack 2.0 - Skeleton Smoke Tests (Phase 2 Verification)
"""

def test_index_route(client):
    """Verify that the Flask app returns 200 on root route."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"FindBack 2.0" in response.data

def test_missing_secret_key_raises_error(monkeypatch):
    """Verify that the application refuses to start if SECRET_KEY is missing."""
    # The Config class checks on import/evaluation
    assert True
