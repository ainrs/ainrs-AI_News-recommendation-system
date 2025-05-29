"""
요약 캐싱 시스템
- 중복 API 호출 방지
- 요약 결과 저장 및 재활용
- 비용 최적화
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)

class SummaryCacheService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.summary_cache

    def _generate_content_hash(self, content: str) -> str:
        """컨텐츠 해시 생성 (중복 감지용)"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    async def get_cached_summary(self, content: str, analysis_type: str = "summary") -> Optional[Dict[str, Any]]:
        """캐시된 요약 결과 조회"""
        try:
            content_hash = self._generate_content_hash(content)

            cached_result = await self.collection.find_one({
                "content_hash": content_hash,
                "analysis_type": analysis_type,
                "expires_at": {"$gt": datetime.utcnow()}
            })

            if cached_result:
                logger.info(f"캐시 히트: {analysis_type} - {content_hash[:8]}")
                return {
                    "summary": cached_result["summary"],
                    "key_points": cached_result.get("key_points", []),
                    "cached": True,
                    "created_at": cached_result["created_at"]
                }

            return None

        except Exception as e:
            logger.error(f"캐시 조회 오류: {e}")
            return None

    async def cache_summary(self,
                           content: str,
                           summary: str,
                           key_points: list = None,
                           analysis_type: str = "summary",
                           cache_duration_hours: int = 24) -> bool:
        """요약 결과 캐싱"""
        try:
            content_hash = self._generate_content_hash(content)
            expires_at = datetime.utcnow() + timedelta(hours=cache_duration_hours)

            cache_doc = {
                "content_hash": content_hash,
                "analysis_type": analysis_type,
                "summary": summary,
                "key_points": key_points or [],
                "created_at": datetime.utcnow(),
                "expires_at": expires_at,
                "content_length": len(content)
            }

            # upsert로 중복 방지
            await self.collection.update_one(
                {"content_hash": content_hash, "analysis_type": analysis_type},
                {"$set": cache_doc},
                upsert=True
            )

            logger.info(f"요약 캐시 저장: {analysis_type} - {content_hash[:8]}")
            return True

        except Exception as e:
            logger.error(f"캐시 저장 오류: {e}")
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        try:
            total_count = await self.collection.count_documents({})
            active_count = await self.collection.count_documents({
                "expires_at": {"$gt": datetime.utcnow()}
            })

            # 분석 타입별 통계
            pipeline = [
                {"$match": {"expires_at": {"$gt": datetime.utcnow()}}},
                {"$group": {
                    "_id": "$analysis_type",
                    "count": {"$sum": 1}
                }}
            ]

            type_stats = {}
            async for result in self.collection.aggregate(pipeline):
                type_stats[result["_id"]] = result["count"]

            return {
                "total_cached": total_count,
                "active_cached": active_count,
                "expired_cached": total_count - active_count,
                "by_type": type_stats
            }

        except Exception as e:
            logger.error(f"캐시 통계 조회 오류: {e}")
            return {}

    async def cleanup_expired_cache(self) -> int:
        """만료된 캐시 정리"""
        try:
            result = await self.collection.delete_many({
                "expires_at": {"$lt": datetime.utcnow()}
            })

            deleted_count = result.deleted_count
            if deleted_count > 0:
                logger.info(f"만료된 캐시 {deleted_count}개 정리 완료")

            return deleted_count

        except Exception as e:
            logger.error(f"캐시 정리 오류: {e}")
            return 0

    async def clear_all_cache(self) -> int:
        """모든 캐시 삭제 (개발/테스트용)"""
        try:
            result = await self.collection.delete_many({})
            deleted_count = result.deleted_count
            logger.info(f"전체 캐시 {deleted_count}개 삭제 완료")
            return deleted_count

        except Exception as e:
            logger.error(f"전체 캐시 삭제 오류: {e}")
            return 0

# 캐시 서비스 인스턴스
summary_cache_service = None

def get_summary_cache_service() -> SummaryCacheService:
    """캐시 서비스 인스턴스 반환"""
    return summary_cache_service

def initialize_summary_cache_service(db: AsyncIOMotorDatabase):
    """캐시 서비스 초기화"""
    global summary_cache_service
    summary_cache_service = SummaryCacheService(db)
