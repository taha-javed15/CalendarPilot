from fastapi.testclient import TestClient
from app.main import app

# raise_server_exceptions=False so we can assert on the global exception
# handler's response instead of pytest re-raising the underlying error.
client = TestClient(app, raise_server_exceptions=False)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_happy_path(monkeypatch):
    monkeypatch.setattr("app.main.run_agent", lambda message, session_id: "Sure, I can help with that.")

    response = client.post("/chat", json={"message": "hi", "session_id": "abc"})

    assert response.status_code == 200
    assert response.json() == {"response": "Sure, I can help with that."}


def test_chat_endpoint_unhandled_exception_returns_generic_500(monkeypatch):
    def boom(message, session_id):
        raise RuntimeError("something exploded deep inside a workflow")

    monkeypatch.setattr("app.main.run_agent", boom)

    response = client.post("/chat", json={"message": "hi", "session_id": "abc"})

    assert response.status_code == 500
    body = response.json()
    # must never leak the raw exception message to the client
    assert "exploded" not in body["response"]
    assert "went wrong" in body["response"].lower()


def test_chat_endpoint_validates_request_body():
    response = client.post("/chat", json={"message": "hi"})  # missing session_id
    assert response.status_code == 422
