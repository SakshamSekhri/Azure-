from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.user import User
from backend.app.models.profile import StudentProfile
from backend.app.schemas.user import UserCreate
from backend.app.core.security import hash_password, verify_password, create_access_token


class AuthService:
    @staticmethod
    def register_user(db: Session, user_in: UserCreate) -> User:
        existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )

        hashed_pw = hash_password(user_in.password)
        db_user = User(
            email=user_in.email.lower(),
            password_hash=hashed_pw,
            is_active=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Create default initial profile
        default_profile = StudentProfile(
            user_id=db_user.id,
            name=user_in.email.split("@")[0].capitalize(),
            target_role="Full Stack Developer",
            experience_level="Entry Level"
        )
        db.add(default_profile)
        db.commit()

        return db_user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
