"""Smoke test de rendu Streamlit sans services gRPC démarrés."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_dashboard_renders_when_services_are_offline():
    app_path = Path(__file__).resolve().parents[1] / "ui_app.py"
    app = AppTest.from_file(str(app_path), default_timeout=10).run()
    assert not app.exception
    assert any("Clinique Espoir" in element.value for element in app.title)
    assert any("Hors ligne" in element.value for element in app.markdown)
