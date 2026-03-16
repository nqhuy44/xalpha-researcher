import datetime
from typing import Optional
from jose import jwt, JWTError
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.config.settings import settings
import structlog

logger = structlog.get_logger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=settings.api.jwt_expire_hours)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.api.jwt_secret, algorithm="HS256")
    return encoded_jwt

async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Security(security),
    token: Optional[str] = None
):
    """
    FastAPI dependency to validate JWT token.
    Supports both Authorization header (Bearer) and 'token' query parameter.
    """
    jwt_token = None
    if auth:
        jwt_token = auth.credentials
    elif token:
        jwt_token = token
        
    if not jwt_token:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    try:
        payload = jwt.decode(jwt_token, settings.api.jwt_secret, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

def authenticate_admin(password: str) -> bool:
    """
    Checks if provided password matches the ADMIN_PASSWORD in settings.
    """
    if not settings.api.admin_password:
        logger.warning("auth_admin_password_not_set")
        return False
    return password == settings.api.admin_password
