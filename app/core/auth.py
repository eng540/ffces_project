# ============================================================
# Authentication API Routes
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from uuid import UUID

from app.core.database import get_db
from app.core.config import settings
from app.models import User
from app.schemas import UserCreate, UserResponse, UserLogin, TokenResponse

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None: raise credentials_exception
    except JWTError: raise credentials_exception

    query = select(User).where(User.id == UUID(user_id))
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if user is None: raise credentials_exception
    return user

def require_role(allowed_roles: list):
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.email == data.email)
    result = await db.execute(query)
    if result.scalar_one_or_none(): raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=data.email, password_hash=get_password_hash(data.password), role=data.role, full_name=data.full_name, phone=data.phone, organization_id=data.organization_id)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.email == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token({"sub": str(user.id), "role": user.role, "org": str(user.organization_id)})
    refresh_token = create_access_token({"sub": str(user.id), "type": "refresh"}, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

    user.last_login_at = datetime.utcnow()
    await db.flush()

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
