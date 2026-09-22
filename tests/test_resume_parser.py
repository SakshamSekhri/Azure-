from backend.app.utils.text_extractor import extract_text_from_file, compute_file_hash
from backend.app.services.resume_service import ResumeService


def test_text_extractor_txt():
    sample_text = "John Doe\nPython, FastAPI, SQL Engineer\nBuilt E-Commerce Microservices."
    bytes_data = sample_text.encode("utf-8")
    extracted = extract_text_from_file(bytes_data, "resume.txt")
    assert "John Doe" in extracted
    assert "FastAPI" in extracted

    h1 = compute_file_hash(bytes_data)
    h2 = compute_file_hash(bytes_data)
    assert h1 == h2


def test_resume_upload_and_analysis(db_session, test_user):
    sample_text = "Alice Smith\nSkills: Python, SQL, Docker, FastAPI\nProjects: Cloud REST API in FastAPI and PostgreSQL."
    bytes_data = sample_text.encode("utf-8")

    resume = ResumeService.upload_resume(
        db=db_session,
        user_id=test_user.id,
        file_bytes=bytes_data,
        filename="alice_resume.txt"
    )

    assert resume.id is not None
    assert resume.version == 1
    assert "Alice Smith" in resume.raw_text

    # Analyze Resume
    analyzed = ResumeService.analyze_resume(
        db=db_session,
        user_id=test_user.id,
        resume_id=resume.id
    )

    assert analyzed.parsed_data is not None
    skills = [s["name"] for s in analyzed.parsed_data.get("skills", [])]
    assert "Python" in skills or "SQL" in skills

    # Second analysis call must reuse parsed data (credit-control check)
    reanalyzed = ResumeService.analyze_resume(
        db=db_session,
        user_id=test_user.id,
        resume_id=resume.id,
        force_refresh=False
    )
    assert reanalyzed.parsed_data == analyzed.parsed_data
