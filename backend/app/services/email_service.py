import os
import secrets
import string
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi import HTTPException, status

from app.core.config import settings
from app.db.mongodb import verification_codes_collection

# FastAPI-Mail ConnectionConfig 설정: 이메일 제공자에 따라 TLS/SSL 설정 변경
if settings.EMAIL_PROVIDER == "naver":
    conf = ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_STARTTLS=False,    # 네이버는 TLS 사용하지 않음
        MAIL_SSL_TLS=True,      # 네이버는 SSL 사용
        USE_CREDENTIALS=settings.USE_CREDENTIALS,
        VALIDATE_CERTS=True,
        TEMPLATE_FOLDER=None
    )
else:
    conf = ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_STARTTLS=True,     # Gmail은 TLS 사용
        MAIL_SSL_TLS=False,     # Gmail은 SSL 미사용
        USE_CREDENTIALS=settings.USE_CREDENTIALS,
        VALIDATE_CERTS=True,
        TEMPLATE_FOLDER=None
    )

class EmailService:
    @staticmethod
    def generate_verification_code(length: int = 6) -> str:
        """
        지정된 길이의 숫자 인증 코드를 생성합니다.
        """
        return ''.join(secrets.choice(string.digits) for _ in range(length))

    @staticmethod
    async def save_verification_code(email: str, code: str) -> None:
        """
        이메일 인증 코드를 데이터베이스에 저장합니다.
        """
        # 기존 코드가 있다면 삭제
        await verification_codes_collection.delete_many({"email": email})

        # 새 코드 저장 및 만료 시간 설정
        expiration_time = datetime.utcnow() + timedelta(minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES)

        await verification_codes_collection.insert_one({
            "email": email,
            "code": code,
            "expires_at": expiration_time
        })

    @staticmethod
    async def verify_code(email: str, code: str) -> bool:
        """
        사용자가 입력한 코드와 저장된 코드를 검증합니다.
        """
        # 이메일에 해당하는 인증 코드 조회
        verification = await verification_codes_collection.find_one({"email": email})
        if not verification:
            return False

        # 만료 시간 확인
        if verification.get("expires_at", datetime.min) < datetime.utcnow():
            # 만료된 코드는 삭제
            await verification_codes_collection.delete_one({"email": email})
            return False

        # 코드 일치 여부 확인
        if verification.get("code") != code:
            return False

        # 검증 성공 시 코드 삭제
        await verification_codes_collection.delete_one({"email": email})
        return True

    @staticmethod
    async def send_verification_email(email: str, code: str) -> None:
        """
        인증 코드가 포함된 이메일을 사용자에게 전송합니다.
        """
        message = MessageSchema(
            subject="버라이어티.AI 회원가입 인증 코드",
            recipients=[email],
            body=f"안녕하세요.\n인증 코드: [{code}]\n이 코드는 {settings.EMAIL_VERIFICATION_EXPIRE_MINUTES}분 후에 만료됩니다.",
            subtype="plain"
        )

        fm = FastMail(conf)
        await fm.send_message(message)

# 서비스 인스턴스
email_service = EmailService()

# 헬퍼 함수
async def send_verification_code(email: str) -> str:
    """
    이메일 인증 코드를 생성하고 이메일로 전송합니다.
    """
    code = EmailService.generate_verification_code()
    await EmailService.save_verification_code(email, code)
    await EmailService.send_verification_email(email, code)
    return code
