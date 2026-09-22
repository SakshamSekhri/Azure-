from backend.app.services.job_service import JobService


def test_job_service_creation_and_analysis(db_session, test_user):
    jd_text = (
        "Senior Backend Engineer at CloudTech.\n"
        "Requirements: Must have strong proficiency in Python, FastAPI, and SQL.\n"
        "Nice to have: Docker, AWS, and Git."
    )

    job = JobService.create_job_description(
        db=db_session,
        user_id=test_user.id,
        title="Senior Backend Engineer",
        company="CloudTech",
        raw_text=jd_text
    )

    assert job.id is not None
    assert job.title == "Senior Backend Engineer"

    # Analyze Job Description
    analyzed = JobService.analyze_job_description(
        db=db_session,
        user_id=test_user.id,
        job_id=job.id
    )

    assert analyzed.parsed_data is not None
    req_skills = [s["name"] for s in analyzed.parsed_data.get("required_skills", [])]
    assert len(req_skills) > 0
