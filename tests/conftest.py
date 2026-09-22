import sys
import os
from pathlib import Path

# Add project root to sys.path
root_dir = str(Path(__file__).parent.parent.resolve())
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.core.security import hash_password, create_access_token
from backend.app.models.user import User
from backend.app.models.profile import StudentProfile
from backend.app.models.skill import Skill
from backend.app.models.assessment import Assessment

# Use in-memory SQLite for fast, isolated test runs
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_user(db_session):
    user = User(
        email="tester@example.com",
        password_hash=hash_password("testpassword123"),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    profile = StudentProfile(
        user_id=user.id,
        name="Tester Student",
        target_role="Full Stack Developer",
        experience_level="Entry Level"
    )
    db_session.add(profile)

    # Add standard skills
    py_skill = Skill(name="Python", category="Programming")
    sql_skill = Skill(name="SQL", category="Database")
    db_session.add_all([py_skill, sql_skill])
    db_session.commit()

    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(subject=test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
