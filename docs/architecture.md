# Placement Preparation Agent — Technical Architecture

This document describes the design principles, credit-control policies, database models, and service boundaries of the **Placement Preparation Agent**.

---

## 1. Architectural Philosophy: The Deterministic / AI Split

A common anti-pattern in AI tooling is routing deterministic logic (scoring, scheduling, comparison, state transitions) through expensive, nondeterministic Large Language Models.

The Placement Preparation Agent adheres to a strict division of responsibility:

```
+-------------------------------------------------------------------------+
|                         APPLICATION LAYER (PYTHON)                      |
|                                                                         |
|  - User Authentication & Session Security (JWT, bcrypt)                 |
|  - Relational Data Management (SQLite / PostgreSQL with SQLAlchemy)     |
|  - Objective MCQ Assessment Evaluation & Score Calculation              |
|  - Bounded Public GitHub REST API Extraction & Rate Limiting            |
|  - Deterministic Skill Gap Matrix Calculation                           |
|  - Next Action Recommendation Logic (Rule-based decision tree)          |
|  - 7-Day Curriculum Scheduling & Activity Checklist Progress            |
|  - File Text Extraction (PDF, DOCX, TXT) & SHA-256 Deduplication        |
+-------------------------------------------------------------------------+
                                    |
                                    | Only when semantic reasoning required
                                    v
+-------------------------------------------------------------------------+
|                        CENTRALIZED AI GATEWAY                           |
|                                                                         |
|  - SHA-256 Prompt Hashing & In-Memory/Database Cache Lookup             |
|  - Structured Pydantic Output Validation & Error Recovery               |
|  - Telemetry, Latency, and Token Consumption Auditing                   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------+-------------------------------------+
|   MICROSOFT AZURE AI FOUNDRY      |         AZURE AI SEARCH             |
|     (Persistent Agent Service)    |   (Knowledge Retrieval Layer)       |
|                                   |                                     |
|  1. Resume Semantic Parsing       |  - Bounded Context Search           |
|  2. JD Competency Mapping         |  - Educational Knowledge Base       |
|  3. Dynamic Assessment Generation |  - Strict Grounding / No-Hallucinate|
|  4. AI Diagnostic Result Analysis |                                     |
|  5. 7-Day Improvement Plan        |                                     |
|  6. Grounded RAG Educational Q&A  |                                     |
+-----------------------------------+-------------------------------------+
```

---

## 2. Credit Control & AI Gateway Mechanics

Every AI call in the platform must satisfy:
1. **Explicit Trigger**: AI is never called on page loads, routing transitions, or state updates. An explicit user button click (e.g. "Analyze Resume", "Generate Assessment", "Submit Assessment") is required.
2. **SHA-256 Prompt Hash**:
   $$\text{hash} = \text{SHA-256}(\text{operation\_type} + \text{payload})$$
3. **Zero Token Caching**: If the prompt hash exists in the `ai_operations` table with a successful response, the system serves the cached response immediately with `0` tokens consumed.
4. **No Chat Loops**: Live conversational back-and-forth loops are explicitly avoided. Instead, bounded batches (e.g., 5-question assessment batches) are sent in one single prompt pass.

---

## 3. Deterministic Skill Gap Engine

The platform determines student readiness mathematically:

$$\text{Readiness Score} = 0.6 \times \text{Skill Confidence} + 0.2 \times \text{Plan Completion} + 0.2 \times \text{Evidence Depth}$$

### Confidence Matrix Rules
- **High Confidence**: Assessment Score $\ge 75\%$, or $\ge 65\%$ with verified GitHub code & resume claim.
- **Medium Confidence**: Assessment Score between $50\%$ and $74\%$, or claimed with verified public GitHub code.
- **Low Confidence**: Assessment Score $< 50\%$, or claimed without proof.
- **Critical Gap**: Required by target job description but lacking proof or below assessment passing threshold.

---

## 4. Bounded GitHub Evidence Policy
- Supported: Public repositories only.
- Bounds: Up to 10 top repositories, maximum 2,000 characters of README snippet.
- Policy: GitHub code evidence is **supporting evidence only** and is explicitly never treated as proof of algorithmic mastery.
