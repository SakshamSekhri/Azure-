# 🚀 Placement Preparation Agent

[![Python 3.12](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.37+-FF4B4B.svg)](https://streamlit.io/)
[![Azure AI Foundry](https://img.shields.io/badge/Azure_AI_Foundry-Integrated-0078D4.svg)](https://ai.azure.com/)
[![Tests](https://img.shields.io/badge/Pytest-92%20Passed%20(100%25)-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Issues](https://img.shields.io/github/issues/SakshamSekhri/Azure-)](https://github.com/SakshamSekhri/Azure-/issues)
[![GitHub Stars](https://img.shields.io/github/stars/SakshamSekhri/Azure-)](https://github.com/SakshamSekhri/Azure-/stargazers)

An enterprise-grade, credit-conscious placement preparation agent designed to evaluate student competencies against real-world Job Descriptions. It extracts multi-source evidence, performs canonical skill gap analysis, generates 100% dynamic role-tailored assessments via Azure AI Foundry, deterministically computes per-skill scores, provides deep AI diagnostics, and synthesizes grounded 7-day personalized improvement curriculums.

---

## ⚡ Core Architectural Principles

```text
Resume / CV
    ↓
Job Description / Target Role
    ↓
Central Normalized Placement Profile
    ↓
Canonical Skill Gap Analysis
    ↓
Dynamic MCQ Assessment (Azure AI Foundry)
    ↓
Deterministic Scoring (Pure Python)
    ↓
Per-Skill Performance & Weakness Detection
    ↓
7-Day Grounded Improvement Curriculum
    ↓
Targeted Reassessment & Progress Tracking
```

### Strict Quality & Operational Guarantees
1. **Zero Predefined Questions & Zero Fallbacks**: Every assessment question is generated dynamically at runtime by Azure AI Foundry (`PlacementPreparationAgent:4`). There are NO static question banks, mock catalogs, or hardcoded fallbacks. On failure, 1 corrective retry is attempted; if still failing, a controlled HTTP 502 error is returned.
2. **Quality Validation**: Questions must have exactly 4 unique options, 1 verified correct answer matching an option, non-empty technical content (placeholder options like `Option A` are rejected), and zero answer leakage into the question stem.
3. **Semantic Deduplication**: Questions are deduplicated using normalized SHA-256 stem hashing, fuzzy similarity matching (`difflib.SequenceMatcher > 0.80`), and intra-batch concept deduplication across the candidate's last 50 questions.
4. **Canonical Skill Normalization**: Skill aliases (e.g. `React.js` $\to$ `react`, `PostgreSQL` $\to$ `postgresql`, `Node.js` $\to$ `nodejs`) are mapped to canonical identifiers so candidate claims, JD requirements, and assessment performance unify seamlessly.
5. **Multi-Source Evidence Calibration**: Confidence is calibrated conservatively. A single high-scoring MCQ never inflates a skill to "Advanced" or "High" confidence without multi-question verification ($\ge 2$ samples) or corroborating code evidence.
6. **Deterministic Scoring**: Scoring remains 100% in application Python code, never delegated to AI.
7. **Strict Ownership Authorization**: All assessments, attempts, resumes, job descriptions, and learning plans enforce strict tenant/user ownership across every API route.
8. **AI Gateway Telemetry & Prompt Versioning**: Every AI invocation tracks prompt version, model deployment, token counts, cache hits/misses, and estimated USD expenditure.

---

## 🏗️ Technical Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, SQLite / PostgreSQL, Bcrypt, PyJWT.
- **Frontend**: Streamlit with custom CSS command center, real-time KPI breakdown, and interactive skill gap matrix.
- **AI Gateway**: Microsoft Azure AI Foundry Agent Service (`PlacementPreparationAgent` v4 on `gpt-5-mini`), SHA-256 context-and-version invalidating cache, token telemetry.
- **RAG & Learning**: Curated educational knowledge base with Azure AI Search grounding.
- **Security**: Strict production `SECRET_KEY` validation ($\ge 32$ chars), cross-platform Azure CLI discovery (`shutil.which("az")`), portable database path resolution.
- **Testing**: Pytest with in-memory SQLite fixtures (92 tests, 100% pass rate).

---

## 📦 Project Structure

```
.
├── backend/
│   └── app/
│       ├── main.py                          # FastAPI entry point, CORS, and route registration
│       ├── config/settings.py               # Production-hardened settings with secret validation
│       ├── core/database.py                 # SQLAlchemy 2.0 engine, Base, and session provider
│       ├── models/                          # 18 normalized SQLAlchemy models
│       │   ├── skill.py                     # Canonical skills & student skill records
│       │   ├── assessment.py                # Assessment header
│       │   ├── assessment_question.py       # Authoritative question source of truth
│       │   ├── assessment_attempt.py        # Multi-attempt tracking with duration & attempt_number
│       │   ├── assessment_answer.py         # Deterministic answer records
│       │   ├── ai_operation.py              # AI Gateway telemetry and cost records
│       │   └── ...
│       ├── schemas/                         # Pydantic v2 validation models
│       │   ├── placement_profile.py         # Central normalized PlacementProfile representation
│       │   ├── skill.py                     # Canonical skill schemas & matrix items
│       │   ├── assessment.py                # Assessment requests & deterministic results
│       │   ├── practice.py                  # Practice engine schemas
│       │   └── dashboard.py                 # Placement Readiness primary KPI & breakdown
│       ├── services/                        # Business logic
│       │   ├── skill_canonicalizer.py       # Catalog of canonical skills and deterministic slugifier
│       │   ├── skill_topic_service.py       # Hierarchical skill and topic management
│       │   ├── placement_profile_service.py # Unified profile aggregation & compact AI context
│       │   ├── assessment_service.py        # Dynamic question generation, validation, & scoring
│       │   ├── learning_service.py          # Grounded 7-day curriculum generator
│       │   └── ...
│       ├── ai/                              # AI Gateway, prompts, versions, and Foundry client
│       └── api/routes/                      # Secured FastAPI REST API endpoints
├── frontend/
│   ├── app.py                               # Multi-page Streamlit orchestrator with auth guard
│   ├── components/styles.py                 # Modern custom CSS styling & responsive cards
│   ├── components/ui.py                     # Shared UI components and renderers
│   ├── components/api_client.py             # Frontend REST client with token injection
│   └── views/                               # Streamlit views (Dashboard, Assessments, Practice, etc.)
├── migrations/                              # Alembic schema migrations
├── scripts/
│   ├── seed_data.py                         # Seeds canonical skills and student account
│   ├── apply_migration.py                   # Applies schema migrations and backfills canonical IDs
│   ├── clean_database.py                    # Database schema cleanup and migration utility
│   ├── run_backend.bat                      # Start FastAPI backend
│   └── run_frontend.bat                     # Start Streamlit frontend
├── tests/                                   # 92 comprehensive unit and integration tests
├── docs/                                    # System architecture and Azure setup documentation
│   ├── architecture.md                      # Detailed technical architecture guide
│   └── azure_setup.md                       # Azure AI Foundry & Azure AI Search configuration
├── .env.example                             # Environment configuration template
├── LICENSE                                  # MIT License
└── requirements.txt                         # Pinned dependencies
```

---

## 🚀 Getting Started

### 1. Environment Setup
```bash
git clone https://github.com/SakshamSekhri/Azure-.git
cd Azure-
python -m venv venv
venv\Scripts\activate  # On Windows (or source venv/bin/activate on Linux/macOS)
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```
Configure your Azure AI Foundry and project credentials:
```ini
AZURE_AI_FOUNDRY_ENDPOINT=https://<your-hub>.services.ai.azure.com/api/projects/<project-name>
AZURE_AI_AGENT_NAME=PlacementPreparationAgent
SECRET_KEY=<32-character-production-secret-key>
ENVIRONMENT=development
```

### 3. Initialize & Seed Database
```bash
python scripts/apply_migration.py
python scripts/seed_data.py
```
*Creates demo student account: `student@example.com` / `password123`*

### 4. Run the Application
**Terminal 1 (Backend):**
```bash
uvicorn backend.app.main:app --reload --port 8000
```
Interactive Swagger docs: `http://127.0.0.1:8000/docs`

**Terminal 2 (Frontend):**
```bash
streamlit run frontend/app.py
```
Frontend web application: `http://localhost:8501`

---

## 🧪 Automated Test Suite

Run all 92 automated tests across authorization, canonical skills, question validation, deterministic scoring, profile aggregation, and API routes:

```bash
python -m pytest -v
```

### Test Coverage Highlights
- `tests/test_authorization.py`: Verifies User A cannot view, submit, or access User B's assessments, attempts, resumes, jobs, or learning plans.
- `tests/test_canonical_skills.py`: Verifies alias normalization, JD vs candidate comparison, and multi-source confidence calibration.
- `tests/test_question_validation_and_grounding.py`: Verifies strict 4-option validation, single correct answer, answer leakage rejection, hash deduplication, and zero-fallback guarantees on failure.
- `tests/test_placement_profile.py`: Verifies central profile normalization, weak topic extraction, and compact token-efficient context.
- `tests/test_target_job_single_source_of_truth.py`: Verifies the active target job description is strictly the single source of truth for skill comparisons.
- `tests/test_practice_engine.py`: Verifies topic-targeted practice drill generation, evaluation, and feedback loops.
- `tests/test_per_skill_scoring.py`: Verifies deterministic per-skill scoring and multi-attempt tracking.
- `tests/test_ai_gateway_caching.py`: Verifies SHA-256 context-and-prompt caching and cost accounting.

---

## 📚 Technical Documentation

- [System Architecture Guide](docs/architecture.md): Deep-dive into deterministic/AI division, confidence matrices, and credit control policies.
- [Microsoft Foundry & Azure AI Search Setup](docs/azure_setup.md): Complete setup guide for `PlacementPreparationAgent` v4 and Azure AI Search index.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more details. Built for enterprise and academic placement readiness.
