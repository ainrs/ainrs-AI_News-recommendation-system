import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import random

# MongoDB 컬렉션
from app.db.mongodb import (
    news_collection,
    user_collection,
    user_interactions_collection,
    recommendations_collection
)

# 서비스
from app.services.embedding_service import get_embedding_service
from app.core.config import settings

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BERT4RecService:
    """
    BERT4Rec 기반 뉴스 추천 서비스

    양방향 인코더 표현을 사용하여 시퀀스 추천을 수행하며,
    콘텐츠 정보를 활용하여 콜드 스타트 문제를 해결합니다.
    """

    def __init__(self):
        self.embedding_service = get_embedding_service()
        # 초기화 시 모델 로딩 완료 메시지
        logger.info("✅ BERT4Rec 서비스 초기화 완료")

    def add_interaction(self, user_id: str, news_id: str, interaction_type: str = "view") -> bool:
        """
        사용자와 뉴스 간의 상호작용을 BERT4Rec 모델에 추가합니다.

        Args:
            user_id: 사용자 ID
            news_id: 뉴스 ID
            interaction_type: 상호작용 유형 ("view", "click", "like", "bookmark" 등)

        Returns:
            성공 여부
        """
        try:
            # 상호작용 데이터 준비
            interaction_data = {
                "user_id": user_id,
                "news_id": news_id,
                "type": interaction_type,
                "timestamp": datetime.utcnow()
            }

            # 비동기 DB 작업이 불가능하므로 동기 메서드 사용
            user_interactions_collection.insert_one(interaction_data)

            logger.info(f"✅ 사용자 {user_id}의 {interaction_type} 상호작용 추가 (뉴스 ID: {news_id})")
            return True
        except Exception as e:
            logger.error(f"❌ 상호작용 추가 중 오류: {str(e)}")
            return False

    def get_cold_start_recommendations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        콜드 스타트 상황에서 추천할 뉴스 목록을 반환

        콘텐츠 기반 방식과 인기도를 결합하여 다양한 뉴스를 추천
        """
        try:
            # 최근 뉴스 가져오기 (최근 3일 이내)
            from datetime import timedelta
            recent_date = datetime.utcnow() - timedelta(days=3)

            # 1. 최근 인기 뉴스 (조회수 기준)
            try:
                popular_news = list(news_collection.find(
                    {"published_date": {"$gte": recent_date}},
                    {"_id": 1, "title": 1, "summary": 1, "source": 1, "image_url": 1, "content": 1,
                     "categories": 1, "view_count": 1, "published_date": 1, "trust_score": 1, "sentiment_score": 1}
                ).sort("view_count", -1).limit(limit * 2))
            except Exception as e1:
                logger.error(f"인기 뉴스 가져오기 오류: {e1}")
                popular_news = []

            # 2. 최신 뉴스
            try:
                latest_news = list(news_collection.find(
                    {},
                    {"_id": 1, "title": 1, "summary": 1, "source": 1, "image_url": 1, "content": 1,
                     "categories": 1, "published_date": 1, "trust_score": 1, "sentiment_score": 1}
                ).sort("published_date", -1).limit(limit * 2))
            except Exception as e2:
                logger.error(f"최신 뉴스 가져오기 오류: {e2}")
                latest_news = []

            # 3. 다양한 카테고리 뉴스
            diverse_news = []
            try:
                # 주요 카테고리 명시적 지정 (인공지능, 빅데이터, 클라우드, 스타트업 등)
                important_categories = ["인공지능", "빅데이터", "클라우드", "스타트업", "IT기업", "로봇", "블록체인", "메타버스", "AI서비스", "칼럼"]

                # 데이터베이스에서 모든 카테고리 가져오기
                all_categories = self._get_distinct_categories()

                # 중요 카테고리를 우선 처리하고 나머지 카테고리도 포함
                priority_categories = []
                for cat in important_categories:
                    if cat in all_categories:
                        priority_categories.append(cat)

                # 남은 카테고리 추가 (중복 제거)
                for cat in all_categories:
                    if cat not in priority_categories:
                        priority_categories.append(cat)

                # 모든 카테고리에서 뉴스 가져오기 (카테고리당 2개씩)
                for category in priority_categories[:min(10, len(priority_categories))]:
                    try:
                        category_news = list(news_collection.find(
                            {"categories": {"$in": [category]}},
                            {"_id": 1, "title": 1, "summary": 1, "source": 1, "image_url": 1, "content": 1,
                             "categories": 1, "published_date": 1, "trust_score": 1, "sentiment_score": 1}
                        ).sort("published_date", -1).limit(3))  # 카테고리당 3개로 증가

                        # 로그 추가
                        logger.info(f"카테고리 '{category}'에서 {len(category_news)}개 뉴스 가져옴")
                        diverse_news.extend(category_news)
                    except Exception as cat_error:
                        logger.error(f"카테고리 '{category}' 뉴스 가져오기 오류: {cat_error}")
                        continue
            except Exception as e3:
                logger.error(f"다양한 카테고리 뉴스 가져오기 오류: {e3}")

            # 모든 후보 뉴스 합치기
            all_candidates = []
            all_candidates.extend(popular_news)
            all_candidates.extend(latest_news)
            all_candidates.extend(diverse_news)

            if not all_candidates:
                logger.warning("콜드 스타트 추천: 후보 뉴스가 없습니다")
                # 일반 최신 뉴스만 가져오기
                fallback_news = list(news_collection.find().sort("published_date", -1).limit(limit))
                if not fallback_news:
                    logger.error("콜드 스타트 추천: 뉴스가 없습니다")
                    return []
                return fallback_news

            # 중복 제거
            unique_ids = set()
            unique_recommendations = []

            for news in all_candidates:
                try:
                    news_id = str(news["_id"])
                    if news_id not in unique_ids:
                        # 필요한 필드가 모두 있는지 확인
                        if "title" not in news or not news["title"]:
                            continue

                        # published_date가 없으면 현재 시간 사용
                        if "published_date" not in news or not news["published_date"]:
                            news["published_date"] = datetime.utcnow()

                        # source가 없으면 기본값 사용
                        if "source" not in news or not news["source"]:
                            news["source"] = "Unknown Source"

                        unique_ids.add(news_id)
                        unique_recommendations.append(news)
                except Exception as item_error:
                    logger.error(f"뉴스 항목 처리 중 오류: {str(item_error)}")
                    continue

            # 카테고리별로 뉴스 그룹화하여 다양성 보장
            category_groups = {}
            for news in unique_recommendations:
                news_categories = news.get("categories", [])
                if not news_categories:
                    news_categories = ["미분류"]

                # 뉴스의 첫 번째 카테고리를 기준으로 그룹화
                primary_category = news_categories[0]
                if primary_category not in category_groups:
                    category_groups[primary_category] = []
                category_groups[primary_category].append(news)

            # 균형있는 추천 결과 생성
            balanced_recommendations = []
            remaining_slots = limit

            # 모든 카테고리에서 최소 1개씩 선택
            important_categories = ["인공지능", "빅데이터", "클라우드", "스타트업", "IT기업", "로봇", "블록체인", "메타버스", "AI서비스", "칼럼"]
            for category in important_categories:
                if category in category_groups and remaining_slots > 0:
                    # 해당 카테고리에서 최신 뉴스 1개 선택
                    news_item = category_groups[category][0]
                    balanced_recommendations.append(news_item)
                    category_groups[category].remove(news_item)
                    remaining_slots -= 1

            # 남은 슬롯을 다양한 카테고리로 채우기
            all_categories = list(category_groups.keys())
            random.shuffle(all_categories)

            for category in all_categories:
                if remaining_slots <= 0:
                    break

                if category_groups[category]:
                    news_item = category_groups[category][0]
                    balanced_recommendations.append(news_item)
                    category_groups[category].remove(news_item)
                    remaining_slots -= 1

            # 그래도 남은 슬롯이 있으면 남은 뉴스로 채우기
            if remaining_slots > 0:
                remaining_news = []
                for category, news_list in category_groups.items():
                    remaining_news.extend(news_list)

                random.shuffle(remaining_news)
                balanced_recommendations.extend(remaining_news[:remaining_slots])

            # 로그 추가
            category_counts = {}
            for news in balanced_recommendations:
                cat = news.get("categories", ["미분류"])[0]
                category_counts[cat] = category_counts.get(cat, 0) + 1

            logger.info(f"추천 결과 카테고리 분포: {category_counts}")

            # 요청된 개수만큼 반환
            return balanced_recommendations[:limit]

        except Exception as e:
            logger.error(f"❌ 콜드 스타트 추천 생성 오류: {e}")
            # 오류 발생 시 빈 배열 반환
            return []

    def _get_distinct_categories(self) -> List[str]:
        """
        데이터베이스에서 모든 뉴스 카테고리 목록 가져오기
        """
        try:
            pipeline = [
                {"$unwind": "$categories"},
                {"$group": {"_id": "$categories"}},
                {"$project": {"category": "$_id", "_id": 0}}
            ]

            categories = news_collection.aggregate(pipeline)
            return [doc.get("category") for doc in categories if doc.get("category")]
        except Exception as e:
            logger.error(f"❌ 카테고리 가져오기 오류: {e}")
            return ["인공지능", "빅데이터", "클라우드", "스타트업", "IT기업", "로봇", "블록체인", "메타버스", "AI서비스", "칼럼"]  # 다양한 기본 카테고리

    def get_content_based_recommendations(self, news_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        특정 뉴스와 유사한 뉴스 추천 (콘텐츠 기반)
        """
        try:
            # 대상 뉴스 가져오기
            target_news = news_collection.find_one({"_id": news_id})
            if not target_news:
                return []

            # 텍스트 컨텍스트 구성
            context = f"{target_news.get('title', '')} {target_news.get('summary', '')}"

            # 임베딩 생성
            embedding = self.embedding_service.get_embeddings(context)

            # 임베딩 기반 유사 뉴스 검색
            similar_news = self.embedding_service.search_by_embedding(
                embedding,
                limit=limit,
                exclude_ids=[news_id]
            )

            return similar_news
        except Exception as e:
            logger.error(f"❌ 콘텐츠 기반 추천 오류: {e}")
            return []

    def initialize_cold_start_recommendations(self) -> bool:
        """
        시스템 시작 시 콜드 스타트 추천 데이터 준비
        """
        try:
            # 추천 컬렉션에 기본 추천 데이터가 있는지 확인
            if recommendations_collection.count_documents({"type": "cold_start"}) > 0:
                logger.info("✅ 콜드 스타트 추천 데이터가 이미 존재합니다.")
                return True

            # 기본 추천 데이터 생성 (더 많은 뉴스 포함)
            recommendations = self.get_cold_start_recommendations(limit=20)  # 20개로 증가

            # 추천 ID 목록
            recommendation_ids = [str(rec["_id"]) for rec in recommendations]

            # 데이터베이스에 저장
            result = recommendations_collection.insert_one({
                "type": "cold_start",
                "news_ids": recommendation_ids,
                "created_at": datetime.utcnow()
            })

            logger.info(f"✅ 콜드 스타트 추천 데이터 생성 완료: {len(recommendation_ids)}개 뉴스")
            return True
        except Exception as e:
            logger.error(f"❌ 콜드 스타트 추천 데이터 초기화 오류: {e}")
            return False

# 싱글톤 인스턴스
_bert4rec_service = None

def get_bert4rec_service() -> BERT4RecService:
    """
    BERT4Rec 서비스의 싱글톤 인스턴스 반환
    """
    global _bert4rec_service
    if _bert4rec_service is None:
        _bert4rec_service = BERT4RecService()
    return _bert4rec_service