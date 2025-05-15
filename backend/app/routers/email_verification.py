from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import EmailStr
from typing import Dict, Any

from app.models.user import UserVerify
from app.services.email_service import email_service, send_verification_code
from app.db.mongodb import verification_codes_collection, user_collection

router = APIRouter(
    prefix="/api/email",
    tags=["email"],
    responses={404: {"description": "Not found"}},
)

@router.post("/send-verification-code")
async def request_verification_code(email: EmailStr) -> Dict[str, Any]:
    """
    이메일 인증 코드를 요청합니다.
    """
    try:
        # 이미 가입된 이메일인지 확인
        existing_user = await user_collection.find_one({"email": email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 가입된 이메일입니다."
            )

        # 인증 코드 생성 및 전송
        await send_verification_code(email)

        return {
            "status": "success",
            "message": "인증 코드가 이메일로 전송되었습니다.",
            "expires_in_minutes": 4
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인증 코드 전송 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/verify-code")
async def verify_email_code(verification: UserVerify) -> Dict[str, Any]:
    """
    이메일 인증 코드를 검증합니다.
    """
    # 인증 코드 검증
    is_valid = await email_service.verify_code(verification.email, verification.code)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 인증 코드입니다."
        )

    return {
        "status": "success",
        "message": "이메일 인증에 성공했습니다.",
        "verified": True
    }
