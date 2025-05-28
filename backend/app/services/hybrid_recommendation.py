"""
하이브리드 추천 시스템
협업 필터링, 콘텐츠 기반 필터링, LLM 기반 추천을 결합한 하이브리드 추천 시스템
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np
from bson import ObjectId

# MongoDB 컬렉션
from app.db.mongodb import (
    news_collection,
    user_collection,
    user_interactions_collection
)

# 서비스
from app.services.collaborative_filtering import get_collaborative_filtering_service
from app.services.embedding_service import get_embedding_service
from app.services.langchain_service import get_langchain_service
from app.services.recommendation_service import get_recommendation_service

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HybridRecommendationService:
    """하이브리드 추천 시스템

    협업 필터링, 콘텐츠 기반 필터링, LLM 기반 추천을 결합하여
    Cold Start 문제와 데이터 희소성 문제를 해결합니다.
    """

    def __init__(self):
        """서비스 초기화"""
        self.collaborative_filtering = get_collaborative_filtering_service()
        self.embedding_service = get_embedding_service()
        self.langchain_service = get_langchain_service()
        self.recommendation_service = get_recommendation_service()

    async def get_personalized_recommendations(
        self,
        user_id: str,
        limit: int = 10,
        diversity_level: float = 0.3  # 0.0 ~ 1.0 (높을수록 다양성 강화)
    ) -> List[Dict[str, Any]]:
        """개인화된 뉴스 추천

        하이브리드 접근 방식을 사용하여 사용자에게 개인화된 뉴스를 추천합니다.
        새로운 사용자(Cold Start)와 기존 사용자에 대해 다른 전략을 적용합니다.

        Args:
            user_id: 사용자 ID
            limit: 최대 추천 개수
            diversity_level: 추천 결과의 다양성 수준 (0.0~1.0)

        Returns:
            추천된 뉴스 목록
        """
        try:
            # 사용자 상호작용 데이터 조회
            user_interactions = list(user_interactions_collection.find({
                "user_id": user_id
            }))

            # Cold Start 상황 여부 확인 (상호작용이 3개 미만)
            is_cold_start = len(user_interactions) < 3

            # 추천 뉴스 목록
            recommended_news = []

            if is_cold_start:
                # Cold Start 상황: 관심사 기반 + 인기 기사 혼합
                logger.info(f"Cold Start 상황 - 사용자: {user_id}")

                # 사용자 프로필 조회 (선택한 관심사 확인)
                user = user_collection.find_one({"_id": user_id})
                selected_interests = user.get("preferences", {}).get("categories", []) if user else []

                # 트렌딩 뉴스 가져오기
                trending_news = await self.recommendation_service.get_trending_news(limit=limit*2)

                # LLM 기반 콜드 스타트 추천 요청
                recommended_ids = await self.langchain_service.get_cold_start_recommendations(
                    is_new_user=len(user_interactions) == 0,
                    selected_interests=selected_interests,
                    trending_news=[{
                        "id": news.id,
                        "title": news.title,
                        "source": news.source,
                        "categories": news.categories
                    } for news in trending_news]
                )

                # 추천 결과가 없으면 트렌딩 뉴스 사용
                if not recommended_ids:
                    recommended_ids = [news.id for news in trending_news]

                # 최대 limit까지만 사용
                recommended_ids = recommended_ids[:limit]

                # 뉴스 상세 정보 가져오기
                for news_id in recommended_ids:
                    news = news_collection.find_one({"_id": news_id, "is_basic_info": False})
                    if news:
                        recommended_news.append(news)

            else:
                # 기존 사용자: 협업 필터링 + 콘텐츠 기반 필터링 + LLM 하이브리드
                logger.info(f"기존 사용자 추천 - 사용자: {user_id}")

                # 1. 협업 필터링 추천 (50%)
                cf_count = int(limit * 0.5)
                cf_news_ids = self.collaborative_filtering.get_recommendations_for_user(
                    user_id=user_id,
                    limit=cf_count
                )

                # 2. 콘텐츠 기반 추천 (30%)
                # 최근 상호작용한 뉴스 가져오기
                recent_interactions = sorted(
                    user_interactions,
                    key=lambda x: x.get("timestamp", datetime.min),
                    reverse=True
                )[:5]

                recent_news_ids = [i.get("news_id") for i in recent_interactions]
                content_count = int(limit * 0.3)

                # 각 최근 뉴스마다 유사한 뉴스 찾기
                content_news_ids = set()
                for news_id in recent_news_ids:
                    news = news_collection.find_one({"_id": news_id, "is_basic_info": False})
                    if news:
                        # 임베딩 기반 유사 뉴스 검색
                        query = f"{news.get('title', '')} {news.get('summary', '')}"
                        similar_news = await self.embedding_service.search_similar_news(
                            query=query,
                            limit=2  # 각 뉴스마다 2개씩만 가져오기
                        )

                        # 중복 제거하면서 추가
                        for item in similar_news:
                            if item.get("id") not in content_news_ids and item.get("id") not in cf_news_ids:
                                content_news_ids.add(item.get("id"))

                                if len(content_news_ids) >= content_count:
                                    break

                # 3. LLM 기반 추천 (20%) - 다양성 증진용
                llm_count = limit - len(cf_news_ids) - len(content_news_ids)

                # 사용자 관심사, 상호작용 이력 수집
                user = user_collection.find_one({"_id": user_id})
                interests = user.get("preferences", {}).get("categories", []) if user else []

                # 읽은 뉴스 제목 수집
                read_history = []
                for interaction in recent_interactions:
                    news_id = interaction.get("news_id")
                    news = news_collection.find_one({"_id": news_id, "is_basic_info": False})
                    if news:
                        read_history.append(news.get("title", ""))

                # 최신 뉴스 중 아직 추천되지 않은 뉴스 필터링
                excluded_ids = set(cf_news_ids) | content_news_ids
                recent_news_cursor = news_collection.find({
                    "_id": {"$nin": list(excluded_ids)},
                    "is_basic_info": False  # HTML 파싱 완료된 뉴스만 사용
                }).sort("published_date", -1).limit(limit)

                recent_news_list = list(recent_news_cursor)

                # LLM 기반 다양성 추천
                if interests and recent_news_list:
                    # 관심사 기반 쿼리 생성
                    query = " ".join(interests)

                    # LLM 기반 하이브리드 추천
                    news_list = [{
                        "id": str(news.get("_id")),
                        "title": news.get("title", ""),
                        "source": news.get("source", ""),
                        "categories": news.get("categories", [])
                    } for news in recent_news_list]

                    llm_recommendations = await self.langchain_service.get_recommendations(
                        interests=interests,
                        read_history=read_history,
                        query=query,
                        news_list=news_list
                    )

                    # 추천 결과가 있으면 다양성 강화 적용
                    if isinstance(llm_recommendations, dict) and not "error" in llm_recommendations:
                        # 점수 기반 정렬
                        scored_news = []
                        for news in recent_news_list:
                            news_id = str(news.get("_id"))
                            if news_id in llm_recommendations:
                                rec_data = llm_recommendations[news_id]
                                if isinstance(rec_data, dict):
                                    score = rec_data.get("score", 5)
                                    scored_news.append((news, score))

                        # 점수 순 정렬
                        scored_news.sort(key=lambda x: x[1], reverse=True)

                        # 상위 llm_count개 선택
                        llm_news_list = [news for news, _ in scored_news[:llm_count]]

                        # 다양성 강화 적용
                        if diversity_level > 0:
                            # 주요 관심사 추출
                            main_interests = interests[:3] if interests else []

                            # 현재 선택된 뉴스의 카테고리 분포
                            current_recommendations = [{
                                "id": str(news.get("_id")),
                                "title": news.get("title", ""),
                                "categories": news.get("categories", [])
                            } for news in llm_news_list]

                            # 다양성 강화
                            diversified_news = await self.langchain_service.diversify_recommendations(
                                main_interests=main_interests,
                                current_recommendations=current_recommendations,
                                diversity_target=diversity_level
                            )

                            # 다양성 강화 결과가 있으면 대체
                            if diversified_news and len(diversified_news) > 0:
                                # ID 추출
                                diverse_ids = [news.get("id") for news in diversified_news]

                                # 원본 뉴스 찾기
                                llm_news_list = []
                                for news_id in diverse_ids:
                                    news = news_collection.find_one({"_id": news_id, "is_basic_info": False})
                                    if news:
                                        llm_news_list.append(news)
                    else:
                        # LLM 추천 실패 시 최신 뉴스로 대체
                        llm_news_list = recent_news_list[:llm_count]
                else:
                    # 관심사가 없거나 최신 뉴스가 없는 경우
                    llm_news_list = recent_news_list[:llm_count]

                # 최종 추천 목록 통합
                # 1. 협업 필터링 결과
                for news_id in cf_news_ids:
                    news = news_collection.find_one({"_id": news_id, "is_basic_info": False})
                    if news:
                        recommended_news.append(news)

                # 2. 콘텐츠 기반 필터링 결과
                for news_id in content_news_ids:
                    news = news_collection.find_one({"_id": news_id, "is_basic_info": False})
                    if news:
                        recommended_news.append(news)

                # 3. LLM + 다양성 강화 결과
                recommended_news.extend(llm_news_list)

            # 최종 결과 가공
            result = []
            for news in recommended_news[:limit]:  # limit 개수만큼 제한
                result.append({
                    "id": str(news.get("_id")),
                    "title": news.get("title", ""),
                    "source": news.get("source", ""),
                    "published_date": news.get("published_date", datetime.utcnow()),
                    "summary": news.get("summary", ""),
                    "image_url": news.get("image_url", ""),
                    "categories": news.get("categories", []),
                    "trust_score": news.get("trust_score", 0.5),
                    "sentiment_score": news.get("sentiment_score", 0)
                })

            return result

        except Exception as e:
            logger.error(f"하이브리드 추천 생성 중 오류: {str(e)}")
            # 오류 발생 시 트렌딩 뉴스 반환
            trending_news = await self.recommendation_service.get_trending_news(limit=limit)
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

    async def get_interest_based_recommendations(
        self,
        categories: List[str],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """관심사 기반 뉴스 추천

        사용자가 선택한 관심 카테고리를 기반으로 뉴스를 추천합니다.
        회원가입하지 않은 사용자나 선호도를 설정한 새 사용자를 위한 기능입니다.

        Args:
            categories: 관심 카테고리 목록
            limit: 최대 추천 개수

        Returns:
            추천된 뉴스 목록
        """
        try:
            result = []

            if not categories:
                # 관심사가 없으면 트렌딩 뉴스 반환
                trending_news = await self.recommendation_service.get_trending_news(limit=limit)
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

            # 각 카테고리별로 최신 뉴스 가져오기
            per_category = max(1, limit // len(categories))

            for category in categories:
                # 카테고리 검색 쿼리
                query = {"categories": category}

                # 최신순 정렬
                news_cursor = news_collection.find(query).sort("published_date", -1).limit(per_category)

                # 결과 추가
                for news in news_cursor:
                    result.append({
                        "id": str(news.get("_id")),
                        "title": news.get("title", ""),
                        "source": news.get("source", ""),
                        "published_date": news.get("published_date", datetime.utcnow()),
                        "summary": news.get("summary", ""),
                        "image_url": news.get("image_url", ""),
                        "categories": news.get("categories", []),
                        "trust_score": news.get("trust_score", 0.5),
                        "sentiment_score": news.get("sentiment_score", 0)
                    })

            # 결과가 부족하면 트렌딩 뉴스로 보충
            if len(result) < limit:
                needed = limit - len(result)
                # 이미 추천된 ID 제외
                existing_ids = set(item["id"] for item in result)

                trending_news = await self.recommendation_service.get_trending_news(limit=needed*2)

                for news in trending_news:
                    if news.id not in existing_ids and len(result) < limit:
                        result.append({
                            "id": news.id,
                            "title": news.title,
                            "source": news.source,
                            "published_date": news.published_date,
                            "summary": news.summary,
                            "image_url": news.image_url,
                            "categories": news.categories,
                            "trust_score": news.trust_score,
                            "sentiment_score": news.sentiment_score
                        })
                        existing_ids.add(news.id)

            return result

        except Exception as e:
            logger.error(f"관심사 기반 추천 생성 중 오류: {str(e)}")
            # 오류 발생 시 트렌딩 뉴스 반환
            trending_news = await self.recommendation_service.get_trending_news(limit=limit)
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


# 서비스 인스턴스 관리
_hybrid_recommendation_service = None

def get_hybrid_recommendation_service() -> HybridRecommendationService:
    """하이브리드 추천 서비스 인스턴스를 반환합니다."""
    global _hybrid_recommendation_service
    if _hybrid_recommendation_service is None:
        _hybrid_recommendation_service = HybridRecommendationService()
    return _hybrid_recommendation_service
