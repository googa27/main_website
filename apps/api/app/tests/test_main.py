import sys
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

# Ensure the app package is importable when running tests from repo root
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.main import app
from app.core.config import settings

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Welcome to the Portfolio API"})

    def test_projects_prefix_uses_setting(self):
        response = self.client.get(f"{settings.API_V1_STR}/projects")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

if __name__ == "__main__":
    unittest.main()
