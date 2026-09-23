import pytest
from fastapi import HTTPException
from backend.app.models.profile import StudentProfile
from backend.app.models.resume import Resume
from backend.app.models.job import JobDescription
from backend.app.models.assessment import Assessment
from backend.app.services.assessment_service import AssessmentService
from backend.app.services.job_service import JobService
from backend.app.schemas.ai import AssessmentGenerationResponse, AssessmentMCQItem
from backend.app.ai.foundry_agent import foundry_client


def test_target_job_is_single_source_of_truth_across_platform(client, test_user, auth_headers, db_session, monkeypatch):
    """Verify that the Active Target Job is the single source of truth for the target role
    across Profile, Dashboard, and Assessment services. Legacy profile.target_role ('Full Stack Developer')
    must NEVER override the active Target Job ('Brand Marketing' @ 'Times Of India').
    """
    # 1. Setup candidate profile with old legacy target_role
    profile = db_session.query(StudentProfile).filter(StudentProfile.user_id == test_user.id).first()
    if not profile:
        profile = StudentProfile(
            user_id=test_user.id,
            name="Test Candidate",
            target_role="Full Stack Developer",  # old legacy default
            experience_level="Entry Level"
        )
        db_session.add(profile)
    else:
        profile.target_role = "Full Stack Developer"
    db_session.commit()

    # 2. Upload resume
    resume = Resume(
        user_id=test_user.id,
        filename="marketing_resume.pdf",
        raw_text="Experienced in Content Marketing, Social Media Strategy, and Brand Campaigns.",
        file_hash="marketing_hash_1",
        parsed_data={"skills": [{"name": "Content Marketing"}, {"name": "Social Media Strategy"}]}
    )
    db_session.add(resume)
    db_session.commit()

    # 3. Create Active Target Job: Brand Marketing @ Times Of India
    job1 = JobService.create_job_description(
        db=db_session,
        user_id=test_user.id,
        title="Brand Marketing",
        company="Times Of India",
        raw_text="We are hiring a Brand Marketing Specialist. Requirements: Brand Strategy, Campaign Management, Market Research."
    )
    job1.parsed_data = {
        "required_skills": [{"name": "Brand Strategy"}, {"name": "Campaign Management"}],
        "preferred_skills": [{"name": "Market Research"}]
    }
    db_session.commit()
    db_session.refresh(job1)

    # 4. Verify JobService.get_active_target_job returns Brand Marketing
    active_job = JobService.get_active_target_job(db_session, test_user.id)
    assert active_job is not None
    assert active_job.title == "Brand Marketing"
    assert active_job.company == "Times Of India"

    # 5. Verify Profile API reflects Brand Marketing (NOT 'Full Stack Developer')
    res_prof = client.get("/api/v1/profile", headers=auth_headers)
    assert res_prof.status_code == 200
    prof_data = res_prof.json()
    assert prof_data["target_role"] == "Brand Marketing"
    assert prof_data["active_job"]["title"] == "Brand Marketing"
    assert prof_data["active_job"]["company"] == "Times Of India"

    # 6. Verify Dashboard API reflects Brand Marketing @ Times Of India
    res_dash = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert res_dash.status_code == 200
    dash_data = res_dash.json()
    assert dash_data["target_role"] == "Brand Marketing"
    assert dash_data["target_company"] == "Times Of India"

    # 7. Mock Azure AI Foundry generation for Brand Marketing
    dummy_gen = AssessmentGenerationResponse(
        title="Personalized Brand Marketing Assessment",
        role="Brand Marketing",
        total_questions=2,
        overview="Brand Marketing assessment dynamically synthesized by Azure AI Foundry",
        questions=[
            AssessmentMCQItem(
                id=1,
                question="How do you measure Brand Lift for an omnichannel awareness campaign?",
                options=["Pre-and-post exposure survey comparison", "Counting server requests", "Running a unit test", "Sorting a binary tree"],
                correct_answer="Pre-and-post exposure survey comparison",
                explanation="Brand lift studies compare exposed vs control groups.",
                skill="Brand Strategy",
                difficulty="Intermediate",
                topic="Campaign Analytics",
                why_the_question_is_relevant="Essential competency for Brand Marketing @ Times Of India."
            ),
            AssessmentMCQItem(
                id=2,
                question="What is the primary objective of a market segmentation strategy?",
                options=["Identify high-value audience cohorts for tailored messaging", "Compress image assets", "Compile TypeScript", "Configure Kubernetes pods"],
                correct_answer="Identify high-value audience cohorts for tailored messaging",
                explanation="Segmentation groups audiences by shared characteristics.",
                skill="Market Research",
                difficulty="Intermediate",
                topic="Audience Segmentation",
                why_the_question_is_relevant="Required for Brand Marketing role."
            )
        ]
    )
    monkeypatch.setattr(foundry_client, "execute_operation", lambda *args, **kwargs: (dummy_gen, 400, "LIVE_FOUNDRY"))

    # 8. Generate Personalized Assessment via API (even if role is omitted or differs)
    res_asm = client.post(
        "/api/v1/assessments/personalized/generate",
        headers=auth_headers,
        json={"num_questions": 2}
    )
    assert res_asm.status_code == 200
    asm_data = res_asm.json()
    assert asm_data["role"] == "Brand Marketing"
    assert asm_data["job_id"] == job1.id
    assert "Brand Marketing" in asm_data["title"]
    assert len(asm_data["questions"]) == 2

    # 9. Test Target Job Switching: User switches to Product Manager @ Microsoft
    job2 = JobService.create_job_description(
        db=db_session,
        user_id=test_user.id,
        title="Product Manager",
        company="Microsoft",
        raw_text="Product Manager for Azure Developer Tools. Requirements: Product Roadmap, User Stories, Data-driven Prioritization."
    )
    job2.parsed_data = {
        "required_skills": [{"name": "Product Roadmap"}, {"name": "User Stories"}],
        "preferred_skills": [{"name": "Data-driven Prioritization"}]
    }
    db_session.commit()
    db_session.refresh(job2)

    # 10. Verify seamless role switch on Profile and Dashboard
    res_prof2 = client.get("/api/v1/profile", headers=auth_headers)
    assert res_prof2.status_code == 200
    assert res_prof2.json()["target_role"] == "Product Manager"
    assert res_prof2.json()["active_job"]["title"] == "Product Manager"
    assert res_prof2.json()["active_job"]["company"] == "Microsoft"

    res_dash2 = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert res_dash2.status_code == 200
    assert res_dash2.json()["target_role"] == "Product Manager"
    assert res_dash2.json()["target_company"] == "Microsoft"


def test_personalized_assessment_requires_active_target_job(client, test_user, auth_headers, db_session):
    """Verify that generating an assessment without a target job returns 400 Bad Request."""
    # Delete any existing jobs for this test user
    db_session.query(JobDescription).filter(JobDescription.user_id == test_user.id).delete()
    db_session.commit()

    # Upload resume only
    resume = Resume(
        user_id=test_user.id,
        filename="resume_only.pdf",
        raw_text="Software engineer with general skills.",
        file_hash="hash_only_resume",
        parsed_data={"skills": [{"name": "Python"}]}
    )
    db_session.add(resume)
    db_session.commit()

    res = client.post(
        "/api/v1/assessments/personalized/generate",
        headers=auth_headers,
        json={"num_questions": 5}
    )
    assert res.status_code == 400
    assert "Target Job is required" in res.json().get("detail", "")
