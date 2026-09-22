def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_auth_and_profile_api(client, test_user):
    # Login
    login_res = client.post("/api/v1/auth/login-json", json={
        "email": test_user.email,
        "password": "testpassword123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get Profile
    prof_res = client.get("/api/v1/profile", headers=headers)
    assert prof_res.status_code == 200
    assert prof_res.json()["name"] == "Tester Student"


def test_dashboard_and_ai_usage_api(client, auth_headers):
    # Dashboard summary
    dash_res = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert dash_res.status_code == 200
    data = dash_res.json()
    assert "overall_preparation_score" in data
    assert "recommended_action" in data

    # AI usage summary
    usage_res = client.get("/api/v1/ai/usage", headers=auth_headers)
    assert usage_res.status_code == 200
    usage_data = usage_res.json()
    assert "total_operations" in usage_data
    assert "cache_hit_rate_percentage" in usage_data


def test_rag_learning_api(client, auth_headers):
    # Ask educational grounded question
    rag_res = client.post("/api/v1/learning/ask", headers=auth_headers, json={
        "question": "How do database indexes improve performance in SQL?",
        "topic": "Databases"
    })
    assert rag_res.status_code == 200
    rag_data = rag_res.json()
    assert "answer" in rag_data
    assert "citations" in rag_data
    assert len(rag_data["citations"]) > 0


def test_personalized_assessment_api_flow(client, auth_headers, monkeypatch):
    from backend.app.ai.foundry_agent import foundry_client
    from backend.app.schemas.ai import AssessmentGenerationResponse, AssessmentMCQItem, AssessmentResultAnalysisResponse

    dummy_gen = AssessmentGenerationResponse(
        title="Dynamic Test Assessment",
        role="Backend Engineer",
        total_questions=3,
        overview="Overview",
        questions=[
            AssessmentMCQItem(
                id=1,
                question="Question 1?",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                explanation="Expl 1",
                skill="Python",
                difficulty="Intermediate",
                topic="Core",
                why_the_question_is_relevant="Relevance 1"
            ),
            AssessmentMCQItem(
                id=2,
                question="Question 2?",
                options=["A", "B", "C", "D"],
                correct_answer="B",
                explanation="Expl 2",
                skill="FastAPI",
                difficulty="Intermediate",
                topic="Async",
                why_the_question_is_relevant="Relevance 2"
            ),
            AssessmentMCQItem(
                id=3,
                question="Question 3?",
                options=["A", "B", "C", "D"],
                correct_answer="C",
                explanation="Expl 3",
                skill="SQL",
                difficulty="Intermediate",
                topic="DB",
                why_the_question_is_relevant="Relevance 3"
            )
        ]
    )
    dummy_analysis = AssessmentResultAnalysisResponse(
        role="Backend Engineer",
        strengths=["Python"],
        weaknesses=["FastAPI"],
        skill_gaps=["SQL"],
        topics_to_improve=["Async"],
        priority_areas=["SQL"],
        improvement_plan=["Study Async IO in depth"],
        reassessment_recommendations="Retake in 7 days",
        summary_feedback="Competent profile with targeted areas for improvement."
    )

    def mock_execute(*args, **kwargs):
        op_type = kwargs.get("operation_type") or (args[0] if args else None)
        if op_type == "ASSESSMENT_QUESTION_GENERATION":
            return dummy_gen, 300, "LIVE_FOUNDRY"
        return dummy_analysis, 200, "LIVE_FOUNDRY"

    monkeypatch.setattr(foundry_client, "execute_operation", mock_execute)

    # 1. Generate Personalized Assessment (providing resume & job_description)
    gen_res = client.post("/api/v1/assessments/personalized/generate", headers=auth_headers, json={
        "role": "Backend Engineer",
        "resume": "Experienced Python and FastAPI backend developer.",
        "job_description": "Seeking Python, FastAPI, and SQL developer.",
        "num_questions": 3
    })
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert "id" in gen_data
    assessment_id = gen_data["id"]
    assert len(gen_data["questions"]) == 3

    # Ensure answers and explanations are hidden in public schema
    for q in gen_data["questions"]:
        assert "question" in q
        assert "options" in q
        assert "correct_answer" not in q
        assert "explanation" not in q

    # 2. Submit Assessment Answers
    answers = {str(q["id"]): q["options"][0] for q in gen_data["questions"]}
    sub_res = client.post(f"/api/v1/assessments/{assessment_id}/submit", headers=auth_headers, json={
        "assessment_id": assessment_id,
        "answers": answers
    })
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert "score_percentage" in sub_data
    assert "strengths" in sub_data
    assert "weaknesses" in sub_data
    assert "skill_gaps" in sub_data
    assert "topics_to_improve" in sub_data
    assert "improvement_plan" in sub_data
    assert len(sub_data["improvement_plan"]) > 0
    assert "details" in sub_data
    assert len(sub_data["details"]) > 0
    first_detail = sub_data["details"][0]
    assert "why_the_question_is_relevant" in first_detail

    # 3. Test Result Fetch (Persists across refresh)
    result_res = client.get(f"/api/v1/assessments/{assessment_id}/result", headers=auth_headers)
    assert result_res.status_code == 200
    assert result_res.json()["attempt_id"] == sub_data["attempt_id"]

    # 4. Test Assessment History Endpoint
    hist_res = client.get("/api/v1/assessments/history", headers=auth_headers)
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert len(hist_data) >= 1
    assert hist_data[0]["assessment_id"] == assessment_id

