from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_session_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

DatabaseDependency = Annotated[Session, Depends(get_db)]


def get_current_user(
    database: DatabaseDependency,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    scheme, _, token = authorization.partition(" ") if authorization else ("", "", "")
    user_id = decode_session_token(token) if scheme.lower() == "bearer" and token else None
    user = UserRepository(database).get_by_id(user_id) if user_id else None
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
