"""Data seeder for Placement Preparation Agent.
Populates standard skills taxonomy and a demo student.
Assessments are generated dynamically by PlacementPreparationAgent without static question banks.
"""
import sys
import os

# Append project root
sys.path.insert(0, os.path.abspath("."))

from backend.app.core.database import SessionLocal, engine, Base
from backend.app.core.security import hash_password
from backend.app.models.user import User
from backend.app.models.profile import StudentProfile
from backend.app.models.skill import Skill
from backend.app.models.evidence import Evidence



def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("--- Seeding Placement Preparation Agent Data ---")

    # 1. Standard Skills Taxonomy
    skills_data = [
        ("Python", "Programming", "Core Python language features, data structures, and standard library."),
        ("SQL", "Database", "Relational database querying, schema design, and indexing."),
        ("FastAPI", "Framework", "Modern high-performance Python asynchronous web framework."),
        ("System Design", "CS Fundamentals", "Large-scale distributed systems architecture, caching, and scalability."),
        ("Git", "Tools", "Distributed version control system and collaborative workflows."),
        ("Docker", "DevOps", "Containerization technology for packaging and shipping applications."),
        ("PostgreSQL", "Database", "Advanced open-source object-relational database."),
        ("Redis", "Database", "In-memory data structure store used as a database, cache, and message broker."),
        ("REST APIs", "CS Fundamentals", "Architectural style for designing networked applications."),
        ("React", "Framework", "Component-based front-end library for interactive user interfaces."),
        ("Data Structures", "CS Fundamentals", "Foundational algorithms, trees, graphs, and algorithmic complexity."),
        ("AWS", "Cloud", "Amazon Web Services cloud computing platform.")
    ]

    skill_objs = {}
    for name, cat, desc in skills_data:
        skill = db.query(Skill).filter(Skill.name == name).first()
        if not skill:
            skill = Skill(name=name, category=cat, description=desc)
            db.add(skill)
            db.commit()
            db.refresh(skill)
        skill_objs[name] = skill

    print(f"[+] Verified {len(skill_objs)} standard skills.")
    print("[+] Dynamic assessments enabled: zero static question banks seeded.")

    # 3. Demo Student User for Immediate Evaluation
    demo_email = "student@example.com"
    demo_user = db.query(User).filter(User.email == demo_email).first()
    if not demo_user:
        demo_user = User(
            email=demo_email,
            password_hash=hash_password("password123"),
            is_active=True
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)

        # Profile
        demo_profile = StudentProfile(
            user_id=demo_user.id,
            name="Alex Chen",
            college="State Engineering University",
            degree="B.Tech Computer Science",
            graduation_year=2026,
            target_role="Full Stack Backend Engineer",
            experience_level="Entry Level",
            github_username="alexchen-dev"
        )
        db.add(demo_profile)
        db.commit()
        print(f"[+] Created demo user: {demo_email} (password: password123)")
    else:
        print(f"[+] Demo user already exists: {demo_email}")

    db.close()
    print("--- Database Seeding Complete! ---")


if __name__ == "__main__":
    seed_database()
