"""Tests for the Flask API input validation and health endpoint."""

import pytest

import api as api_module


@pytest.fixture
def client():
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as test_client:
        yield test_client


class TestHealth:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}


class TestProcess:
    def test_missing_body_returns_400(self, client):
        response = client.post("/process")
        assert response.status_code == 400
        assert "text" in response.get_json()["error"]

    def test_missing_text_returns_400(self, client):
        response = client.post("/process", json={"query": "what is this?"})
        assert response.status_code == 400
        assert "text" in response.get_json()["error"]

    def test_missing_query_returns_400(self, client):
        response = client.post("/process", json={"text": "some document text"})
        assert response.status_code == 400
        assert "query" in response.get_json()["error"]

    def test_non_json_body_returns_400(self, client):
        response = client.post("/process", data="not json", content_type="text/plain")
        assert response.status_code == 400

    def test_valid_request_calls_chain(self, client, monkeypatch):
        monkeypatch.setattr(
            api_module.coa, "process", lambda text, query: f"answer:{query}"
        )
        response = client.post(
            "/process", json={"text": "some document text", "query": "summarize"}
        )
        assert response.status_code == 200
        assert response.get_json() == {"result": "answer:summarize"}


class TestProcessStream:
    def test_missing_pdf_returns_400(self, client):
        response = client.post("/process-stream", data={"query": "hello"})
        assert response.status_code == 400
        assert "PDF" in response.get_json()["error"]

    def test_missing_query_returns_400(self, client):
        response = client.post(
            "/process-stream",
            data={"pdf": (__import__("io").BytesIO(b"%PDF-1.4 fake"), "doc.pdf")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400
        assert "query" in response.get_json()["error"].lower()
