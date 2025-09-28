"""Tests for health check endpoint."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_health_check():
    """Test health check endpoint returns 200 OK."""
    client = TestClient(app)
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint():
    """Test that root endpoint exists."""
    client = TestClient(app)

    # This should return 404 since we don't have a root handler
    # but it's good to test the app starts correctly
    response = client.get("/")

    # Should not crash the app
    assert response.status_code in [404, 405]  # Not found or method not allowed