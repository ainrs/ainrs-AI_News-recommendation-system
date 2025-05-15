from fastapi import APIRouter, HTTPException, Depends, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.core.config import settings
from app.models.user import UserCreate, UserProfile, UserInDB, UserVerify
from app.db.mongodb import user_collection, verification_codes_collection
from app.services.email_service import email_service, send_verification_code

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
    responses={401: {"description": "Unauthorized"}}
)

# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# 시크릿 키 설정
SECRET_KEY = settings.EMAIL_VERIFICATION_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30일

def get_password_hash(password: str) -> str:
    """비밀번호를 해싱합니다."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호를 검증합니다."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT 액세스 토큰을 생성합니다."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """사용자 인증을 수행합니다."""
    user = await user_collection.find_one({"username": username})
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return UserInDB(**user)

@router.post("/register", response_model=Dict[str, Any])
async def register_user(user_data: UserCreate = Body(...)):
    """새 사용자를 등록합니다."""
    # 중복 검사
    existing_user = await user_collection.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="사용자 이름이 이미 사용 중입니다"
        )

    if user_data.email:
        existing_email = await user_collection.find_one({"email": user_data.email})
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이메일이 이미 사용 중입니다"
            )

    # 사용자 데이터 생성
    user_id = f"user_{datetime.utcnow().timestamp()}"
    password_hash = get_password_hash(user_data.password)

    new_user = {
        "_id": user_id,
        "username": user_data.username,
        "email": user_data.email,
        "password_hash": password_hash,
        "is_active": True,
        "verified": False,  # 이메일 인증이 필요함
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    # 사용자 저장
    await user_collection.insert_one(new_user)

    # 이메일 인증 필요
    if user_data.email:
        await send_verification_code(user_data.email)

        return {
            "status": "success",
            "message": "사용자가 등록되었습니다. 이메일 인증이 필요합니다.",
            "user_id": user_id,
            "verification_required": True
        }

    return {
        "status": "success",
        "message": "사용자가 등록되었습니다",
        "user_id": user_id
    }

@router.post("/verify-email")
async def verify_email(verification: UserVerify = Body(...)):
    """이메일 인증 코드를 검증합니다."""
    # 인증 코드 검증
    is_valid = await email_service.verify_code(verification.email, verification.code)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 인증 코드입니다"
        )

    # 사용자 찾기 및 인증 상태 업데이트
    user = await user_collection.find_one({"email": verification.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )

    # 사용자 인증 상태 업데이트
    await user_collection.update_one(
        {"email": verification.email},
        {"$set": {"verified": True, "updated_at": datetime.utcnow()}}
    )

    return {
        "status": "success",
        "message": "이메일 인증에 성공했습니다",
        "verified": True
    }

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """사용자 로그인 처리."""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 사용자 이름 또는 비밀번호",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 이메일 인증 확인 (해당하는 경우)
    if user.email and not user.verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 사용자 로그인 시간 업데이트
    await user_collection.update_one(
        {"username": form_data.username},
        {"$set": {"last_login": datetime.utcnow()}}
    )

    # JWT 토큰 생성
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username
    }
