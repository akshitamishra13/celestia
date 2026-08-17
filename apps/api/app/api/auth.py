from fastapi import APIRouter, Response, status

from app.api.dependencies import CurrentUser, DatabaseDependency
from app.core.config import get_settings
from app.core.security import create_session_token
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthData, LoginRequest, LogoutResponse, SignupRequest, SuccessResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


def set_session_cookie(response: Response, user_id: object) -> None:
    settings = get_settings()
    response.set_cookie(
        key="astrolive_session",
        value=create_session_token(user_id),
        max_age=settings.session_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/signup", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, response: Response, database: DatabaseDependency) -> SuccessResponse:
    user = AuthService(UserRepository(database)).signup(payload)
    set_session_cookie(response, user.id)
    return SuccessResponse(data=AuthData(user=user))


@router.post("/login", response_model=SuccessResponse)
def login(payload: LoginRequest, response: Response, database: DatabaseDependency) -> SuccessResponse:
    user = AuthService(UserRepository(database)).login(payload)
    set_session_cookie(response, user.id)
    return SuccessResponse(data=AuthData(user=user))


@router.post("/logout", response_model=LogoutResponse)
def logout(response: Response) -> LogoutResponse:
    response.delete_cookie("astrolive_session", path="/")
    return LogoutResponse()


@router.get("/me", response_model=SuccessResponse)
def me(user: CurrentUser) -> SuccessResponse:
    return SuccessResponse(data=AuthData(user=user))
