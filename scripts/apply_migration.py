import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
import json
from backend.app.services.skill_canonicalizer import canonicalize_skill

db_path = Path(__file__).resolve().parent.parent / "placement_prep.db"
conn = sqlite3.connect(str(db_path))
c = conn.cursor()

# 1. Skills
existing_skills_cols = [col[1] for col in c.execute("PRAGMA table_info(skills)").fetchall()]
if "canonical_id" not in existing_skills_cols:
    c.execute("ALTER TABLE skills ADD COLUMN canonical_id VARCHAR(100)")
    print("[+] Added canonical_id to skills")
if "aliases" not in existing_skills_cols:
    c.execute("ALTER TABLE skills ADD COLUMN aliases JSON")
    print("[+] Added aliases to skills")

# Backfill canonical_id on existing skills
skills = c.execute("SELECT id, name, category FROM skills").fetchall()
for s_id, name, cat in skills:
    canon = canonicalize_skill(name, cat)
    c.execute("UPDATE skills SET canonical_id = ?, aliases = ? WHERE id = ?", (canon.canonical_id, json.dumps(canon.aliases), s_id))
print(f"[+] Backfilled {len(skills)} skills with canonical IDs")

# 2. Assessment Questions
existing_q_cols = [col[1] for col in c.execute("PRAGMA table_info(assessment_questions)").fetchall()]
if "canonical_skill_id" not in existing_q_cols:
    c.execute("ALTER TABLE assessment_questions ADD COLUMN canonical_skill_id VARCHAR(100)")
    print("[+] Added canonical_skill_id to assessment_questions")
if "question_hash" not in existing_q_cols:
    c.execute("ALTER TABLE assessment_questions ADD COLUMN question_hash VARCHAR(64)")
    print("[+] Added question_hash to assessment_questions")

# 3. Assessment Attempts
existing_att_cols = [col[1] for col in c.execute("PRAGMA table_info(assessment_attempts)").fetchall()]
if "attempt_number" not in existing_att_cols:
    c.execute("ALTER TABLE assessment_attempts ADD COLUMN attempt_number INTEGER NOT NULL DEFAULT 1")
    print("[+] Added attempt_number to assessment_attempts")
if "duration_seconds" not in existing_att_cols:
    c.execute("ALTER TABLE assessment_attempts ADD COLUMN duration_seconds INTEGER")
    print("[+] Added duration_seconds to assessment_attempts")

# 4. AI Operations
existing_ai_cols = [col[1] for col in c.execute("PRAGMA table_info(ai_operations)").fetchall()]
if "model" not in existing_ai_cols:
    c.execute("ALTER TABLE ai_operations ADD COLUMN model VARCHAR(100) DEFAULT 'gpt-5-mini'")
    print("[+] Added model to ai_operations")
if "prompt_version" not in existing_ai_cols:
    c.execute("ALTER TABLE ai_operations ADD COLUMN prompt_version VARCHAR(50) DEFAULT 'v1.0'")
    print("[+] Added prompt_version to ai_operations")
if "input_tokens" not in existing_ai_cols:
    c.execute("ALTER TABLE ai_operations ADD COLUMN input_tokens INTEGER NOT NULL DEFAULT 0")
    print("[+] Added input_tokens to ai_operations")
if "output_tokens" not in existing_ai_cols:
    c.execute("ALTER TABLE ai_operations ADD COLUMN output_tokens INTEGER NOT NULL DEFAULT 0")
    print("[+] Added output_tokens to ai_operations")
if "cache_hit" not in existing_ai_cols:
    c.execute("ALTER TABLE ai_operations ADD COLUMN cache_hit BOOLEAN NOT NULL DEFAULT 0")
    print("[+] Added cache_hit to ai_operations")
if "estimated_cost" not in existing_ai_cols:
    c.execute("ALTER TABLE ai_operations ADD COLUMN estimated_cost FLOAT NOT NULL DEFAULT 0.0")
    print("[+] Added estimated_cost to ai_operations")

conn.commit()
conn.close()
print("[*] Database migration applied successfully!")
