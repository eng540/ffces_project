# ============================================
# FFCES - المصادقة والتفويض (Authentication & Authorization)
# ============================================
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db

# ===== Password Hashing =====
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ===== OAuth2 =====
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ===== JWT Token Creation =====
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ===== Password Utilities =====
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ===== Dependency: Get Current User =====
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """استخراج المستخدم الحالي من رمز الوصول"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="لا يمكن التحقق من بيانات المصادقة",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    from app.models import User
    query = select(User).where(User.id == uuid.UUID(user_id))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=403, detail="الحساب معطل")

    return user


# ===== Dependency: Require Specific Role =====
def require_role(allowed_roles: List[str]):
    """التأكد من أن المستخدم لديه دور محدد"""
    async def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"الوصول مرفوض. الأدوار المسموحة: {', '.join(allowed_roles)}",
            )
        return current_user
    return role_checker


# ===== Router =====
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["المصادقة"])


# ===== Helper to get User model lazily (avoid circular imports) =====
def _get_user_model():
    from app.models import User
    return User


# ===== Endpoints =====
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    email: str,
    full_name: str,
    password: str,
    role: str = "employee",
    db: AsyncSession = Depends(get_db),
):
    """تسجيل مستخدم جديد - Register a new user"""
    User = _get_user_model()
    from sqlalchemy import select as sa_select

    # Check if user already exists
    query = sa_select(User).where(User.email == email)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="البريد الإلكتروني مسجل مسبقاً")

    # Create user
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        role=role,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()

    # Generate tokens
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """تسجيل الدخول - User login"""
    User = _get_user_model()
    from sqlalchemy import select as sa_select

    query = sa_select(User).where(User.email == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="بيانات الدخول غير صحيحة",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="الحساب معطل")

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.flush()

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    }


@router.post("/refresh")
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """تجديد رمز الوصول - Refresh access token"""
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="رمز غير صالح")
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="رمز غير صالح")
    except JWTError:
        raise HTTPException(status_code=401, detail="رمز غير صالح")

    User = _get_user_model()
    from sqlalchemy import select as sa_select

    query = sa_select(User).where(User.id == uuid.UUID(user_id))
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="المستخدم غير موجود أو معطل")

    new_access_token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    """بيانات المستخدم الحالي - Current user profile"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "employee_number": current_user.employee_number,
        "phone": current_user.phone,
        "organization_id": str(current_user.organization_id) if current_user.organization_id else None,
    }