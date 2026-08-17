from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, database: Session):
        self.database = database

    def get_by_email(self, email: str) -> User | None:
        return self.database.scalar(select(User).where(User.email == email.lower()))

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.database.get(User, user_id)

    def create(self, *, name: str, email: str, password_hash: str) -> User:
        user = User(name=name, email=email.lower(), password_hash=password_hash)
        self.database.add(user)
        self.database.commit()
        self.database.refresh(user)
        return user
