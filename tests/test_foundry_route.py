from backend.app.config.settings import settings


def test_assessment_start_validation(client):
    # Test empty payload returns 422 Unprocessable Entity
    res = client.post("/api/assessment/start", json={})
    assert res.status_code == 422

    # Test blank fields return 400 Bad Request
    res2 = client.post("/api/assessment/start", json={
        "role": "",
        "job_description": "",
        "resume": ""
    })
    assert res2.status_code == 400
    assert "non-empty" in res2.json()["detail"]


def test_assessment_start_missing_endpoint_error(client):
    original_endpoint = settings.FOUNDRY_PROJECT_ENDPOINT
    settings.FOUNDRY_PROJECT_ENDPOINT = ""
    try:
        res = client.post("/api/assessment/start", json={
            "role": "Backend Developer",
            "job_description": "Python, FastAPI, PostgreSQL, Docker, AWS",
            "resume": "Python, FastAPI, MongoDB, React"
        })
        assert res.status_code == 500
        assert "FOUNDRY_PROJECT_ENDPOINT" in res.json()["detail"]
    finally:
        settings.FOUNDRY_PROJECT_ENDPOINT = original_endpoint


def test_assessment_start_unauthenticated_error(client, monkeypatch):
    from azure.core.exceptions import ClientAuthenticationError
    from backend.app.ai.foundry_agent import foundry_client

    def mock_execute(*args, **kwargs):
        raise ClientAuthenticationError("Authentication failed in Azure AI Foundry.")

    monkeypatch.setattr(foundry_client, "execute_operation", mock_execute)
    res = client.post("/api/assessment/start", json={
        "role": "Backend Developer",
        "job_description": "Python, FastAPI, PostgreSQL, Docker, AWS",
        "resume": "Python, FastAPI, MongoDB, React"
    })
    assert res.status_code in [401, 502]
    assert "authentication" in res.json()["detail"].lower() or "foundry" in res.json()["detail"].lower()


def test_foundry_agent_json_extraction():
    from backend.app.ai.foundry_agent import foundry_client
    # 1. Direct JSON string
    assert foundry_client._extract_and_parse_json('{"key": "value"}') == {"key": "value"}
    # 2. Markdown fenced code block
    fenced = '```json\n{"candidate_name": "Alice", "summary": "Dev"}\n```'
    assert foundry_client._extract_and_parse_json(fenced)["candidate_name"] == "Alice"
    # 3. Outer braces with surrounding text
    surrounded = 'Here is the requested output:\n{"status": "ok"}\nHope this helps!'
    assert foundry_client._extract_and_parse_json(surrounded) == {"status": "ok"}
