from fastapi import APIRouter, status

from app.api.dependencies import CurrentUser, DatabaseDependency
from app.core.security import create_session_token
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthData, LoginRequest, LogoutResponse, SignupRequest, SuccessResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


def auth_data(user: object) -> AuthData:
    return AuthData(user=user, access_token=create_session_token(user.id), token_type="bearer")


@router.post("/signup", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, database: DatabaseDependency) -> SuccessResponse:
    user = AuthService(UserRepository(database)).signup(payload)
    return SuccessResponse(data=auth_data(user))


@router.post("/login", response_model=SuccessResponse)
def login(payload: LoginRequest, database: DatabaseDependency) -> SuccessResponse:
    user = AuthService(UserRepository(database)).login(payload)
    return SuccessResponse(data=auth_data(user))


@router.post("/logout", response_model=LogoutResponse)
def logout() -> LogoutResponse:
    # JWTs are stateless; the client logs out by discarding its token.
    return LogoutResponse()


@router.get("/me", response_model=SuccessResponse)
def me(user: CurrentUser) -> SuccessResponse:
    return SuccessResponse(data=AuthData(user=user))
