import pytest
from fastapi.testclient import TestClient
from backend.app.models.user import User
from backend.app.models.resume import Resume
from backend.app.models.job import JobDescription
from backend.app.config.settings import settings


def test_resume_synchronization_and_metadata_flow(client, auth_headers, test_user, db_session):
    """Verify that uploading a resume makes it immediately visible to both /resume/latest
    and /profile, with has_content=True, without requiring prior AI analysis.
    """
    # 1. Initially, no resume exists
    res_prof_init = client.get("/api/v1/profile", headers=auth_headers)
    assert res_prof_init.status_code == 200
    prof_data_init = res_prof_init.json()
    assert prof_data_init["active_resume"] is None
    assert prof_data_init["active_job"] is None

    res_latest_init = client.get("/api/v1/resume/latest", headers=auth_headers)
    assert res_latest_init.status_code == 404

    # 2. Upload resume (plain text file)
    resume_content = b"Alex Chen - Python, FastAPI, Docker, Microservices. Built high-concurrency APIs."
    files = {"file": ("AlexChen-Resume.txt", resume_content, "text/plain")}
    upload_res = client.post("/api/v1/resume/upload", headers=auth_headers, files=files)
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["filename"] == "AlexChen-Resume.txt"
    assert upload_data["version"] == 1
    assert upload_data["raw_text"] is not None
    assert "Alex Chen" in upload_data["raw_text"]
    assert upload_data["has_content"] is True
    assert upload_data["has_intelligence"] is False

    # 3. GET /resume/latest MUST return raw_text and has_content=True
    res_latest = client.get("/api/v1/resume/latest", headers=auth_headers)
    assert res_latest.status_code == 200
    latest_data = res_latest.json()
    assert latest_data["filename"] == "AlexChen-Resume.txt"
    assert latest_data["version"] == 1
    assert latest_data["has_content"] is True
    assert latest_data["raw_text"] is not None
    assert len(latest_data["raw_text"]) > 0
    # Before AI analysis, intelligence is False, but resume exists!
    assert latest_data["has_intelligence"] is False

    # 4. GET /profile MUST contain active_resume with exact metadata
    res_prof = client.get("/api/v1/profile", headers=auth_headers)
    assert res_prof.status_code == 200
    prof_data = res_prof.json()
    active_res = prof_data.get("active_resume")
    assert active_res is not None
    assert active_res["filename"] == "AlexChen-Resume.txt"
    assert active_res["version"] == 1
    assert active_res["has_content"] is True
    assert active_res["has_intelligence"] is False

    # 5. Create Job Description
    job_payload = {
        "title": "Backend Systems Engineer",
        "company": "CloudCorp",
        "raw_text": "We are seeking a Backend Systems Engineer proficient in Python, FastAPI, Docker, and distributed systems."
    }
    job_res = client.post("/api/v1/jobs", headers=auth_headers, json=job_payload)
    assert job_res.status_code == 200
    job_data = job_res.json()
    assert job_data["has_content"] is True

    # 6. GET /jobs/latest MUST return has_content=True
    latest_job_res = client.get("/api/v1/jobs/latest", headers=auth_headers)
    assert latest_job_res.status_code == 200
    assert latest_job_res.json()["has_content"] is True

    # 7. GET /profile MUST now have both active_resume AND active_job populated
    res_prof_both = client.get("/api/v1/profile", headers=auth_headers)
    assert res_prof_both.status_code == 200
    prof_both = res_prof_both.json()
    assert prof_both["active_resume"] is not None
    assert prof_both["active_job"] is not None
    assert prof_both["active_job"]["title"] == "Backend Systems Engineer"
    assert prof_both["active_job"]["has_content"] is True

    # 8. Verify candidate state boolean checks as evaluated on frontend
    resume_dict = latest_data
    job_dict = latest_job_res.json()

    # The frontend evaluation:
    has_resume = (
        resume_dict is not None
        and (
            bool(resume_dict.get("has_content"))
            or bool(resume_dict.get("raw_text"))
            or bool(resume_dict.get("id"))
            or bool(resume_dict.get("filename"))
        )
    )
    has_job = (
        job_dict is not None
        and (
            bool(job_dict.get("has_content"))
            or bool(job_dict.get("raw_text"))
            or bool(job_dict.get("id"))
            or bool(job_dict.get("title"))
        )
    )
    assert has_resume is True, "has_resume must be True after upload!"
    assert has_job is True, "has_job must be True after job creation!"
    assert (has_resume and has_job) is True, "Assessment generation must be unlocked!"


def test_database_url_is_absolute_path():
    """Verify that settings.DATABASE_URL resolves to an absolute path."""
    assert "placement_prep.db" in settings.DATABASE_URL
    # Should not start with relative ./
    assert not settings.DATABASE_URL.startswith("sqlite:///./")
    assert settings.DATABASE_URL.startswith("sqlite:///")
