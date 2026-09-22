from backend.app.services.github_service import GitHubService
from backend.app.models.evidence import Evidence


def test_github_service_bounded_evidence(db_session, test_user, monkeypatch):
    mock_repos = [
        {"name": "hello-world", "language": "Python", "description": "A sample python repo"},
        {"name": "fastapi-demo", "language": "Python", "description": "FastAPI with Docker"}
    ]
    monkeypatch.setattr(GitHubService, "_fetch_public_repos", lambda username: mock_repos)
    monkeypatch.setattr(GitHubService, "_fetch_readme_snippet", lambda username, repo: "Sample readme mentioning FastAPI and Docker")

    result = GitHubService.analyze_user_github(
        db=db_session,
        user_id=test_user.id,
        username="octocat"
    )

    assert result.username == "octocat"
    assert result.total_repos_inspected <= 10
    assert len(result.primary_languages) > 0

    # Ensure evidence was saved
    evidences = db_session.query(Evidence).filter(
        Evidence.user_id == test_user.id,
        Evidence.type == "GitHub"
    ).all()
    assert len(evidences) > 0

    # Verify that evidence strength does not exceed supporting limit (0.6)
    for ev in evidences:
        assert ev.evidence_strength <= 0.6
