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
    assert "recent_assessment_results" in data
    assert "recent_practice_results" in data
    assert "target_company" in data

    # AI usage summary
    usage_res = client.get("/api/v1/ai/usage", headers=auth_headers)
    assert usage_res.status_code == 200
    usage_data = usage_res.json()
    assert "total_operations" in usage_data
    assert "cache_hit_rate_percentage" in usage_data


def test_rag_learning_api(client, auth_headers):
    # Ask educational grounded question (Tier 1: Grounded in indexed documentation)
    rag_res = client.post("/api/v1/learning/ask", headers=auth_headers, json={
        "question": "How do database indexes improve performance in SQL?",
        "topic": "Databases"
    })
    assert rag_res.status_code == 200
    rag_data = rag_res.json()
    assert "answer" in rag_data
    assert "citations" in rag_data
    assert len(rag_data["citations"]) > 0


def test_rag_learning_api_tier2_and_tier3(client, auth_headers, monkeypatch):
    from backend.app.ai.foundry_agent import foundry_client
    from backend.app.schemas.ai import RAGAnswerResponse

    # 1. Tier 2 test: Unindexed technical question (Synthesized from core curriculum)
    dummy_tier2 = RAGAnswerResponse(
        question="What is WebAssembly and how does it execute in the browser?",
        answer="WebAssembly (WASM) is a low-level binary format executing near native speed.",
        grounded=False,
        citations=[],
        confidence="Medium"
    )
    monkeypatch.setattr(
        foundry_client,
        "execute_operation",
        lambda operation_type, payload, response_model: (dummy_tier2, 120, "LIVE_FOUNDRY")
    )

    t2_res = client.post("/api/v1/learning/ask", headers=auth_headers, json={
        "question": "What is WebAssembly and how does it execute in the browser?",
        "topic": "Frontend Development"
    })
    assert t2_res.status_code == 200
    t2_data = t2_res.json()
    assert t2_data["grounded"] is False
    assert t2_data["confidence"] == "Medium"
    assert len(t2_data["citations"]) == 0
    assert "WebAssembly" in t2_data["answer"]

    # 2. Tier 3 test: Off-topic non-technical query (Rejected by guardrail)
    dummy_tier3 = RAGAnswerResponse(
        question="What is the best recipe for Margherita pizza?",
        answer="I am a Placement Preparation Assistant focused on Software Engineering. I cannot assist with recipes.",
        grounded=False,
        citations=[],
        confidence="None"
    )
    monkeypatch.setattr(
        foundry_client,
        "execute_operation",
        lambda operation_type, payload, response_model: (dummy_tier3, 50, "LIVE_FOUNDRY")
    )

    t3_res = client.post("/api/v1/learning/ask", headers=auth_headers, json={
        "question": "What is the best recipe for Margherita pizza?",
        "topic": "General"
    })
    assert t3_res.status_code == 200
    t3_data = t3_res.json()
    assert t3_data["grounded"] is False
    assert t3_data["confidence"] == "None"
    assert len(t3_data["citations"]) == 0



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
                question="What is the average time complexity of looking up a key in a Python dictionary?",
                options=["O(1) average time", "O(n) linear search", "O(log n) tree search", "O(n^2) quadratic search"],
                correct_answer="O(1) average time",
                explanation="Dictionaries in Python are hash tables offering O(1) lookups.",
                skill="Python",
                difficulty="Intermediate",
                topic="Data Structures",
                why_the_question_is_relevant="Essential for backend runtime performance."
            ),
            AssessmentMCQItem(
                id=2,
                question="How does FastAPI handle concurrent asynchronous request endpoints?",
                options=["Asyncio event loop execution", "Spawning heavy OS processes", "Blocking threads per request", "Polling web sockets"],
                correct_answer="Asyncio event loop execution",
                explanation="FastAPI runs async endpoints on the asyncio event loop.",
                skill="FastAPI",
                difficulty="Intermediate",
                topic="Concurrency",
                why_the_question_is_relevant="Core requirement for high-throughput microservices."
            ),
            AssessmentMCQItem(
                id=3,
                question="Which SQL keyword eliminates duplicate rows from an executed query result set?",
                options=["DISTINCT clause", "UNIQUE constraint", "GROUP FILTER", "REMOVE DUPLICATES"],
                correct_answer="DISTINCT clause",
                explanation="DISTINCT eliminates duplicate rows from SELECT results.",
                skill="SQL",
                difficulty="Intermediate",
                topic="Database Queries",
                why_the_question_is_relevant="Vital for clean database querying and reporting."
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
    # Fast submission returns with pending AI status without blocking
    assert sub_data["analysis_status"] == "pending"
    assert "details" in sub_data
    assert len(sub_data["details"]) > 0
    first_detail = sub_data["details"][0]
    assert "why_the_question_is_relevant" in first_detail

    # 3. Test Result Fetch (Background task executed by test client, persists across refresh)
    result_res = client.get(f"/api/v1/assessments/{assessment_id}/result", headers=auth_headers)
    assert result_res.status_code == 200
    res_data = result_res.json()
    assert res_data["attempt_id"] == sub_data["attempt_id"]
    assert res_data["analysis_status"] == "completed"
    assert len(res_data["improvement_plan"]) > 0

    # 4. Test Attempt-Specific Endpoint (Requirement 6)
    attempt_id = sub_data["attempt_id"]
    attempt_res = client.get(f"/api/v1/assessments/{assessment_id}/attempts/{attempt_id}/result", headers=auth_headers)
    assert attempt_res.status_code == 200
    att_data = attempt_res.json()
    assert att_data["attempt_id"] == attempt_id
    assert att_data["attempt_number"] == 1
    assert att_data["analysis_status"] == "completed"

    # 5. Test Assessment History Endpoint (Requirement 7)
    hist_res = client.get("/api/v1/assessments/history", headers=auth_headers)
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert len(hist_data) >= 1
    assert hist_data[0]["assessment_id"] == assessment_id
    assert hist_data[0]["attempt_id"] == attempt_id
    assert hist_data[0]["attempt_number"] == 1
    assert hist_data[0]["analysis_status"] == "completed"

