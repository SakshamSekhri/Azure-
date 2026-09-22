# 🚀 Placement Preparation Agent

[![Python 3.12](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.37+-FF4B4B.svg)](https://streamlit.io/)
[![Azure AI Foundry](https://img.shields.io/badge/Azure_AI_Foundry-Integrated-0078D4.svg)](https://ai.azure.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Issues](https://img.shields.io/github/issues/SakshamSekhri/Azure-)](https://github.com/SakshamSekhri/Azure-/issues)
[![GitHub Stars](https://img.shields.io/github/stars/SakshamSekhri/Azure-)](https://github.com/SakshamSekhri/Azure-/stargazers)

An AI-powered placement preparation platform that analyzes student resumes and target job descriptions, identifies required skills, calculates deterministic candidate-vs-JD skill gaps, dynamically generates personalized assessments, deterministically computes scores, performs AI-driven diagnostic result analysis (strengths, weaknesses, critical gaps), and synthesizes actionable personalized improvement plans.

---

## ⚡ Core Architectural Requirement: Credit Control & PlacementPreparationAgent Flow

> **"Be extremely credit-conscious. AI must only be called when AI reasoning/generation is actually required. Everything deterministic must be handled by normal application code. Do NOT build a generic chatbot or static MCQ system."**

```text
Resume/CV + Target Job Description + Target Role
                      ↓
           PlacementPreparationAgent
                      ↓
   Dynamic Role-Tailored Assessment (MCQs)
                      ↓
               Candidate Answers
                      ↓
    Objective Scoring (Deterministic, 0 AI tokens)
                      ↓
          AI-Powered Result Analysis
                      ↓
       Strengths & Weaknesses Identification
                      ↓
              Critical Skill Gaps
                      ↓
         Personalized Improvement Plan
                      ↓
          Reassessment & Progress Tracking
```

### Division of Responsibility
| Deterministic Application Logic (Pure Python) | Azure AI Foundry Agent Service |
| :--- | :--- |
| User Authentication & JWT Security | Resume Semantic Skill Extraction |
| Database CRUD & SQLAlchemy ORM | Job Description Competency Extraction |
| Objective MCQ Scoring (0-100%) | Dynamic Personalized Assessment Generation |
| Candidate-vs-JD Gap Calibration | AI-Powered Result & Gap Analysis |
| File SHA-256 Deduplication & Storage | Personalized Improvement Plan Synthesis |
| SHA-256 Prompt Caching Layer | Grounded RAG Educational Q&A (Azure Search) |
| Next Best Action Decision Engine | Adaptive Difficulty Progression |

---

## 🏗️ Technical Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, SQLite (PostgreSQL ready), Bcrypt, PyJWT.
- **Frontend**: Streamlit with custom CSS (modern cards, status badges, progress bars, non-default UI).
- **AI Engine**: Microsoft Azure AI Foundry Agent Service (`PlacementPreparationAgent` v4) for 100% dynamic question generation and diagnostic result analysis (Zero predefined questions).
- **RAG Layer**: Azure AI Search client with curated educational knowledge base.
- **VCS Integration**: GitHub REST API (bounded public repositories, READMEs, languages, commit signals).
- **Testing**: Pytest with in-memory SQLite fixtures (100% pass rate).

---

## 📦 Project Structure

```
.
├── .github/                         # GitHub issue templates and repository workflows
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI entry point and CORS setup
│       ├── config/settings.py       # Pydantic environment configuration
│       ├── core/                    # Database, direct Bcrypt security, logging
│       ├── models/                  # SQLAlchemy 2.0 normalized models (18 tables)
│       ├── schemas/                 # Pydantic request/response & AI validation schemas
│       ├── services/                # Business logic (Resume, JD, Skill Gap, GitHub, etc.)
│       ├── ai/                      # Centralized AI Gateway, SHA-256 cache, Foundry client
│       ├── rag/                     # Azure AI Search and educational knowledge base
│       ├── api/routes/              # FastAPI route endpoints
│       └── utils/text_extractor.py  # PDF, DOCX, TXT parser with SHA-256 hashing
├── frontend/
│   ├── app.py                       # Streamlit multi-page orchestrator & auth guard
│   ├── components/styles.py         # Modern custom styling & theme
│   ├── components/api_client.py     # Frontend HTTP client
│   └── views/                       # Streamlit view modules
├── tests/                           # Comprehensive Pytest suite (41 tests, 100% pass)
├── scripts/
│   ├── seed_data.py                 # Seeds skills taxonomy and demo student user
│   ├── clean_database.py            # Database schema migration & cleanup utility
│   ├── run_backend.bat              # Start FastAPI server
│   ├── run_frontend.bat             # Start Streamlit frontend
│   └── run_all.bat                  # Start full stack
├── docs/                            # Architecture & Azure setup guides
│   ├── architecture.md              # Detailed system architecture & design philosophy
│   └── azure_setup.md               # Microsoft Foundry & Azure AI Search setup guide
├── .env.example                     # Environment template
├── LICENSE                          # MIT License
└── requirements.txt                 # Project dependencies
```

---

## 🚀 Getting Started

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/SakshamSekhri/Azure-.git
cd Azure-
python -m venv venv
venv\Scripts\activate  # On Windows (or source venv/bin/activate on Unix)
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
# On Windows
copy .env.example .env

# On Unix / macOS
cp .env.example .env
```

*(Dynamic question generation strictly requires Azure AI Foundry credentials configured via `az login` or Azure credentials in `.env` - zero fallback or mock questions exist).*

### 3. Seed Database
Pre-populate skills taxonomy and demo student user:
```bash
python scripts/seed_data.py
```
*Creates demo student account: `student@example.com` / `password123`*

### 4. Start the Application

#### Option A: Quick Launch (Windows)
```cmd
scripts\run_all.bat
```

#### Option B: Dedicated Terminals

**Terminal 1 (FastAPI Backend):**
```bash
uvicorn backend.app.main:app --reload --port 8000
```
Interactive API documentation: `http://127.0.0.1:8000/docs`

**Terminal 2 (Streamlit Frontend):**
```bash
streamlit run frontend/app.py
```
Application interface: `http://localhost:8501`

---

## 🧪 Running Automated Tests

Run the full automated test suite verifying auth, resume parsing, JD analysis, deterministic scoring, skill engine, GitHub integration, AI gateway caching, and API routes:

```bash
python -m pytest -v tests/
```

### AI Caching Verification
The test `tests/test_ai_gateway_caching.py` specifically asserts that:
1. The first call to an AI operation consumes tokens and logs status `SUCCESS`.
2. A subsequent call with the identical prompt hash returns the cached response with **0 new tokens** consumed and status `CACHED`.

---

## 📊 End-to-End Student Workflow

1. **Sign In**: Register a new student account or click "Quick Demo Access".
2. **Profile**: Select target role (e.g. `Full Stack Backend Engineer`) and input public GitHub handle.
3. **Resume Processing**: Upload resume (PDF, DOCX, TXT). Click **"Analyze Resume"** to extract verified skills and project evidence.
4. **Target Job Description**: Paste a target JD and click **"Analyze Job Description"** to extract required competencies and assessment areas.
5. **Skill Gap Engine & Comparison**: Compare candidate evidence against the JD with exact categories (Evidence Found, Needs Assessment, Skill Gap, Unknown).
6. **Personalized Assessment**: Click **"Generate Personalized Assessment"** to dynamically generate role-tailored MCQs based on your profile, JD requirements, and past performance.
7. **Objective Scoring & AI Diagnostic Result Analysis**: Backend deterministically computes scores, followed by AI diagnostic analysis identifying strengths, weaknesses, critical gaps, and prioritized study areas.
8. **Personalized Improvement Plan**: Follow customized, actionable steps and practical scenarios designed to eliminate identified skill gaps.
9. **Reassessment & Progress Tracking**: Retake targeted assessments to verify mastery and elevate your demonstrated proficiency.
10. **AI Cost & Telemetry Dashboard**: Audit total Azure requests, cache hit rate %, token consumption, and estimated expenditure.

---

## 📚 Technical Documentation

- [System Architecture Guide](docs/architecture.md): Deep-dive into deterministic/AI division, confidence matrices, and credit control policies.
- [Microsoft Foundry & Azure AI Search Setup](docs/azure_setup.md): Complete setup guide for `PlacementPreparationAgent` v4 and Azure AI Search index.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more details. Built for enterprise and academic placement readiness.
