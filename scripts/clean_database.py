"""Database Cleaner & Migrator for Dynamic Placement Preparation Platform.
Drops obsolete coding & interview tables.
Removes legacy static assessments.
Adds new assessment_questions and assessment_answers tables and schema updates.
"""
import sys
import os
import sqlite3
import json

sys.path.insert(0, os.path.abspath("."))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "placement_prep.db"))


def clean_and_migrate():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Drop obsolete coding and interview tables
    obsolete_tables = [
        "coding_problems",
        "coding_submissions",
        "interviews",
        "interview_questions",
        "interview_answers"
    ]
    for table in obsolete_tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"[+] Dropped obsolete table: {table}")

    # 2. Clean legacy static assessment questions (where role IS NULL)
    cursor.execute("DELETE FROM assessments WHERE role IS NULL")
    deleted_static = cursor.rowcount
    print(f"[+] Deleted {deleted_static} legacy static assessment records.")

    # 3. Verify / Update columns in 'assessments' table
    cursor.execute("PRAGMA table_info(assessments)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    print(f"Existing assessments columns: {existing_cols}")

    if "candidate_id" not in existing_cols:
        cursor.execute("ALTER TABLE assessments ADD COLUMN candidate_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
        print("[+] Added candidate_id column to assessments")

    if "job_id" not in existing_cols:
        cursor.execute("ALTER TABLE assessments ADD COLUMN job_id INTEGER REFERENCES job_descriptions(id) ON DELETE SET NULL")
        print("[+] Added job_id column to assessments")

    if "question_count" not in existing_cols:
        cursor.execute("ALTER TABLE assessments ADD COLUMN question_count INTEGER NOT NULL DEFAULT 5")
        print("[+] Added question_count column to assessments")

    if "status" not in existing_cols:
        cursor.execute("ALTER TABLE assessments ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'completed'")
        print("[+] Added status column to assessments")

    # 4. Create assessment_questions table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessment_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assessment_id INTEGER NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
        question TEXT NOT NULL,
        options JSON NOT NULL,
        correct_answer TEXT NOT NULL,
        explanation TEXT NOT NULL,
        skill VARCHAR(100),
        topic VARCHAR(100),
        difficulty VARCHAR(50) NOT NULL DEFAULT 'Intermediate',
        why_the_question_is_relevant TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_assessment_questions_id ON assessment_questions(id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_assessment_questions_assessment_id ON assessment_questions(assessment_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_assessment_questions_skill ON assessment_questions(skill)")
    print("[+] Verified assessment_questions table.")

    # 5. Create assessment_answers table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessment_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assessment_id INTEGER NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
        question_id INTEGER NOT NULL REFERENCES assessment_questions(id) ON DELETE CASCADE,
        candidate_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        selected_answer TEXT NOT NULL,
        correct_answer TEXT NOT NULL,
        is_correct BOOLEAN NOT NULL,
        time_taken INTEGER,
        answered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_assessment_answers_id ON assessment_answers(id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_assessment_answers_assessment_id ON assessment_answers(assessment_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_assessment_answers_candidate_id ON assessment_answers(candidate_id)")
    print("[+] Verified assessment_answers table.")

    # 6. Migrate existing questions from dynamic assessments into assessment_questions
    cursor.execute("SELECT id, questions_json, created_at FROM assessments")
    assessments_data = cursor.fetchall()
    migrated_count = 0
    for a_id, q_json, created_at in assessments_data:
        if not q_json:
            continue
        try:
            questions = json.loads(q_json)
        except Exception:
            continue

        for q in questions:
            q_text = q.get("question") or q.get("question_text", "")
            if not q_text:
                continue

            # Check if already inserted
            cursor.execute(
                "SELECT id FROM assessment_questions WHERE assessment_id = ? AND question = ?",
                (a_id, q_text)
            )
            if not cursor.fetchone():
                opts = json.dumps(q.get("options", []))
                cursor.execute(
                    """
                    INSERT INTO assessment_questions 
                    (assessment_id, question, options, correct_answer, explanation, skill, topic, difficulty, why_the_question_is_relevant, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        a_id,
                        q_text,
                        opts,
                        q.get("correct_answer", ""),
                        q.get("explanation", ""),
                        q.get("skill"),
                        q.get("topic"),
                        q.get("difficulty", "Intermediate"),
                        q.get("why_the_question_is_relevant"),
                        created_at or "2026-09-22 00:00:00"
                    )
                )
                migrated_count += 1

    print(f"[+] Migrated {migrated_count} individual questions into assessment_questions table.")

    # 7. Update candidate_id in assessments based on attempts
    cursor.execute("""
        UPDATE assessments
        SET candidate_id = (
            SELECT user_id FROM assessment_attempts 
            WHERE assessment_attempts.assessment_id = assessments.id 
            LIMIT 1
        )
        WHERE candidate_id IS NULL
    """)
    conn.commit()

    # Verify final tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    final_tables = [r[0] for r in cursor.fetchall()]
    print(f"\nFinal tables in DB: {final_tables}")
    conn.close()
    print("--- Database cleanup & migration complete! ---")


if __name__ == "__main__":
    clean_and_migrate()
