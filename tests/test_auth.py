from backend.app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from backend.app.services.auth_service import AuthService
from backend.app.schemas.user import UserCreate


def test_password_hashing():
    pw = "SuperSecretPassword123"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_flow():
    user_id = 42
    token = create_access_token(subject=user_id)
    assert isinstance(token, str)
    decoded_id = decode_access_token(token)
    assert decoded_id == str(user_id)


def test_auth_service_registration_and_login(db_session):
    user_in = UserCreate(email="new_engineer@college.edu", password="securepassword")
    user = AuthService.register_user(db_session, user_in)
    assert user.id is not None
    assert user.email == "new_engineer@college.edu"

    # Verify profile created
    assert user.profile is not None
    assert user.profile.name == "New_engineer"

    # Authenticate
    auth_user = AuthService.authenticate_user(db_session, "new_engineer@college.edu", "securepassword")
    assert auth_user is not None
    assert auth_user.id == user.id

    # Invalid password
    bad_auth = AuthService.authenticate_user(db_session, "new_engineer@college.edu", "wrongpass")
    assert bad_auth is None
