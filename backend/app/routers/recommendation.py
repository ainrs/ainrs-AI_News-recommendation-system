"""
추천 시스템 API 라우터
하이브리드 추천 시스템을 위한 FastAPI 라우터입니다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.db.mongodb import get_mongodb_database
from app.services.hybrid_recommendation import get_hybrid_recommendation_service
from app.services.recommendation_service import get_recommendation_service
from app.services.bert4rec_service import get_bert4rec_service

router = APIRouter(tags=["recommendation"])

class InterestBasedRequest(BaseModel):
    categories: List[str]
    limit: int = 8

class NewsRecommendation(BaseModel):
    id: str
    title: str
    source: str
    published_date: datetime
    summary: Optional[str] = None
    image_url: Optional[str] = None
    categories: List[str] = []
    trust_score: Optional[float] = None
    sentiment_score: Optional[float] = None

@router.get("/recommendation/personalized/{user_id}", response_model=List[NewsRecommendation])
async def get_personalized_recommendations_main(
    user_id: str,
    limit: int = Query(8, ge=1, le=20),
    diversity_level: float = Query(0.3, ge=0.0, le=1.0)
):
    """
    사용자에게 개인화된 뉴스 추천을 제공합니다.

    하이브리드 추천 시스템을 사용하여 협업 필터링, 콘텐츠 기반 필터링,
    LLM 추천을 결합한 결과를 반환합니다.

    Cold Start 문제와 데이터 희소성 문제를 자동으로 처리합니다.

    Args:
        user_id: 사용자 ID
        limit: 최대 추천 개수 (기본값: 8)
        diversity_level: 추천 다양성 수준 (0.0-1.0, 기본값: 0.3)

    Returns:
        List[NewsRecommendation]: 추천된 뉴스 목록
    """
    try:
        recommendation_service = get_hybrid_recommendation_service()
        recommendations = await recommendation_service.get_personalized_recommendations(
            user_id=user_id,
            limit=limit,
            diversity_level=diversity_level
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 생성 중 오류 발생: {str(e)}")

@router.get("/recommendations/{user_id}", response_model=List[NewsRecommendation])
async def get_recommendations_legacy(
    user_id: str,
    limit: int = Query(10, ge=1, le=20),
    diversity_level: float = Query(0.3, ge=0.0, le=1.0)
):
    """
    사용자에게 개인화된 뉴스 추천을 제공합니다. (레거시 엔드포인트)

    이전 버전 API와의 호환성을 위해 유지됩니다.

    Args:
        user_id: 사용자 ID
        limit: 최대 추천 개수 (기본값: 10)
        diversity_level: 추천 다양성 수준 (0.0-1.0, 기본값: 0.3)

    Returns:
        List[NewsRecommendation]: 추천된 뉴스 목록
    """
    recommendation_service = get_hybrid_recommendation_service()
    try:
        recommendations = await recommendation_service.get_personalized_recommendations(
            user_id=user_id,
            limit=limit,
            diversity_level=diversity_level
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 생성 중 오류 발생: {str(e)}")

@router.post("/recommendation/interests", response_model=List[NewsRecommendation])
async def get_interest_based_recommendations_main(
    request: InterestBasedRequest
):
    """
    사용자의 관심사를 기반으로 뉴스를 추천합니다.

    로그인하지 않은 사용자나 새로운 사용자를 위해
    선택한 카테고리 기반으로 추천을 제공합니다.

    Args:
        request: 관심 카테고리 목록과 limit

    Returns:
        List[NewsRecommendation]: 추천된 뉴스 목록
    """
    try:
        recommendation_service = get_hybrid_recommendation_service()
        recommendations = await recommendation_service.get_interest_based_recommendations(
            categories=request.categories,
            limit=request.limit
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 생성 중 오류 발생: {str(e)}")

@router.post("/recommendation/interests", response_model=List[NewsRecommendation])
async def get_interest_based_recommendations_legacy(
    request: InterestBasedRequest
):
    """
    사용자의 관심사를 기반으로 뉴스를 추천합니다. (레거시 엔드포인트)

    이전 버전 API와의 호환성을 위해 유지됩니다.

    Args:
        request: 관심 카테고리 목록과 limit

    Returns:
        List[NewsRecommendation]: 추천된 뉴스 목록
    """
    recommendation_service = get_hybrid_recommendation_service()
    try:
        recommendations = await recommendation_service.get_interest_based_recommendations(
            categories=request.categories,
            limit=request.limit
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 생성 중 오류 발생: {str(e)}")

@router.get("/recommendation/trending", response_model=List[NewsRecommendation])
async def get_trending_recommendations_main(
    limit: int = Query(8, ge=1, le=20)
):
    """
    트렌딩 뉴스를 추천합니다.

    최신성, 인기도, 신뢰도를 결합하여 가장 트렌딩한 뉴스를 반환합니다.

    Args:
        limit: 최대 추천 개수 (기본값: 8)

    Returns:
        List[NewsRecommendation]: 추천된 뉴스 목록
    """
    try:
        recommendation_service = get_recommendation_service()
        trending_news = await recommendation_service.get_trending_news(limit=limit)
        return [{
            "id": news.id,
            "title": news.title,
            "source": news.source,
            "published_date": news.published_date,
            "summary": news.summary,
            "image_url": news.image_url,
            "categories": news.categories,
            "trust_score": news.trust_score,
            "sentiment_score": news.sentiment_score
        } for news in trending_news]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 생성 중 오류 발생: {str(e)}")

@router.get("/news/trending", response_model=List[NewsRecommendation])
async def get_trending_recommendations_news_legacy(
    limit: int = Query(10, ge=1, le=20)
):
    """
    트렌딩 뉴스를 추천합니다. (레거시 엔드포인트)

    이전 버전 API와의 호환성을 위해 유지됩니다.

    Args:
        limit: 최대 추천 개수 (기본값: 10)

    Returns:
        List[NewsRecommendation]: 추천된 뉴스 목록
    """
    recommendation_service = get_recommendation_service()
    try:
        trending_news = await recommendation_service.get_trending_news(limit=limit)
        return [{
            "id": news.id,
            "title": news.title,
            "source": news.source,
            "published_date": news.published_date,
            "summary": news.summary,
            "image_url": news.image_url,
            "categories": news.categories,
            "trust_score": news.trust_score,
            "sentiment_score": news.sentiment_score
        } for news in trending_news]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 생성 중 오류 발생: {str(e)}")

@router.get("/news/cold-start", response_model=List[NewsRecommendation])
async def get_cold_start_recommendations(
    limit: int = Query(5, description="반환할 추천 뉴스의 수")
):
    """
    콜드 스타트 문제를 위한, 신규 사용자/방문자를 위한 추천 뉴스를 제공합니다.
    사용자 데이터나 상호작용 내역이 없는 상태에서도 다양하고 유익한 뉴스를 추천합니다.

    Args:
        limit: 반환할 뉴스 항목 수

    Returns:
        List[NewsRecommendation]: 추천된 뉴스 목록
    """
    bert4rec_service = get_bert4rec_service()
    try:
        cold_start_news = bert4rec_service.get_cold_start_recommendations(limit=limit)
        return [
            {
                "id": str(news.get("_id")),
                "title": news.get("title", ""),
                "source": news.get("source", ""),
                "published_date": news.get("published_date", datetime.utcnow()),
                "summary": news.get("summary", ""),
                "image_url": news.get("image_url", ""),
                "categories": news.get("categories", []),
                "trust_score": news.get("trust_score", 0.7),
                "sentiment_score": news.get("sentiment_score", 0.0)
            } for news in cold_start_news
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"콜드 스타트 추천 생성 중 오류 발생: {str(e)}")
