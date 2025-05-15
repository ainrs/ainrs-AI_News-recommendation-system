from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId
from pydantic import BaseModel

from app.db.mongodb import get_mongodb_database

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}}
)

# 상호작용 모델
class InteractionCreate(BaseModel):
    user_id: str
    news_id: str
    interaction_type: str
    metadata: Optional[Dict[str, Any]] = None

class InteractionResponse(BaseModel):
    id: str
    user_id: str
    news_id: str
    type: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

# 사용자 상호작용 엔드포인트
@router.get("/interactions", response_model=Dict[str, Any])
async def get_user_interactions(
    user_id: str,
    news_id: Optional[str] = None,
    interaction_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db = Depends(get_mongodb_database)
):
    """
    사용자의 상호작용 이력을 가져옵니다.
    """
    try:
        # 사용자 확인
        user_collection = db["users"]
        user = await user_collection.find_one({"_id": user_id})
        if not user:
            # 사용자가 없으면 기본 사용자 생성 (실제 앱에서는 인증 필요)
            user = {
                "_id": user_id,
                "name": "User " + user_id[-4:],
                "created_at": datetime.utcnow()
            }
            await user_collection.insert_one(user)

        # 상호작용 쿼리 생성
        query = {"user_id": user_id}

        if news_id:
            query["news_id"] = news_id

        if interaction_type:
            query["type"] = interaction_type

        # 상호작용 가져오기
        interaction_collection = db["user_interactions"]
        cursor = interaction_collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)

        interactions = []
        async for interaction in cursor:
            interactions.append({
                "id": str(interaction["_id"]),
                "user_id": interaction["user_id"],
                "news_id": interaction["news_id"],
                "type": interaction["type"],
                "timestamp": interaction["timestamp"],
                "metadata": interaction.get("metadata", {})
            })

        return {
            "user_id": user_id,
            "interactions": interactions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching interactions: {str(e)}")

@router.post("/interaction", response_model=Dict[str, Any])
async def create_interaction(
    interaction: InteractionCreate,
    db = Depends(get_mongodb_database)
):
    """
    사용자 상호작용을 기록합니다.
    """
    try:
        # 뉴스 존재 확인
        news_collection = db["news"]
        news = await news_collection.find_one({"_id": ObjectId(interaction.news_id)})
        if not news:
            raise HTTPException(status_code=404, detail="News not found")

        # 상호작용 유효성 검사
        valid_types = ["view", "click", "read", "like", "share", "bookmark"]
        if interaction.interaction_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid interaction type. Must be one of: {', '.join(valid_types)}")

        # 상호작용 데이터 생성
        interaction_data = {
            "user_id": interaction.user_id,
            "news_id": interaction.news_id,
            "type": interaction.interaction_type,
            "timestamp": datetime.utcnow(),
            "metadata": interaction.metadata or {}
        }

        # 중복 상호작용 검사 (좋아요, 북마크와 같은 토글 유형)
        if interaction.interaction_type in ["like", "bookmark"]:
            interaction_collection = db["user_interactions"]
            existing = await interaction_collection.find_one({
                "user_id": interaction.user_id,
                "news_id": interaction.news_id,
                "type": interaction.interaction_type
            })

            if existing:
                # 이미 존재하는 상호작용은 제거 (토글)
                await interaction_collection.delete_one({"_id": existing["_id"]})

                # 뉴스 카운터 업데이트
                if interaction.interaction_type == "like":
                    await news_collection.update_one(
                        {"_id": ObjectId(interaction.news_id)},
                        {"$inc": {"like_count": -1}}
                    )

                return {
                    "message": f"{interaction.interaction_type} removed",
                    "status": "removed"
                }

        # 상호작용 저장
        interaction_collection = db["user_interactions"]
        result = await interaction_collection.insert_one(interaction_data)

        # 뉴스 컬렉션의 카운터 업데이트
        if interaction.interaction_type == "view":
            await news_collection.update_one(
                {"_id": ObjectId(interaction.news_id)},
                {"$inc": {"view_count": 1}}
            )
        elif interaction.interaction_type == "like":
            await news_collection.update_one(
                {"_id": ObjectId(interaction.news_id)},
                {"$inc": {"like_count": 1}}
            )
        elif interaction.interaction_type == "share":
            await news_collection.update_one(
                {"_id": ObjectId(interaction.news_id)},
                {"$inc": {"share_count": 1}}
            )

        return {
            "id": str(result.inserted_id),
            "message": f"{interaction.interaction_type} recorded successfully",
            "status": "created"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording interaction: {str(e)}")

# 추천 관련 엔드포인트
@router.get("/{user_id}/recommendations", response_model=List[Dict[str, Any]])
async def get_user_recommendations(
    user_id: str,
    limit: int = Query(10, ge=1, le=50),
    db = Depends(get_mongodb_database)
):
    """
    사용자 맞춤 뉴스 추천을 가져옵니다.
    """
    try:
        # 사용자 존재 확인
        user_collection = db["users"]
        user = await user_collection.find_one({"_id": user_id})
        if not user:
            # 사용자가 없으면 기본 사용자 생성
            user = {
                "_id": user_id,
                "name": "User " + user_id[-4:],
                "created_at": datetime.utcnow()
            }
            await user_collection.insert_one(user)

        # 추천 기록 가져오기
        recommendation_collection = db["recommendations"]
        recommendations = await recommendation_collection.find_one({
            "user_id": user_id,
            "timestamp": {"$gt": datetime.utcnow() - timedelta(days=1)}  # 최근 1일 내 추천
        })

        if not recommendations:
            # 추천 기록이 없거나 오래된 경우 최신 뉴스 반환
            news_collection = db["news"]
            cursor = news_collection.find().sort("published_date", -1).limit(limit)

            news_list = []
            async for news in cursor:
                news_list.append({
                    "id": str(news["_id"]),
                    "title": news.get("title", ""),
                    "source": news.get("source", ""),
                    "published_date": news.get("published_date", datetime.utcnow()),
                    "summary": news.get("summary", ""),
                    "image_url": news.get("image_url", ""),
                    "categories": news.get("categories", []),
                    "recommendation_type": "latest"
                })

            return news_list

        # 추천된 뉴스 ID 목록
        recommended_ids = [rec["news_id"] for rec in recommendations.get("recommendations", [])]

        # 추천된 뉴스 정보 가져오기
        news_collection = db["news"]
        result = []

        for rec in recommendations.get("recommendations", [])[:limit]:
            try:
                news_id = rec["news_id"]
                news = await news_collection.find_one({"_id": ObjectId(news_id)})

                if news:
                    result.append({
                        "id": str(news["_id"]),
                        "title": news.get("title", ""),
                        "source": news.get("source", ""),
                        "published_date": news.get("published_date", datetime.utcnow()),
                        "summary": news.get("summary", ""),
                        "image_url": news.get("image_url", ""),
                        "categories": news.get("categories", []),
                        "recommendation_score": rec.get("score", 0),
                        "recommendation_reason": rec.get("reason", "Based on your interests"),
                        "recommendation_type": rec.get("type", "personalized")
                    })
            except Exception as e:
                print(f"Error processing recommendation {news_id}: {str(e)}")
                continue

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recommendations: {str(e)}")
