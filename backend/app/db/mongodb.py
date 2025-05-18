from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
import motor.motor_asyncio
from typing import Optional

from app.core.config import settings

import logging
logger = logging.getLogger(__name__)

try:
    logger.info(f"MongoDB: 연결 시도 중... URI: {settings.MONGODB_URI}, DB: {settings.MONGODB_DB_NAME}")
    client = MongoClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=5000,
        tls=True,  # SSL/TLS 활성화
        tlsAllowInvalidCertificates=True  # 유효하지 않은 인증서 허용
    )
    # 연결 테스트를 위해 ping 명령 실행
    client.admin.command('ping')
    db = client[settings.MONGODB_DB_NAME]
    logger.info("MongoDB: 연결 성공!")
except Exception as e:
    logger.error(f"MongoDB 연결 실패: {str(e)}")
    # 에러 발생 시에도 객체는 생성하여 앱 실행은 가능하게 함
    client = MongoClient(
        settings.MONGODB_URI,
        tls=True,
        tlsAllowInvalidCertificates=True
    )
    db = client[settings.MONGODB_DB_NAME]

news_collection = db["news"]
embeddings_collection = db["embeddings"]
user_collection = db["users"]
user_interactions_collection = db["user_interactions"]
metadata_collection = db["metadata"]
recommendations_collection = db["recommendations"]
ai_models_collection = db["ai_models"]
model_usage_collection = db["model_usage"]
verification_codes_collection = db["verification_codes"]

news_collection.create_index("url", unique=True)
news_collection.create_index("published_date")
news_collection.create_index("source")
embeddings_collection.create_index("news_id")
user_interactions_collection.create_index([("user_id", 1), ("news_id", 1)])
recommendations_collection.create_index("user_id")
recommendations_collection.create_index("timestamp")
ai_models_collection.create_index("model_id", unique=True)
model_usage_collection.create_index("model_id")
model_usage_collection.create_index("timestamp")

def get_db() -> Database:
    """
    Get MongoDB database instance
    """
    return db

def get_collection(collection_name: str) -> Collection:
    """
    Get MongoDB collection by name
    """
    return db[collection_name]

_async_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
_async_db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None

async def get_mongodb_database() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """
    MongoDB 데이터베이스를 가져옵니다.
    """
    global _async_db

    if _async_db is None:
        client = await get_mongodb_client()
        _async_db = client[settings.MONGODB_DB_NAME]

        # 인덱스 생성
        await _ensure_indexes(_async_db)

    return _async_db

async def get_mongodb_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    """
    MongoDB 클라이언트를 가져옵니다.
    """
    global _async_client

    if _async_client is None:
        try:
            logger.info(f"MongoDB 비동기 클라이언트 연결 시도 중... URI: {settings.MONGODB_URI}")
            _async_client = motor.motor_asyncio.AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                tls=True,
                tlsAllowInvalidCertificates=True
            )
            # 연결 테스트
            await _async_client.admin.command('ping')
            logger.info("MongoDB 비동기 클라이언트 연결 성공!")
        except Exception as e:
            logger.error(f"MongoDB 비동기 클라이언트 연결 실패: {str(e)}")
            # 에러 발생해도 앱 작동을 위해 클라이언트 생성
            _async_client = motor.motor_asyncio.AsyncIOMotorClient(
                settings.MONGODB_URI,
                tls=True,
                tlsAllowInvalidCertificates=True
            )

    return _async_client

async def _ensure_indexes(db: motor.motor_asyncio.AsyncIOMotorDatabase) -> None:
    """
    필요한 인덱스를 생성합니다.
    """
    # 인덱스 생성 전에 id가 null인 문서들을 처리
    try:
        # id가 null인 문서들 확인
        null_id_docs = await db["news"].count_documents({"id": None})
        if null_id_docs > 0:
            logger.warning(f"id가 null인 {null_id_docs}개 문서 확인됨. 이 문서들을 수정합니다.")

            # id가 null인 문서들에 임의의 id 할당
            import uuid
            cursor = db["news"].find({"id": None})
            async for doc in cursor:
                doc_id = str(uuid.uuid4())
                await db["news"].update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"id": doc_id}}
                )
            logger.info("id가 null인 문서들 수정 완료")
    except Exception as e:
        logger.error(f"id가 null인 문서 처리 중 오류 발생: {str(e)}")

    # 뉴스 컬렉션 인덱스
    try:
        # 기존 인덱스 삭제 시도
        try:
            await db["news"].drop_index("id_1")
            logger.info("기존 id 인덱스 삭제 성공")
        except Exception as e:
            logger.debug(f"기존 인덱스 삭제 중 오류 (무시됨): {str(e)}")

        # 중복 문서 제거 (id가 null인 문서를 한 번 더 삭제)
        await db["news"].delete_many({"id": None})

        # 인덱스 생성
        await db["news"].create_index("id", unique=True)
        logger.info("id 인덱스 생성 성공")
    except Exception as idx_error:
        logger.error(f"id 인덱스 생성 중 오류: {str(idx_error)}")
    await db["news"].create_index("source")
    await db["news"].create_index("categories")
    await db["news"].create_index("published_at")
    await db["news"].create_index([("title", "text"), ("content", "text")])

    # 사용자 컬렉션 인덱스
    await db["users"].create_index("id", unique=True)
    await db["users"].create_index("username", unique=True)
    await db["users"].create_index("email", unique=True)

    # 상호작용 컬렉션 인덱스
    await db["user_interactions"].create_index([("user_id", 1), ("article_id", 1)])
    await db["user_interactions"].create_index("timestamp")

    # 추천 컬렉션 인덱스
    await db["recommendations"].create_index("user_id")
    await db["recommendations"].create_index("timestamp")

    # AI 모델 컬렉션 인덱스
    await db["ai_models"].create_index("model_id", unique=True)

    # 모델 사용 컬렉션 인덱스
    await db["model_usage"].create_index("model_id")
    await db["model_usage"].create_index("timestamp")

    # 이메일 인증 코드 컬렉션 인덱스
    await db["verification_codes"].create_index("email", unique=True)
    await db["verification_codes"].create_index("expires_at", expireAfterSeconds=0)

async def close_mongodb_connection() -> None:
    """
    MongoDB 연결을 닫습니다.
    """
    global _async_client

    if _async_client is not None:
        _async_client.close()
        _async_client = None
