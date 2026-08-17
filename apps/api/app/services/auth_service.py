from fastapi import HTTPException, status

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, SignupRequest


class AuthService:
    def __init__(self, users: UserRepository):
        self.users = users

    def signup(self, payload: SignupRequest) -> User:
        if self.users.get_by_email(str(payload.email)):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")
        return self.users.create(name=payload.name, email=str(payload.email), password_hash=hash_password(payload.password))

    def login(self, payload: LoginRequest) -> User:
        user = self.users.get_by_email(str(payload.email))
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="The email or password is incorrect.")
        return user
