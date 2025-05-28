import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

# LangChain
from langchain.chains import LLMChain
from langchain_community.chat_models import ChatOpenAI  # 수정: community 패키지 사용
from langchain.prompts import ChatPromptTemplate
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import EmbeddingsFilter

# MongoDB
from app.db.mongodb import (
    news_collection,
    user_collection,
    user_interactions_collection
)

# Services
from app.services.embedding_service import get_embedding_service
from app.services.langchain_service import get_langchain_service
from app.services.vector_store_service import get_vector_store_service

# Models
from app.models.news import NewsSearchQuery, NewsSummary

# Config
from app.core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RecommendationService:
    """Service for recommending news articles to users"""

    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.langchain_service = get_langchain_service()
        self.vector_store_service = get_vector_store_service()

        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.2,
            openai_api_key=settings.OPENAI_API_KEY
        )
        self._setup_chains()

    def _setup_chains(self):
        """Setup LangChain chains"""
        # News summarization prompt
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert news editor who creates concise, informative summaries.
             Keep the summary factual and objective. Summary should be 1-2 sentences."""),
            ("user", "Summarize the following news article:\n\nTitle: {title}\n\nContent: {content}")
        ])

        # Summary chain
        self.summary_chain = LLMChain(
            llm=self.llm,
            prompt=summary_prompt,
            output_key="summary"
        )

        # Keyword extraction prompt
        keyword_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at extracting the most important keywords from text.
            Extract 3-5 keywords that best represent the main topics of this article.
            Return the keywords as a comma-separated list."""),
            ("user", "Extract keywords from this article:\n\nTitle: {title}\n\nContent: {content}")
        ])

        # Keyword chain
        self.keyword_chain = LLMChain(
            llm=self.llm,
            prompt=keyword_prompt,
            output_key="keywords"
        )

        # Category classification prompt
        category_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert news categorizer.
            Assign the most appropriate category to this article from the following list:
            Politics, Business, Technology, Science, Health, Sports, Entertainment, World, Environment, Education.
            Return only the category name, nothing else."""),
            ("user", "Assign a category to this article:\n\nTitle: {title}\n\nContent: {content}")
        ])

        # Category chain
        self.category_chain = LLMChain(
            llm=self.llm,
            prompt=category_prompt,
            output_key="category"
        )

    async def process_article_metadata(self, news_id: str) -> Dict[str, Any]:
        """Process and enrich article metadata using LLM chains"""
        # Get news article (only HTML-parsed ones)
        news = news_collection.find_one({"_id": news_id, "is_basic_info": False})
        if not news:
            return {"success": False, "error": "Article not found"}

        try:
            # Extract title and content
            title = news["title"]

            # Limit content length
            content = news["content"]
            if len(content) > 4000:
                content = content[:4000]

            # Generate summary
            summary_result = self.summary_chain.run(title=title, content=content)

            # Extract keywords
            keyword_result = self.keyword_chain.run(title=title, content=content)
            keywords = [k.strip() for k in keyword_result.split(',')]

            # Classify category
            category_result = self.category_chain.run(title=title, content=content)
            categories = [category_result.strip()]

            # Update article in database
            news_collection.update_one(
                {"_id": news_id},
                {"$set": {
                    "summary": summary_result.strip(),
                    "keywords": keywords,
                    "categories": categories,
                    "updated_at": datetime.utcnow()
                }}
            )

            return {
                "success": True,
                "summary": summary_result.strip(),
                "keywords": keywords,
                "categories": categories
            }

        except Exception as e:
            logger.error(f"Error processing article metadata: {e}")
            return {"success": False, "error": str(e)}

    async def analyze_news_langchain(self, news_id: str) -> Dict[str, Any]:
        """LangChain을 사용하여 뉴스 기사를 분석합니다."""
        # Get news article (only HTML-parsed ones)
        news = news_collection.find_one({"_id": news_id, "is_basic_info": False})
        if not news:
            return {"success": False, "error": "Article not found"}

        try:
            # Extract title and content
            title = news["title"]
            content = news["content"]

            # LangChain 서비스를 통한 분석
            analysis_result = await self.langchain_service.analyze_news(title, content)

            # 결과가 올바르게 반환되었는지 확인
            if "error" in analysis_result:
                return {"success": False, "error": analysis_result["error"]}

            # 키워드와 주제 추출
            keywords = analysis_result.get("keywords", [])
            topics = analysis_result.get("topics", [])
            summary = analysis_result.get("summary", "")
            importance = analysis_result.get("importance", 5)

            # 문자열로 반환된 경우 리스트로 변환
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(',')]
            if isinstance(topics, str):
                topics = [t.strip() for t in topics.split(',')]

            # Update article in database
            news_collection.update_one(
                {"_id": news_id},
                {"$set": {
                    "summary": summary,
                    "keywords": keywords,
                    "topics": topics,
                    "categories": topics[:1] if topics else [],  # 첫 번째 주제를 카테고리로 사용
                    "importance": importance,
                    "updated_at": datetime.utcnow()
                }}
            )

            return {
                "success": True,
                "summary": summary,
                "keywords": keywords,
                "topics": topics,
                "importance": importance
            }

        except Exception as e:
            logger.error(f"Error analyzing news with LangChain: {e}")
            return {"success": False, "error": str(e)}

    async def search_news(self, query: NewsSearchQuery) -> List[NewsSummary]:
        """Search for news articles based on query"""
        try:
            # Get similar news articles using vector search
            similar_news = await self.search_similar_news(
                query.query,
                limit=query.limit
            )

            # Apply additional filters
            filtered_news = []
            for news in similar_news:
                # Filter by category
                if query.categories and news.get("categories"):
                    if not any(cat in query.categories for cat in news.get("categories", [])):
                        continue

                # Filter by source
                if query.sources and news.get("source"):
                    if news["source"] not in query.sources:
                        continue

                # Filter by date range
                if query.start_date and news.get("published_date"):
                    if news["published_date"] < query.start_date:
                        continue

                if query.end_date and news.get("published_date"):
                    if news["published_date"] > query.end_date:
                        continue

                # Filter by trust score
                if query.min_trust_score is not None and news.get("trust_score") is not None:
                    if news["trust_score"] < query.min_trust_score:
                        continue

                # Filter by sentiment
                if query.sentiment and news.get("sentiment_label"):
                    if news["sentiment_label"] != query.sentiment:
                        continue

                # Add to filtered results
                filtered_news.append(news)

            # Convert to NewsSummary objects
            result = []
            for news in filtered_news:
                # Get full news article to access all fields (only HTML-parsed ones)
                full_news = news_collection.find_one({"_id": news["id"], "is_basic_info": False})
                if full_news:
                    summary = NewsSummary(
                        id=full_news["_id"],
                        title=full_news["title"],
                        source=full_news["source"],
                        published_date=full_news["published_date"],
                        summary=full_news.get("summary"),
                        image_url=full_news.get("image_url"),
                        trust_score=full_news.get("trust_score"),
                        sentiment_score=full_news.get("sentiment_score"),
                        similarity_score=news.get("similarity_score"),
                        categories=full_news.get("categories", [])
                    )
                    result.append(summary)

            return result

        except Exception as e:
            logger.error(f"Error searching news: {e}")
            return []

    async def search_similar_news(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        임베딩 기반 유사 뉴스 검색 (embedding_service의 search_similar_news를 대체)
        """
        try:
            # 임베딩 서비스를 통한 검색
            embedding = await self.embedding_service.get_embedding(query)

            # 벡터 저장소에서 유사한 문서 검색
            results = await self.vector_store_service.search_by_vector(
                query_vector=embedding,
                limit=limit
            )

            # 결과 형식 변환
            similar_news = []
            for result in results:
                news_id = result["id"]
                news = news_collection.find_one({"_id": news_id, "is_basic_info": False})
                if news:
                    similar_news.append({
                        "id": news["_id"],
                        "title": news["title"],
                        "source": news["source"],
                        "published_date": news["published_date"],
                        "url": news.get("url", ""),
                        "trust_score": news.get("trust_score"),
                        "sentiment_score": news.get("sentiment_score"),
                        "similarity_score": result.get("similarity", 0.5)
                    })

            return similar_news

        except Exception as e:
            logger.error(f"Error in search_similar_news: {e}")

            # 기존 임베딩 서비스의 메서드 호출 (fallback)
            try:
                return self.embedding_service.search_similar_news(query, limit)
            except Exception as fallback_error:
                logger.error(f"Fallback search also failed: {fallback_error}")
                return []

    async def get_personalized_recommendations(self, user_id: str, limit: int = 10) -> List[NewsSummary]:
        """Get personalized news recommendations for a user based on interactions"""
        try:
            # Get user's recent interactions
            one_week_ago = datetime.utcnow() - timedelta(days=7)
            interactions = list(user_interactions_collection.find({
                "user_id": user_id,
                "timestamp": {"$gte": one_week_ago}
            }).sort("timestamp", -1).limit(20))

            if not interactions:
                # If no interactions, return trending news
                return await self.get_trending_news(limit)

            # Extract interacted news IDs
            interacted_news_ids = [i["news_id"] for i in interactions]

            # Get the articles the user interacted with
            interacted_news = list(news_collection.find({
                "_id": {"$in": interacted_news_ids}
            }))

            # Extract categories and keywords from interacted articles
            categories = []
            keywords = []
            for news in interacted_news:
                if "categories" in news:
                    categories.extend(news["categories"])
                if "keywords" in news:
                    keywords.extend(news["keywords"])

            # Count frequency and get top items
            category_counts = {}
            for cat in categories:
                category_counts[cat] = category_counts.get(cat, 0) + 1

            keyword_counts = {}
            for kw in keywords:
                keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

            # Get top categories and keywords
            top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            # Build query from user interests
            interest_query = " ".join([cat for cat, _ in top_categories] + [kw for kw, _ in top_keywords])

            # If we couldn't build a good query, use a default
            if not interest_query:
                interest_query = "latest news"

            # 벡터 검색으로 유사 뉴스 찾기
            similar_news = await self.search_similar_news(interest_query, limit=limit*2)

            # Filter out already interacted news
            recommendations = [n for n in similar_news if n["id"] not in interacted_news_ids][:limit]

            # 사용자 관심사와 검색 결과를 기반으로 LangChain 개인화 추천 요청
            try:
                langchain_recommendations = await self.langchain_service.get_recommendations(
                    interests=[cat for cat, _ in top_categories],
                    read_history=[news.get("title", "") for news in interacted_news[-5:]],  # 최근 5개 읽은 기사 제목
                    query=interest_query,
                    news_list=recommendations
                )

                # LangChain 추천 결과를 recommendations에 통합
                if isinstance(langchain_recommendations, dict) and not "error" in langchain_recommendations:
                    for i, news in enumerate(recommendations):
                        news_id = news["id"]
                        if news_id in langchain_recommendations:
                            rec_data = langchain_recommendations[news_id]
                            if isinstance(rec_data, dict):
                                recommendations[i]["relevance_score"] = rec_data.get("score", 5)
                                recommendations[i]["recommendation_reason"] = rec_data.get("reason", "")
            except Exception as lc_error:
                logger.error(f"LangChain 추천 중 오류 발생: {lc_error}")

            # Convert to NewsSummary objects
            result = []
            for news in recommendations:
                # Get full news article to access all fields (only HTML-parsed ones)
                full_news = news_collection.find_one({"_id": news["id"], "is_basic_info": False})
                if full_news:
                    summary = NewsSummary(
                        id=full_news["_id"],
                        title=full_news["title"],
                        source=full_news["source"],
                        published_date=full_news["published_date"],
                        summary=full_news.get("summary"),
                        image_url=full_news.get("image_url"),
                        trust_score=full_news.get("trust_score"),
                        sentiment_score=full_news.get("sentiment_score"),
                        similarity_score=news.get("similarity_score"),
                        categories=full_news.get("categories", [])
                    )
                    result.append(summary)

            return result

        except Exception as e:
            logger.error(f"Error getting personalized recommendations: {e}")
            return await self.get_trending_news(limit)

    async def get_trending_news(self, limit: int = 10) -> List[NewsSummary]:
        """Get trending news articles based on recency and interaction count"""
        try:
            # Get recent news with high interaction counts
            recent_news = list(news_collection.find().sort("published_date", -1).limit(100))

            if not recent_news or len(recent_news) == 0:
                logger.warning("트렌딩 뉴스: 최근 기사가 없습니다.")
                return []

            # Calculate trending score (recency + interaction count + trust score)
            trending_news = []
            for news in recent_news:
                try:
                    # Count interactions
                    interaction_count = user_interactions_collection.count_documents({
                        "news_id": str(news["_id"])
                    })

                    # Calculate days since publication
                    days_old = 0
                    if "published_date" in news:
                        delta = datetime.utcnow() - news["published_date"]
                        days_old = delta.days + (delta.seconds / 86400.0)  # Convert seconds to fractional days

                    # Calculate trending score
                    # More recent articles and more interactions = higher score
                    recency_factor = max(0, 7 - days_old) / 7  # 0-1 scale, 0 if older than 7 days
                    trust_factor = news.get("trust_score", 0.5)  # 0-1 scale

                    trending_score = (0.4 * recency_factor) + (0.4 * min(1, interaction_count / 10)) + (0.2 * trust_factor)

                    trending_news.append({
                        "news": news,
                        "trending_score": trending_score
                    })
                except Exception as item_error:
                    logger.error(f"뉴스 항목 처리 중 오류: {str(item_error)}")
                    continue

            if not trending_news or len(trending_news) == 0:
                logger.warning("트렌딩 뉴스: 처리된 기사가 없습니다.")
                return []

            # Sort by trending score and limit results
            trending_news.sort(key=lambda x: x["trending_score"], reverse=True)
            trending_news = trending_news[:limit]

            # Convert to NewsSummary objects
            result = []
            for item in trending_news:
                try:
                    news = item["news"]
                    summary = NewsSummary(
                        id=str(news["_id"]),
                        title=news["title"],
                        source=news["source"],
                        published_date=news["published_date"],
                        summary=news.get("summary", ""),
                        image_url=news.get("image_url", ""),
                        trust_score=news.get("trust_score", 0.5),
                        sentiment_score=news.get("sentiment_score", 0.0),
                        categories=news.get("categories", [])
                    )
                    result.append(summary)
                except Exception as convert_error:
                    logger.error(f"NewsSummary 변환 중 오류: {str(convert_error)}")
                    continue

            return result

        except Exception as e:
            logger.error(f"Error getting trending news: {e}")
            return []

    async def record_user_interaction(self, user_id: str, news_id: str, interaction_type: str, metadata: Dict[str, Any] = None) -> bool:
        """Record a user's interaction with a news article"""
        try:
            # Check if user exists, create if not
            user = user_collection.find_one({"_id": user_id})
            if not user:
                user_collection.insert_one({
                    "_id": user_id,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })

            # Check if news exists (only HTML-parsed ones)
            news = news_collection.find_one({"_id": news_id, "is_basic_info": False})
            if not news:
                return False

            # Record interaction
            interaction = {
                "user_id": user_id,
                "news_id": news_id,
                "interaction_type": interaction_type,  # click, read, like, share, etc.
                "timestamp": datetime.utcnow(),
                "metadata": metadata or {}
            }

            user_interactions_collection.insert_one(interaction)

            # Update user's last interaction time
            user_collection.update_one(
                {"_id": user_id},
                {"$set": {"updated_at": datetime.utcnow()}}
            )

            return True

        except Exception as e:
            logger.error(f"Error recording user interaction: {e}")
            return False

    async def ask_question_about_news(self, news_id: str, question: str) -> str:
        """
        기사에 대한 질문에 답변합니다.

        Args:
            news_id: 뉴스 ID
            question: 질문 내용

        Returns:
            답변 텍스트
        """
        try:
            # 뉴스 기사 가져오기 (HTML 파싱 완료된 뉴스만)
            news = news_collection.find_one({"_id": news_id, "is_basic_info": False})
            if not news:
                return "해당 기사를 찾을 수 없습니다."

            # LangChain 서비스를 사용하여 질문에 답변
            answer = await self.langchain_service.answer_question(
                title=news["title"],
                content=news["content"],
                question=question
            )

            return answer

        except Exception as e:
            logger.error(f"Error answering question about news: {e}")
            return f"죄송합니다. 질문에 답변하는 중 오류가 발생했습니다: {str(e)}"


# Helper function to initialize service
_recommendation_service = None

def get_recommendation_service() -> RecommendationService:
    """Get recommendation service instance"""
    global _recommendation_service
    if _recommendation_service is None:
        _recommendation_service = RecommendationService()
    return _recommendation_service
