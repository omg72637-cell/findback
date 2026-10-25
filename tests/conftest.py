"""
Pytest Test Fixtures for FindBack 2.0

Provides reusable test client and isolated temporary database fixtures.
"""

import pytest
from app import create_app
from database.db import init_db_schema

@pytest.fixture
def app(tmp_path):
    """Create a Flask application instance configured with an isolated test database."""
    db_path = str(tmp_path / "test_findback.db")
    test_config = {
        "TESTING": True,
        "SECRET_KEY": "test-key-32-chars-long-for-pytest-execution",
        "DATABASE": db_path,
    }
    app = create_app(test_config=test_config)
    with app.app_context():
        init_db_schema()
    yield app

@pytest.fixture
def client(app):
    """A test client for sending simulated HTTP requests."""
    return app.test_client()
