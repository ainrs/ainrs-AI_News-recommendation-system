import os
from typing import List, Dict, Any, Optional
import asyncio
import uuid
from datetime import datetime, timedelta
import json

from app.db.mongodb import get_mongodb_database, ai_models_collection, model_usage_collection

class ModelControllerService:
    def __init__(self):
        """
        AI 모델 컨트롤러 서비스 초기화
        이 서비스는 여러 AI 모델을 관리하고 모델 사용 통계를 추적합니다.
        """
        # MongoDB 컬렉션 (동기 방식)
        self.models_collection = ai_models_collection
        self.model_usage_collection = model_usage_collection

        # 비동기 초기화 플래그
        self.initialized = False
        self.async_db = None

        # 등록된 모델 목록 - 프로그램 시작 시 구성
        self.registered_models = {
            "openai_embedding": {
                "name": "OpenAI Embedding",
                "type": "embedding",
                "description": "OpenAI의 text-embedding-ada-002 모델을 사용한 텍스트 임베딩",
                "api_required": True,
                "status": "active"
            },
            "bilstm_trust": {
                "name": "BiLSTM Trust Analysis",
                "type": "trust_analysis",
                "description": "BiLSTM을 사용한 뉴스 신뢰도 분석",
                "api_required": False,
                "status": "active"
            },
            "sentiment_bert": {
                "name": "Sentiment BERT",
                "type": "sentiment_analysis",
                "description": "BERT를 사용한 감정 분석",
                "api_required": False,
                "status": "active"
            },
            "gpt3.5_controller": {
                "name": "GPT-3.5 Controller",
                "type": "langchain_controller",
                "description": "LangChain 오케스트레이션을 위한 GPT-3.5 컨트롤러",
                "api_required": True,
                "status": "active"
            }
        }

        # 모델 정보를 DB에 등록 (동기 방식)
        self._register_models_sync()

    def _register_models_sync(self):
        """
        모델 정보를 DB에 등록합니다 (동기 방식).
        """
        for model_id, model_info in self.registered_models.items():
            self.models_collection.update_one(
                {"model_id": model_id},
                {"$set": {
                    **model_info,
                    "model_id": model_id,
                    "updated_at": datetime.utcnow().isoformat()
                }},
                upsert=True
            )

    async def initialize(self):
        """
        비동기 초기화 - MongoDB 연결 설정 및 모델 정보 로드
        """
        if not self.initialized:
            self.async_db = await get_mongodb_database()
            self.async_models_collection = self.async_db["ai_models"]
            self.async_model_usage_collection = self.async_db["model_usage"]

            # 모델 정보를 DB에 등록
            for model_id, model_info in self.registered_models.items():
                await self.async_models_collection.update_one(
                    {"model_id": model_id},
                    {"$set": {
                        **model_info,
                        "model_id": model_id,
                        "updated_at": datetime.utcnow().isoformat()
                    }},
                    upsert=True
                )

            self.initialized = True

    async def record_model_usage(self, model_id: str, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        모델 사용 기록을 저장합니다.

        Args:
            model_id: 모델 ID
            user_id: 사용자 ID (선택 사항)
            metadata: 추가 메타데이터 (선택 사항)

        Returns:
            성공 여부
        """
        await self.initialize()

        try:
            # 사용 기록 생성
            usage_record = {
                "model_id": model_id,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }

            # DB에 저장
            await self.async_model_usage_collection.insert_one(usage_record)

            # 모델 사용 카운터 증가
            await self.async_models_collection.update_one(
                {"model_id": model_id},
                {"$inc": {"usage_count": 1}}
            )

            return True

        except Exception as e:
            print(f"모델 사용 기록 중 오류 발생: {e}")
            return False

    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        모델 정보를 가져옵니다.

        Args:
            model_id: 모델 ID

        Returns:
            모델 정보 또는 None
        """
        await self.initialize()

        try:
            model_info = await self.async_models_collection.find_one({"model_id": model_id})
            return model_info
        except Exception as e:
            print(f"모델 정보 조회 중 오류 발생: {e}")
            return None

    async def get_all_models(self) -> List[Dict[str, Any]]:
        """
        모든 등록된 모델 정보를 가져옵니다.

        Returns:
            모델 정보 목록
        """
        await self.initialize()

        try:
            models = await self.async_models_collection.find().to_list(length=100)
            return models
        except Exception as e:
            print(f"모델 목록 조회 중 오류 발생: {e}")
            return []

    async def update_model_status(self, model_id: str, status: str) -> bool:
        """
        모델 상태를 업데이트합니다.

        Args:
            model_id: 모델 ID
            status: 새 상태 ('active', 'inactive', 'error' 등)

        Returns:
            성공 여부
        """
        await self.initialize()

        try:
            result = await self.async_models_collection.update_one(
                {"model_id": model_id},
                {"$set": {
                    "status": status,
                    "updated_at": datetime.utcnow().isoformat()
                }}
            )

            return result.modified_count > 0

        except Exception as e:
            print(f"모델 상태 업데이트 중 오류 발생: {e}")
            return False

    async def get_usage_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        모델 사용 통계를 가져옵니다.

        Args:
            days: 통계를 계산할 이전 일수

        Returns:
            사용 통계 정보
        """
        await self.initialize()

        try:
            # 시작 날짜 계산
            start_date = datetime.utcnow() - timedelta(days=days)
            start_date_str = start_date.isoformat()

            # 각 모델별 사용 횟수 집계
            pipeline = [
                {"$match": {"timestamp": {"$gte": start_date_str}}},
                {"$group": {
                    "_id": "$model_id",
                    "count": {"$sum": 1}
                }}
            ]

            model_usage = await self.async_model_usage_collection.aggregate(pipeline).to_list(length=100)

            # 일별 사용 횟수 집계
            daily_pipeline = [
                {"$match": {"timestamp": {"$gte": start_date_str}}},
                {"$project": {
                    "date": {"$substr": ["$timestamp", 0, 10]},
                    "model_id": 1
                }},
                {"$group": {
                    "_id": {"date": "$date", "model_id": "$model_id"},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id.date": 1}}
            ]

            daily_usage = await self.async_model_usage_collection.aggregate(daily_pipeline).to_list(length=1000)

            # 결과 형식화
            model_counts = {item["_id"]: item["count"] for item in model_usage}

            daily_data = {}
            for item in daily_usage:
                date = item["_id"]["date"]
                model_id = item["_id"]["model_id"]
                count = item["count"]

                if date not in daily_data:
                    daily_data[date] = {}

                daily_data[date][model_id] = count

            return {
                "total_by_model": model_counts,
                "daily_usage": daily_data
            }

        except Exception as e:
            print(f"사용 통계 조회 중 오류 발생: {e}")
            return {
                "total_by_model": {},
                "daily_usage": {}
            }

    # 동기 API 메서드들 (기존 코드와의 호환성)
    def record_model_usage_sync(self, model_id: str, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        모델 사용 기록을 저장합니다 (동기 방식).
        """
        try:
            # 사용 기록 생성
            usage_record = {
                "model_id": model_id,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }

            # DB에 저장
            self.model_usage_collection.insert_one(usage_record)

            # 모델 사용 카운터 증가
            self.models_collection.update_one(
                {"model_id": model_id},
                {"$inc": {"usage_count": 1}}
            )

            return True

        except Exception as e:
            print(f"모델 사용 기록 중 오류 발생: {e}")
            return False

    def get_model_info_sync(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        모델 정보를 가져옵니다 (동기 방식).
        """
        try:
            model_info = self.models_collection.find_one({"model_id": model_id})
            return model_info
        except Exception as e:
            print(f"모델 정보 조회 중 오류 발생: {e}")
            return None

    # 누락된 메서드 추가
    async def get_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        모델 ID로 모델 정보를 가져옵니다.
        """
        return await self.get_model_info(model_id)

    async def toggle_model(self, model_id: str, enabled: bool) -> Optional[Dict[str, Any]]:
        """
        모델의 활성화 상태를 전환합니다.

        Args:
            model_id: 모델 ID
            enabled: 활성화 여부

        Returns:
            업데이트된 모델 정보 또는 None
        """
        await self.initialize()

        try:
            status = "active" if enabled else "inactive"

            result = await self.async_models_collection.update_one(
                {"model_id": model_id},
                {"$set": {
                    "status": status,
                    "updated_at": datetime.utcnow().isoformat()
                }}
            )

            if result.modified_count > 0:
                return await self.get_model_info(model_id)
            else:
                return None

        except Exception as e:
            print(f"모델 상태 토글 중 오류 발생: {e}")
            return None

    async def update_model_settings(self, model_id: str, settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        모델 설정을 업데이트합니다.

        Args:
            model_id: 모델 ID
            settings: 업데이트할 설정

        Returns:
            업데이트된 모델 정보 또는 None
        """
        await self.initialize()

        try:
            update_data = {
                "updated_at": datetime.utcnow().isoformat(),
                "settings": settings
            }

            result = await self.async_models_collection.update_one(
                {"model_id": model_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                return await self.get_model_info(model_id)
            else:
                return None

        except Exception as e:
            print(f"모델 설정 업데이트 중 오류 발생: {e}")
            return None

# 서비스 인스턴스를 가져오는 헬퍼 함수
_model_controller_service = None

def get_model_controller_service() -> ModelControllerService:
    """
    ModelControllerService 인스턴스를 가져옵니다. (싱글톤 패턴)
    """
    global _model_controller_service
    if _model_controller_service is None:
        _model_controller_service = ModelControllerService()
    return _model_controller_service
