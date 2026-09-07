"""PHC-OAUTH-01 — no mock auth backdoors; secrets not embedded in frontend."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_mock_oauth_backdoor_in_connectors():
    text = (ROOT / "backend" / "connectors" / "__init__.py").read_text()
    assert "mock_auth" not in text.lower()
    assert "backdoor" not in text.lower()
    assert "fixture" in text.lower()


def test_frontend_has_no_embedded_secrets():
    for name in ("app.js", "index.html"):
        body = (ROOT / "frontend" / name).read_text()
        assert "CLIENT_SECRET" not in body
        assert "BEGIN PRIVATE KEY" not in body
        assert "ACCESS_TOKEN=" not in body
