import os
import logging
import uuid
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from app.core.config import settings
from app.db.mongodb import news_collection, user_collection, user_interactions_collection, get_mongodb_database
from bson.objectid import ObjectId
from app.models.news import NewsResponse, NewsSummary, NewsSearchQuery
from app.services.rss_crawler import run_crawler

# 서비스 가져오기
from app.services.embedding_service import get_embedding_service
from app.services.recommendation_service import get_recommendation_service
from app.services.user_analytics import get_user_analytics_service
from app.services.rag_service import get_rag_service
from app.services.collaborative_filtering import get_collaborative_filtering_service
from app.services.trust_analysis_service import get_trust_analysis_service
from app.services.sentiment_analysis_service import get_sentiment_analysis_service
from app.services.langchain_service import get_langchain_service
from app.services.vector_store_service import get_vector_store_service
from app.services.model_controller_service import get_model_controller_service
from app.services.scheduler import get_scheduler_service
from app.services.hybrid_recommendation import get_hybrid_recommendation_service
from app.services.system_prompt import get_system_prompt
from app.services.bert4rec_service import get_bert4rec_service

# 라우터 가져오기
from app.routers import news, users, admin, recommendation, auth, email_verification

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create data directory if it doesn't exist
os.makedirs(settings.DATA_DIR, exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 시작 로그
logger.info(f"서버 시작 중...")
logger.info(f"OpenAI API 키 설정됨: {'예' if settings.OPENAI_API_KEY else '아니오'}")
logger.info(f"데이터 디렉토리: {settings.DATA_DIR}")
logger.info(f"API 경로: {settings.API_V1_STR}")

# 몽고디비 연결 확인
try:
    # connection 확인
    from pymongo import MongoClient
    client = MongoClient(settings.MONGODB_URI)
    # ping 명령으로 연결 상태 확인
    client.admin.command('ping')
    logger.info(f"✅ MongoDB 연결 성공")
except Exception as e:
    logger.error(f"❌ MongoDB 연결 실패: {str(e)}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 오리진 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # 프론트엔드에 노출할 헤더
)

# Dependency to get embedding service
def get_embedding_service_dep():
    return get_embedding_service()

# Dependency to get recommendation service
def get_recommendation_service_dep():
    return get_recommendation_service()

# Dependency to get user analytics service
def get_user_analytics_service_dep():
    return get_user_analytics_service()

# Dependency to get RAG service
def get_rag_service_dep():
    return get_rag_service()

# Dependency to get collaborative filtering service
def get_collaborative_filtering_service_dep():
    return get_collaborative_filtering_service()

# Dependency to get trust analysis service
def get_trust_analysis_service_dep():
    return get_trust_analysis_service()

# Dependency to get sentiment analysis service
def get_sentiment_analysis_service_dep():
    return get_sentiment_analysis_service()

# Dependency to get LangChain service
def get_langchain_service_dep():
    return get_langchain_service()

# Dependency to get vector store service
def get_vector_store_service_dep():
    return get_vector_store_service()

# Dependency to get model controller service
def get_model_controller_service_dep():
    return get_model_controller_service()

# Dependency to get scheduler service
def get_scheduler_service_dep():
    return get_scheduler_service()

# Dependency to get hybrid recommendation service
def get_hybrid_recommendation_service_dep():
    return get_hybrid_recommendation_service()

# Dependency to get system prompt
def get_system_prompt_dep():
    return get_system_prompt()

# 라우터 등록
app.include_router(news.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(recommendation.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(email_verification.router, prefix="/api/v1")

# 애플리케이션 시작 시 이벤트 핸들러
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행되는 이벤트 핸들러"""
    logger.info("🚀 애플리케이션 시작 이벤트 실행")

    # 스케줄러 서비스 시작
    try:
        scheduler_service = get_scheduler_service()
        scheduler_service.start()
        logger.info("✅ 스케줄러 시작됨")
    except Exception as e:
        logger.error(f"❌ 스케줄러 시작 오류: {e}")

    # 초기 뉴스 크롤링 실행 (즉시 실행)
    try:
        # 직접 크롤러 실행
        article_count = run_crawler()
        logger.info(f"✅ 초기 뉴스 크롤링 완료: {article_count}개 기사 가져옴")

        # BERT4Rec 서비스로 콜드 스타트 추천 데이터 초기화
        try:
            bert4rec_service = get_bert4rec_service()
            bert4rec_service.initialize_cold_start_recommendations()
            logger.info("✅ 콜드 스타트 추천 데이터 초기화 완료")
        except Exception as rec_error:
            logger.error(f"❌ 콜드 스타트 추천 데이터 초기화 실패: {rec_error}")

        # API 엔드포인트 준비 완료 표시
        # 이렇게 하면 크롤링이 완료된 후에 API 엔드포인트가 응답하기 시작함
        logger.info("🔌 API 엔드포인트 준비 완료 - 클라이언트 요청 수신 가능")
    except Exception as e:
        logger.error(f"❌ 초기 뉴스 크롤링 실패: {e}")

# 연결 진단을 위한 엔드포인트
@app.get("/api/v1/diagnostics")
async def run_diagnostics():
    """시스템 연결 상태를 진단합니다."""
    results = {
        "mongodb": {"status": "unknown", "error": None},
        "openai_api": {"status": "unknown", "error": None},
        "embedding_service": {"status": "unknown", "error": None},
        "vector_store": {"status": "unknown", "error": None},
        "timestamp": datetime.utcnow().isoformat()
    }

    # MongoDB 연결 확인
    try:
        db = await get_mongodb_database()
        # 데이터베이스 ping 테스트
        await db.command("ping")
        # 컬렉션 확인
        collections = await db.list_collection_names()
        results["mongodb"]["status"] = "connected"
        results["mongodb"]["collections"] = collections
        results["mongodb"]["count"] = {
            "news": await db["news"].count_documents({}),
            "users": await db["users"].count_documents({})
        }
    except Exception as e:
        results["mongodb"]["status"] = "error"
        results["mongodb"]["error"] = str(e)
        logger.error(f"MongoDB 연결 오류: {str(e)}")

    # OpenAI API 연결 확인
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        # 간단한 API 호출로 연결 테스트
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input="테스트"
        )
        results["openai_api"]["status"] = "connected"
        results["openai_api"]["model"] = "text-embedding-3-small"
    except Exception as e:
        results["openai_api"]["status"] = "error"
        results["openai_api"]["error"] = str(e)
        logger.error(f"OpenAI API 연결 오류: {str(e)}")

    # 임베딩 서비스 확인
    try:
        embedding_service = get_embedding_service()
        test_embedding = await embedding_service.get_embedding("테스트")
        if test_embedding and len(test_embedding) > 0:
            results["embedding_service"]["status"] = "working"
            results["embedding_service"]["embedding_size"] = len(test_embedding)
        else:
            results["embedding_service"]["status"] = "error"
            results["embedding_service"]["error"] = "임베딩 생성 실패"
    except Exception as e:
        results["embedding_service"]["status"] = "error"
        results["embedding_service"]["error"] = str(e)
        logger.error(f"임베딩 서비스 오류: {str(e)}")

    # 벡터 저장소 확인
    try:
        import os
        vector_store_service = get_vector_store_service()
        chroma_path = os.path.join(settings.DATA_DIR, "chroma")
        faiss_path = os.path.join(settings.DATA_DIR, "faiss")

        results["vector_store"]["status"] = "partial"
        results["vector_store"]["paths"] = {
            "chroma_exists": os.path.exists(chroma_path),
            "chroma_path": chroma_path,
            "faiss_exists": os.path.exists(faiss_path),
            "faiss_path": faiss_path
        }

        if os.path.exists(chroma_path) and os.path.exists(faiss_path):
            results["vector_store"]["status"] = "ready"

    except Exception as e:
        results["vector_store"]["status"] = "error"
        results["vector_store"]["error"] = str(e)
        logger.error(f"벡터 저장소 확인 오류: {str(e)}")

    # 전체 시스템 상태 판단
    all_ok = all(results[component]["status"] in ["connected", "working", "ready"]
                 for component in ["mongodb", "openai_api", "embedding_service", "vector_store"])

    if all_ok:
        results["overall_status"] = "ok"
    elif results["mongodb"]["status"] != "connected":
        results["overall_status"] = "critical"
    else:
        results["overall_status"] = "degraded"

    return results

# 수동 크롤러 실행 엔드포인트
@app.post("/api/v1/admin/run-crawler")
async def manual_run_crawler():
    """RSS 크롤러를 수동으로 실행합니다."""
    try:
        article_count = run_crawler()
        return {"success": True, "message": f"크롤러 실행 성공: {article_count}개 기사 수집됨"}
    except Exception as e:
        logger.error(f"❌ 수동 크롤러 실행 오류: {e}")
        return {"success": False, "error": str(e)}

@app.get("/")
def read_root():
    return {"message": "Welcome to AI News Recommendation System"}


@app.get("/api/v1/health")
async def health_check():
    # 데이터베이스 연결 확인
    db_status = "ok"
    mongodb_error = None
    try:
        # DB 연결 테스트
        db = await get_mongodb_database()
        await db.command("ping")
    except Exception as e:
        db_status = "error"
        mongodb_error = str(e)

    # OpenAI API 키 확인
    openai_api_status = "ok" if settings.OPENAI_API_KEY else "not_configured"

    # 자세한 상태 반환
    return {
        "status": "ok" if db_status == "ok" and openai_api_status == "ok" else "degraded",
        "components": {
            "api": "ok",
            "database": db_status,
            "database_error": mongodb_error,
            "openai_api": openai_api_status
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/crawl")
async def crawl_news(background_tasks: BackgroundTasks):
    """Crawl news from RSS feeds"""
    background_tasks.add_task(run_crawler)
    return {"message": "News crawling started in background"}


@app.get("/api/v1/news", response_model=List[NewsResponse])
async def get_news(
    background_tasks: BackgroundTasks,
    skip: int = 0,
    limit: int = 10,
    source: Optional[str] = None,
    category: Optional[str] = None
):
    """Get list of news articles"""
    logger.info(f"뉴스 목록 요청: limit={limit}, category={category}, source={source}")

    try:
        query = {}
        if source:
            query["source"] = source

        # 카테고리 필터링 로직 수정 - 카테고리 배열에 포함된 항목 검색
        if category:
            query["categories"] = {"$in": [category]}  # 배열 내에 카테고리가 포함된 항목 검색
            logger.info(f"카테고리 필터링: {category}, 쿼리: {query}")

        # 데이터베이스 상태 확인
        total_news_count = news_collection.count_documents({})
        logger.info(f"전체 뉴스 수: {total_news_count}개")

        # 쿼리에 해당하는 뉴스 개수 확인
        filtered_count = news_collection.count_documents(query)
        logger.info(f"필터링된 뉴스 수: {filtered_count}개")

        # 뉴스 가져오기 - 최신순으로 정렬
        news = list(news_collection.find(query).skip(skip).limit(limit).sort("published_date", -1))
        logger.info(f"뉴스 쿼리 결과: {len(news)}개 항목")

        # 결과가 없는 경우
        if not news:
            logger.warning(f"일치하는 뉴스가 없습니다. 쿼리: {query}")
            # 뉴스 데이터가 없으면 크롤러 실행
            if total_news_count == 0:
                logger.info("뉴스 데이터가 없습니다. 크롤러를 자동으로 실행합니다.")
                background_tasks.add_task(run_crawler)

        result = []
        for item in news:
            # 필수 필드에 기본값 할당 (유효성 검사 오류 방지)
            if "image_url" not in item or not item.get("image_url"):
                item["image_url"] = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAZAAAADICAMAAAD2ShmzAAAAM1BMVEX////CwsL5+fnV1dXq6ur19fXg4OC8vLzT09Pt7e3Hx8fv7+/d3d3h4eHQ0NCwsLD///+ck8V3AAAACXBIWXMAAAsTAAALEwEAmpwYAAAD90lEQVR4nO3di5KjIBCFYQREvEDf/2UX0E2ceGlAiQy6/1fTtZVJ1SQndjtBr7IcZ7TqfnAZHhODu1cP/92V0tpqEz6BePgzcb/+Qb01hSK9VQeQKU6e0iJ6VXpRfFcfoAlbRZoiCCKEAEIIIIQAQggghABCCCCEAEIIBYUwU0kGsZoG8k4yiNPf1f9bvWQQ70zpSnnBILZcnhTLBbGutBDLfXbFBmF/CJQMwiXtsiDcrLJXJYNYZkpCsQghgBACCCGAEAIIIYAQQgEhk9UVMGhMMVQ3qGsZbZ+HGqY53jJp90Nouo2HUL2O/6pqpjmGQx6R9PlbY8+GUJ0+GTTHJdIhVGfOhFCdP7OT6qYTi6NvRULcR3UkBnVbXOUexFd2LkTVdjnRV3ZqIGbLXnp2Jb5T8dwcPrM5F8It/Ft48yrR3HbVHQ+hvlqfFwihL5cA4SCr1J0B8UWnPTKhvtfAu9ZQCB2sU85rCcyH0Nl65GQIXaj+T4doCtL4jAL3hWzpkahZXLsxO2tRFoIyIKV6ZDaEZmwDQlUHQVyhQkNo3g4gtPCDNkdVIJdDXJt0Y5xXcmMOyjXIpZNIGj3mZQgVPd4IQttaCqG1zfI1EFoNGc6HUNnD8URIYJ8QYzAiFMStzZGlENrYvhLSl2t20qUQYm1hq+wVh0Jo4UgIre6PQ6jocYi+XGXXJZdBaN2i4iFUdkVSPy7axrIglHdZXz/OwpW3UrMg3aYP+6HdTjdX8g/SPU6hgx32P4imbKF0z0txA+bZ0e3FNuX3LtfucWhbkofVU+DhXPe4FN4vQcfz2e4JH1DQ5zt8KftFuSDgk6Ou/AxoG/HZ7Mu1ouD5N2f/rLYxe1DGCDxj6ux7yjdC5P1S4Dlt5y2TvTIQRzV7XuDZiVcfUCJ4q8qXy2EJ3yrK5aA7e6/MhfAfQxcAoYc4UWflw0BFNKcdJPjZJQgBhBBACAGEEEAIAYQQQAgBhBBACAGEEEAIAYQQQAgBhBBACAGEEEAIAYQQQAgBhBBACAGEEEAIAYQQQAgBhBAWA8K9MlwI9ynhXqQsCOcXEWw3JQvCPRdcFMkgzEfJZZEMwv1g+EqJZBDuUcN+jgWDcL8h7rkkGYR7V3FPMO5lxEUSCXGPRuoNx0USCfd65d6zDIj+Moj+Moj+Moj+Moj+Moj++vMQ8tRCf/1lEP31l0H0FzV7YV9sMQ1Wf1Gz4QDC3XaYF1tUfGISrT91EUQI/WUQ/WUQ/WUQ/WUQ/UXNIJjfGYR5xUa0+NQZ1g8lzSCkGQT7uZ14Nd8QJt5fJIjDiqIAAAAASUVORK5CYII="

            if "categories" not in item or not item.get("categories"):
                item["categories"] = ["인공지능"]

            if "summary" not in item or not item.get("summary"):
                item["summary"] = item.get("title", "")[:100]

            if "content" not in item or not item.get("content"):
                item["content"] = item.get("title", "") + " (자세한 내용은 원문을 참조하세요.)"

            result.append(NewsResponse(
                id=item["_id"],
                title=item["title"],
                content=item.get("content", ""),
                url=item["url"],
                source=item["source"],
                published_date=item["published_date"],
                author=item.get("author", ""),
                image_url=item.get("image_url"),
                summary=item.get("summary"),
                categories=item.get("categories", ["인공지능"]),
                keywords=item.get("keywords", []),
                created_at=item["created_at"],
                updated_at=item["updated_at"],
                trust_score=item.get("trust_score", 0.5),
                sentiment_score=item.get("sentiment_score", 0),
                metadata=item.get("metadata", {})
            ))

        logger.info(f"뉴스 응답: {len(result)}개 항목")
        return result
    except Exception as e:
        logger.error(f"뉴스 목록 처리 중 오류: {str(e)}")
        return []


@app.get("/api/v1/news/{news_id}", response_model=NewsResponse)
async def get_news_by_id(news_id: str):
    """Get a news article by ID"""
    # 먼저 문자열 ID로 시도
    news = news_collection.find_one({"_id": news_id})

    # 결과가 없으면 ObjectId로 시도
    if not news:
        try:
            obj_id = ObjectId(news_id)
            news = news_collection.find_one({"_id": obj_id})
        except:
            # ID가 문자열인데 MongoDB에는 ObjectId로 저장된 경우
            # 또는 그 반대의 경우를 처리
            news = news_collection.find_one({"id": news_id})

    # 여전히 결과가 없으면 에러
    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    # 누락된 필드 처리
    if "image_url" not in news or not news.get("image_url"):
        news["image_url"] = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAZAAAADICAMAAAD2ShmzAAAAM1BMVEX////CwsL5+fnV1dXq6ur19fXg4OC8vLzT09Pt7e3Hx8fv7+/d3d3h4eHQ0NCwsLD///+ck8V3AAAACXBIWXMAAAsTAAALEwEAmpwYAAAD90lEQVR4nO3di5KjIBCFYQREvEDf/2UX0E2ceGlAiQy6/1fTtZVJ1SQndjtBr7IcZ7TqfnAZHhODu1cP/92V0tpqEz6BePgzcb/+Qb01hSK9VQeQKU6e0iJ6VXpRfFcfoAlbRZoiCCKEAEIIIIQAQggghABCCCCEAEIIBYUwU0kGsZoG8k4yiNPf1f9bvWQQ70zpSnnBILZcnhTLBbGutBDLfXbFBmF/CJQMwiXtsiDcrLJXJYNYZkpCsQghgBACCCGAEAIIIYAQQgEhk9UVMGhMMVQ3qGsZbZ+HGqY53jJp90Nouo2HUL2O/6pqpjmGQx6R9PlbY8+GUJ0+GTTHJdIhVGfOhFCdP7OT6qYTi6NvRULcR3UkBnVbXOUexFd2LkTVdjnRV3ZqIGbLXnp2Jb5T8dwcPrM5F8It/Ft48yrR3HbVHQ+hvlqfFwihL5cA4SCr1J0B8UWnPTKhvtfAu9ZQCB2sU85rCcyH0Nl65GQIXaj+T4doCtL4jAL3hWzpkahZXLsxO2tRFoIyIKV6ZDaEZmwDQlUHQVyhQkNo3g4gtPCDNkdVIJdDXJt0Y5xXcmMOyjXIpZNIGj3mZQgVPd4IQttaCqG1zfI1EFoNGc6HUNnD8URIYJ8QYzAiFMStzZGlENrYvhLSl2t20qUQYm1hq+wVh0Jo4UgIre6PQ6jocYi+XGXXJZdBaN2i4iFUdkVSPy7axrIglHdZXz/OwpW3UrMg3aYP+6HdTjdX8g/SPU6hgx32P4imbKF0z0txA+bZ0e3FNuX3LtfucWhbkofVU+DhXPe4FN4vQcfz2e4JH1DQ5zt8KftFuSDgk6Ou/AxoG/HZ7Mu1ouD5N2f/rLYxe1DGCDxj6ux7yjdC5P1S4Dlt5y2TvTIQRzV7XuDZiVcfUCJ4q8qXy2EJ3yrK5aA7e6/MhfAfQxcAoYc4UWflw0BFNKcdJPjZJQgBhBBACAGEEEAIAYQQQAgBhBBACAGEEEAIAYQQQAgBhBBACAGEEEAIAYQQQAgBhBBACAGEEEAIAYQQQAgBhBAWA8K9MlwI9ynhXqQsCOcXEWw3JQvCPRdcFMkgzEfJZZEMwv1g+EqJZBDuUcN+jgWDcL8h7rkkGYR7V3FPMO5lxEUSCXGPRuoNx0USCfd65d6zDIj+Moj+Moj+Moj+Moj+Moj++vMQ8tRCf/1lEP31l0H0FzV7YV9sMQ1Wf1Gz4QDC3XaYF1tUfGISrT91EUQI/WUQ/WUQ/WUQ/WUQ/UXNIJjfGYR5xUa0+NQZ1g8lzSCkGQT7uZ14Nd8QJt5fJIjDiqIAAAAASUVORK5CYII="

    return NewsResponse(
        id=news["_id"],
        title=news["title"],
        content=news["content"],
        url=news["url"],
        source=news["source"],
        published_date=news["published_date"],
        author=news.get("author"),
        image_url=news.get("image_url"),
        summary=news.get("summary"),
        categories=news.get("categories", []),
        keywords=news.get("keywords", []),
        created_at=news["created_at"],
        updated_at=news["updated_at"],
        trust_score=news.get("trust_score"),
        sentiment_score=news.get("sentiment_score"),
        metadata=news.get("metadata", {})
    )


@app.post("/api/v1/news/search", response_model=List[NewsSummary])
async def search_news(
    query: NewsSearchQuery,
    recommendation_service: Any = Depends(get_recommendation_service_dep)
):
    """Search for news articles"""
    results = await recommendation_service.search_news(query)
    return results


@app.get("/api/v1/news/trending", response_model=List[NewsSummary])
async def get_trending_news(
    limit: int = 10,
    recommendation_service: Any = Depends(get_recommendation_service_dep)
):
    """Get trending news articles"""
    logger.info(f"트렌딩 뉴스 요청: limit={limit}")
    try:
        # 기본 뉴스라도 있는지 확인
        total_news_count = news_collection.count_documents({})
        if total_news_count == 0:
            logger.warning("뉴스 데이터가 없습니다. 빈 목록 반환")
            return []

        trending = await recommendation_service.get_trending_news(limit)

        # 추천 결과가 없는 경우 최신 뉴스로 대체
        if not trending or len(trending) == 0:
            logger.info("트렌딩 뉴스가 없습니다. 최신 뉴스로 대체합니다.")
            recent_news = list(news_collection.find().sort("published_date", -1).limit(limit))
            trending = []

            for news in recent_news:
                summary = NewsSummary(
                    id=str(news["_id"]),
                    title=news["title"],
                    source=news["source"],
                    published_date=news["published_date"],
                    summary=news.get("summary", ""),
                    image_url=news.get("image_url", ""),
                    trust_score=news.get("trust_score", 0.5),
                    sentiment_score=news.get("sentiment_score", 0),
                    categories=news.get("categories", [])
                )
                trending.append(summary)

        logger.info(f"트렌딩 뉴스 응답: {len(trending)}개 항목")
        return trending
    except Exception as e:
        logger.error(f"트렌딩 뉴스 처리 중 오류: {str(e)}")
        # 오류 발생 시 빈 목록 반환
        return []


# 이 엔드포인트는 recommendation 라우터로 이동했습니다.
# 이전 코드와의 호환성을 위해 유지합니다.
@app.get("/api/v1/recommendations/{user_id}", response_model=List[NewsSummary])
async def get_recommendations(
    user_id: str,
    limit: int = 10,
    recommendation_service: Any = Depends(get_recommendation_service_dep)
):
    """Get personalized recommendations for a user"""
    # 라우터로 이동한 동일한 로직 사용
    recommendations = await recommendation_service.get_personalized_recommendations(user_id, limit)
    return recommendations

# 하이브리드 추천 엔드포인트
@app.get("/api/v1/hybrid-recommendations/{user_id}", response_model=List[NewsSummary])
async def get_hybrid_recommendations(
    user_id: str,
    limit: int = 10,
    hybrid_recommendation_service: Any = Depends(get_hybrid_recommendation_service_dep)
):
    """Get hybrid recommendations for a user (content + collaborative)"""
    # 하이브리드 추천 요청을 처리합니다
    recommendations = await hybrid_recommendation_service.get_personalized_recommendations(user_id, limit)
    return recommendations

@app.post("/api/v1/interaction")
async def record_interaction(
    user_id: str,
    news_id: str,
    interaction_type: str,
    metadata: Optional[Dict[str, Any]] = None,
    recommendation_service: Any = Depends(get_recommendation_service_dep)
):
    """Record a user interaction with a news article"""
    success = await recommendation_service.record_user_interaction(
        user_id,
        news_id,
        interaction_type,
        metadata
    )

    if not success:
        raise HTTPException(status_code=404, detail="Failed to record interaction")

    return {"message": "Interaction recorded successfully"}


@app.post("/api/v1/interactions/detail")
async def record_detailed_interaction(
    user_id: str,
    news_id: str,
    interaction_type: str,
    dwell_time_seconds: Optional[int] = None,
    scroll_depth_percent: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Record a detailed user interaction with a news article"""
    news = news_collection.find_one({"_id": news_id})
    if not news:
        raise HTTPException(status_code=404, detail="News article not found")

    interaction_data = {
        "user_id": user_id,
        "news_id": news_id,
        "interaction_type": interaction_type,
        "timestamp": datetime.utcnow(),
        "metadata": metadata or {}
    }

    if dwell_time_seconds is not None:
        interaction_data["metadata"]["dwell_time_seconds"] = dwell_time_seconds

    if scroll_depth_percent is not None:
        interaction_data["metadata"]["scroll_depth_percent"] = scroll_depth_percent

    interaction_score = 1.0  # Default score

    if interaction_type == "view":
        interaction_score = 0.5
    elif interaction_type == "click":
        interaction_score = 1.0
    elif interaction_type == "read":
        interaction_score = 2.0
    elif interaction_type == "like":
        interaction_score = 3.0
    elif interaction_type == "share":
        interaction_score = 4.0

    if dwell_time_seconds:
        if dwell_time_seconds > 300:
            interaction_score *= 2.0
        elif dwell_time_seconds > 120:
            interaction_score *= 1.5
        elif dwell_time_seconds > 60:
            interaction_score *= 1.2

    if scroll_depth_percent:
        if scroll_depth_percent > 80:
            interaction_score *= 1.5
        elif scroll_depth_percent > 50:
            interaction_score *= 1.2

    interaction_data["interaction_score"] = interaction_score

    user_interactions_collection.insert_one(interaction_data)

    return {"message": "Interaction recorded successfully"}


@app.post("/api/v1/process/{news_id}")
async def process_news(
    news_id: str,
    background_tasks: BackgroundTasks,
    embedding_service: Any = Depends(get_embedding_service_dep)
):
    """Process a news article (create embeddings, trust analysis, sentiment analysis)"""
    news = news_collection.find_one({"_id": news_id})
    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    background_tasks.add_task(embedding_service.process_news_pipeline, news_id)

    return {"message": f"Processing started for news ID: {news_id}"}


@app.post("/api/v1/metadata/{news_id}")
async def process_metadata(
    news_id: str,
    recommendation_service: Any = Depends(get_recommendation_service_dep)
):
    """Process and enrich article metadata"""
    news = news_collection.find_one({"_id": news_id})
    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    result = await recommendation_service.process_article_metadata(news_id)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to process metadata"))

    return result


# 협업 필터링 추천 엔드포인트
@app.get("/api/v1/collaborative/recommendations/{user_id}")
async def get_collaborative_recommendations(
    user_id: str,
    limit: int = 10,
    user_analytics_service: Any = Depends(get_user_analytics_service_dep)
):
    """Get collaborative filtering-based recommendations for a user"""
    # 협업 필터링 기반 추천 요청
    news_ids = user_analytics_service.get_collaborative_filtering_recommendations(user_id, limit)

    results = []
    for news_id in news_ids:
        news = news_collection.find_one({"_id": news_id})
        if news:
            results.append(NewsSummary(
                id=news["_id"],
                title=news["title"],
                source=news["source"],
                published_date=news["published_date"],
                summary=news.get("summary"),
                image_url=news.get("image_url"),
                trust_score=news.get("trust_score"),
                sentiment_score=news.get("sentiment_score"),
                categories=news.get("categories", [])
            ))

    return results


@app.get("/api/v1/users/stats/{user_id}")
async def get_user_stats(
    user_id: str,
    days: int = 30,
    user_analytics_service: Any = Depends(get_user_analytics_service_dep)
):
    """Get statistics about a user's interactions"""
    stats = user_analytics_service.get_user_interaction_stats(user_id, days)
    return stats


@app.get("/api/v1/users/engagement/{user_id}")
async def get_user_engagement(
    user_id: str,
    days: int = 30,
    user_analytics_service: Any = Depends(get_user_analytics_service_dep)
):
    """Get engagement score for a user"""
    score = user_analytics_service.get_user_engagement_score(user_id, days)
    return {"user_id": user_id, "engagement_score": score}


@app.get("/api/v1/users/preferences/{user_id}")
async def get_user_preferences(
    user_id: str,
    days: int = 90,
    user_analytics_service: Any = Depends(get_user_analytics_service_dep)
):
    """Get category preferences for a user"""
    preferences = user_analytics_service.get_user_category_preferences(user_id, days)
    return {"user_id": user_id, "category_preferences": preferences}


@app.get("/api/v1/users/similar/{user_id}")
async def get_similar_users(
    user_id: str,
    limit: int = 5,
    user_analytics_service: Any = Depends(get_user_analytics_service_dep)
):
    """Get similar users for a user"""
    similar_users = user_analytics_service.get_similar_users(user_id, limit)
    return {"user_id": user_id, "similar_users": similar_users}


# collaborative-filtering 추천 API
@app.get("/api/v1/collaborative-filtering/recommendations/{user_id}")
async def get_cf_recommendations(
    user_id: str,
    limit: int = 10,
    cf_service: Any = Depends(get_collaborative_filtering_service_dep)
):
    """Get collaborative filtering recommendations for a user"""
    # 협업 필터링 서비스를 통한 추천
    recommended_news_ids = cf_service.get_recommendations_for_user(user_id, limit)

    results = []
    for news_id in recommended_news_ids:
        news = news_collection.find_one({"_id": news_id})
        if news:
            results.append(NewsSummary(
                id=news["_id"],
                title=news["title"],
                source=news["source"],
                published_date=news["published_date"],
                summary=news.get("summary"),
                image_url=news.get("image_url"),
                trust_score=news.get("trust_score"),
                sentiment_score=news.get("sentiment_score"),
                categories=news.get("categories", [])
            ))

    return results


# RSS 피드 가져오기 API - 실시간 데이터
@app.get("/api/v1/rss/feeds")
async def get_rss_feeds(
    category: str = None,
    limit: int = 20
):
    """실제 RSS 피드에서 실시간으로 최신 뉴스 가져오기"""
    try:
        # 실시간 RSS 피드 크롤링을 위한 인스턴스 생성
        rss_crawler = RSSCrawler()

        # 실제 RSS 피드에서 최신 데이터 가져오기 (캐시 없음 - 항상 최신 데이터)
        articles = rss_crawler.fetch_rss_feeds()

        # LangChain 서비스를 통한 뉴스 AI 업스케일링
        langchain_service = get_langchain_service()

        # 결과를 News 객체 포맷으로 변환
        news_articles = []
        for article in articles:
            # 카테고리 필터링 (있는 경우)
            if category and not any(category.lower() in c.lower() for c in article.get("categories", [])):
                continue

            # News 객체로 변환
            news_id = article.get("id", str(uuid.uuid4()))
            title = article.get("title", "")
            content = article.get("content", "")
            original_summary = article.get("summary", "")

            # AI 업스케일링 - 콘텐츠가 충분히 있는 경우만 처리
            ai_enhanced = False
            ai_summary = ""
            ai_keywords = []
            trust_score = 0.5  # 기본값
            sentiment_score = 0  # 기본값

            # 콘텐츠 길이가 충분한 경우만 AI 처리
            if len(content) > 300 or len(original_summary) > 100:
                try:
                    # AI 요약 생성
                    ai_result = await langchain_service.analyze_news(title, content if len(content) > 100 else original_summary)

                    if not "error" in ai_result:
                        # AI 요약 적용
                        ai_summary = ai_result.get("summary", "")
                        ai_keywords = ai_result.get("keywords", [])
                        ai_enhanced = True

                        # 신뢰도 및 감정 분석 추가
                        if "importance" in ai_result:
                            trust_score = min(1.0, float(ai_result["importance"]) / 10.0)

                    logger.info(f"AI 요약 생성 성공: {news_id}")
                except Exception as e:
                    logger.error(f"AI 요약 생성 실패: {str(e)}")

            # 최종 뉴스 객체 구성
            news = {
                "_id": news_id,
                "title": title,
                "content": content,
                "summary": ai_summary if ai_enhanced and ai_summary else original_summary,
                "url": article.get("link", ""),
                "source": article.get("source", ""),
                "published_date": article.get("published_date", datetime.utcnow()),
                "author": article.get("author", ""),
                "image_url": article.get("image_url", ""),
                "categories": article.get("categories", []),
                "keywords": ai_keywords if ai_enhanced and ai_keywords else article.get("keywords", []),
                "ai_enhanced": ai_enhanced,
                "trust_score": trust_score,
                "sentiment_score": sentiment_score
            }
            news_articles.append(news)

            # 개수 제한
            if len(news_articles) >= limit:
                break

        # 가장 최근 기사 우선 정렬
        news_articles.sort(key=lambda x: x["published_date"], reverse=True)

        return news_articles[:limit]
    except Exception as e:
        logger.error(f"RSS 피드 가져오기 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RSS 피드 가져오기 실패: {str(e)}")


@app.get("/api/v1/collaborative-filtering/similar-users/{user_id}")
async def get_cf_similar_users(
    user_id: str,
    limit: int = 5,
    cf_service: Any = Depends(get_collaborative_filtering_service_dep)
):
    """Get similar users based on collaborative filtering"""
    similar_users = cf_service.get_similar_users(user_id, limit)
    return {"user_id": user_id, "similar_users": similar_users}


@app.post("/api/v1/rag/index")
async def index_articles(
    background_tasks: BackgroundTasks,
    days: int = 7,
    rag_service: Any = Depends(get_rag_service_dep)
):
    """Index news articles in the vector store"""
    background_tasks.add_task(rag_service.index_news_articles, days)
    return {"message": "Indexing started in background"}


@app.get("/api/v1/rag/search")
async def search_with_rag(
    query: str,
    limit: int = 5,
    rag_service: Any = Depends(get_rag_service_dep)
):
    """Search for news articles with RAG"""
    try:
        results = rag_service.search_news_with_query(query, limit)

        # 결과 필드 유효성 검사 및 변환
        processed_results = []
        for result in results:
            # 기본 필드 확인
            if not result or not isinstance(result, dict):
                continue

            # image_url이 HttpUrl 형식인 경우 문자열로 변환
            if result.get("image_url") and not isinstance(result["image_url"], str):
                result["image_url"] = str(result["image_url"])

            # 필수 필드가 누락된 경우 기본값 설정
            if "id" not in result or not result["id"]:
                if "_id" in result:
                    result["id"] = str(result["_id"])
                else:
                    continue  # ID가 없으면 건너뜀

            if "title" not in result or not result["title"]:
                result["title"] = "제목 없음"

            if "summary" not in result or not result["summary"]:
                result["summary"] = result.get("title", "내용 없음")[:100]

            if "source" not in result or not result["source"]:
                result["source"] = "미확인 출처"

            # 유효한 결과만 추가
            processed_results.append(result)

        return processed_results
    except Exception as e:
        logger.error(f"RAG 검색 중 오류 발생: {str(e)}")
        # 오류 발생 시 빈 배열 반환
        return []
        return []


@app.post("/api/v1/rag/summarize/{news_id}")
async def generate_summary(
    news_id: str,
    max_length: int = Query(200, description="최대 요약 길이"),
    rag_service: Any = Depends(get_rag_service_dep)
):
    """Generate a summary for a news article using LLM"""
    try:
        # ObjectId로 변환 시도
        try:
            from bson.objectid import ObjectId
            news_id_obj = ObjectId(news_id)
            news = news_collection.find_one({"_id": news_id_obj})
        except:
            # 실패하면 문자열 ID로 시도
            news = news_collection.find_one({"_id": news_id})

        if not news:
            raise HTTPException(status_code=404, detail="News not found")

        # 이미 요약이 있는지 확인
        if "summary" in news and news["summary"] and len(news["summary"].strip()) > 10:
            logger.info(f"Using existing summary for news {news_id}")
            return {"news_id": news_id, "summary": news["summary"].strip()}

        # 새 요약 생성
        # generate_news_summary는 동기 함수이므로 이벤트 루프 차단을 피하기 위해
        # 백그라운드 태스크로 실행하는 것이 좋지만 지금은 단순화를 위해 직접 호출
        summary = rag_service.generate_news_summary(news_id)

        if not summary:
            # 요약 생성 실패 시 간단한 요약 생성
            title = news.get("title", "")
            content = news.get("content", "")
            # 컨텐츠가 너무 길면 앞부분만 사용
            if len(content) > 500:
                simple_summary = content[:500] + "..."
            else:
                simple_summary = content

            return {"news_id": news_id, "summary": simple_summary}

        # 요약 길이 제한
        if max_length and len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return {"news_id": news_id, "summary": summary}

    except Exception as e:
        logger.error(f"Error generating summary for news {news_id}: {e}")
        return {"news_id": news_id, "summary": "요약을 생성하는 중 오류가 발생했습니다."}


@app.post("/api/v1/rag/chat")
async def chat_with_news(
    user_id: str,
    query: str,
    rag_service: Any = Depends(get_rag_service_dep)
):
    """Chat with news articles using RAG"""
    result = rag_service.chat_with_news(user_id, query)
    return result


@app.post("/api/v1/rag/analyze-topic")
async def analyze_topic(
    topic: str,
    rag_service: Any = Depends(get_rag_service_dep)
):
    """Generate an analysis of a news topic using RAG"""
    result = rag_service.generate_topic_analysis(topic)
    return result


@app.post("/api/v1/rag/switch-vectorstore")
async def switch_vectorstore(
    store_type: str = "chroma",
    rag_service: Any = Depends(get_rag_service_dep)
):
    """Switch between Chroma and FAISS vector stores"""
    rag_service.switch_vectorstore(store_type)
    return {"message": f"Switched to {store_type} vectorstore"}


# 새로 추가된 API 엔드포인트 - 고급 자연어 처리 및 AI 기능

class QuestionRequest(BaseModel):
    question: str

class AnalyzeNewsRequest(BaseModel):
    title: str
    content: str

@app.post("/api/v1/news/{news_id}/ask", response_model=Dict[str, str])
async def ask_question_about_news(
    news_id: str,
    request: QuestionRequest,
    recommendation_service: Any = Depends(get_recommendation_service_dep)
):
    """뉴스 기사에 대한 질문에 답변합니다."""
    news = news_collection.find_one({"_id": news_id})
    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    answer = await recommendation_service.ask_question_about_news(news_id, request.question)
    return {"answer": answer}

@app.post("/api/v1/news/{news_id}/analyze-langchain")
async def analyze_news_with_langchain(
    news_id: str,
    recommendation_service: Any = Depends(get_recommendation_service_dep)
):
    """LangChain을 사용하여 뉴스 기사를 분석합니다."""
    result = await recommendation_service.analyze_news_langchain(news_id)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to analyze news"))

    return result

@app.post("/api/v1/analyze-news")
async def analyze_news_content(
    request: AnalyzeNewsRequest,
    langchain_service: Any = Depends(get_langchain_service_dep)
):
    """LangChain을 사용하여 제공된 뉴스 콘텐츠를 분석합니다."""
    result = await langchain_service.analyze_news(request.title, request.content)
    return result

@app.post("/api/v1/news/{news_id}/trust-analysis")
async def analyze_news_trustworthiness(
    news_id: str,
    embedding_service: Any = Depends(get_embedding_service_dep)
):
    """BiLSTM 모델을 사용하여 뉴스 기사의 신뢰도를 분석합니다."""
    try:
        # ObjectId로 변환 시도
        try:
            news_id_obj = ObjectId(news_id)
            news = news_collection.find_one({"_id": news_id_obj})
        except:
            # 실패하면 문자열 ID로 시도
            news = news_collection.find_one({"_id": news_id})

        if not news:
            raise HTTPException(status_code=404, detail="News not found")

        # 이미 신뢰도 점수가 있는지 확인
        if "trust_score" in news and news["trust_score"] is not None:
            # 이미 있다면 기존 점수 반환
            logger.info(f"Using existing trust score for news {news_id}: {news['trust_score']}")
            return {
                "news_id": news_id,
                "trust_score": news["trust_score"],
                "model": "cached_result"
            }

        # 신뢰도 분석 수행
        result = await embedding_service.perform_trust_analysis(news_id)

        if result:
            return {
                "news_id": news_id,
                "trust_score": result.trust_score,
                "model": result.model_name
            }
        else:
            # 결과가 없으면 기본값 반환
            logger.warning(f"No trust analysis result for news {news_id}, using default value")
            return {
                "news_id": news_id,
                "trust_score": 0.5,  # 기본 신뢰도 점수
                "model": "default_fallback"
            }
    except Exception as e:
        # 모든 예외 처리 - 500 오류 대신 기본값 반환
        logger.error(f"Error in trust analysis API: {e}")
        return {
            "news_id": news_id,
            "trust_score": 0.5,  # 기본 신뢰도 점수
            "model": "error_fallback"
        }

@app.post("/api/v1/news/{news_id}/sentiment-analysis")
async def analyze_news_sentiment(
    news_id: str,
    embedding_service: Any = Depends(get_embedding_service_dep)
):
    """BERT 모델을 사용하여 뉴스 기사의 감정을 분석합니다."""
    # ObjectId로 변환 시도
    try:
        news_id_obj = ObjectId(news_id)
        news = news_collection.find_one({"_id": news_id_obj})
    except:
        # 실패하면 문자열 ID로 시도
        news = news_collection.find_one({"_id": news_id})

    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    result = await embedding_service.perform_sentiment_analysis(news_id)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to perform sentiment analysis")

    return {
        "news_id": news_id,
        "sentiment_score": result.sentiment_score,
        "sentiment_label": result.sentiment_label,
        "model": result.model_name
    }

@app.get("/api/v1/news/cold-start", response_model=List[NewsSummary])
async def get_cold_start_recommendations(
    limit: int = 5,
    bert4rec_service = Depends(get_bert4rec_service)
):
    """사용자 데이터가 없는 상태에서 초기 추천을 제공합니다."""
    logger.info(f"콜드 스타트 추천 요청: limit={limit}")
    try:
        # BERT4Rec 서비스를 통해 콜드 스타트 추천 가져오기
        recommendations = bert4rec_service.get_cold_start_recommendations(limit=limit)

        if not recommendations or len(recommendations) == 0:
            logger.warning("콜드 스타트 추천이 없습니다. 최신 뉴스로 대체합니다.")
            recent_news = list(news_collection.find().sort("published_date", -1).limit(limit))
            recommendations = recent_news

        # 응답 포맷팅
        result = []
        for news in recommendations:
            summary = NewsSummary(
                id=str(news["_id"]),
                title=news["title"],
                source=news.get("source", "Unknown"),
                published_date=news.get("published_date", datetime.utcnow()),
                summary=news.get("summary", ""),
                image_url=news.get("image_url", ""),
                trust_score=news.get("trust_score", 0.5),
                sentiment_score=news.get("sentiment_score", 0),
                categories=news.get("categories", [])
            )
            result.append(summary)

        logger.info(f"콜드 스타트 추천 응답: {len(result)}개 항목")
        return result
    except Exception as e:
        logger.error(f"콜드 스타트 추천 처리 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting news: {str(e)}")

@app.post("/api/v1/text/embeddings")
async def generate_text_embeddings(
    text: str,
    embedding_service: Any = Depends(get_embedding_service_dep)
):
    """OpenAI 모델을 사용하여 텍스트의 임베딩을 생성합니다."""
    embedding = await embedding_service.get_embedding(text)
    return {
        "text": text[:100] + "..." if len(text) > 100 else text,
        "embedding_dimension": len(embedding),
        "embedding": embedding[:5] + ["..."] + embedding[-5:] if embedding else []  # 첫 5개와 마지막 5개 요소만 반환
    }

@app.get("/api/v1/models/status")
async def get_models_status(
    model_controller: Any = Depends(get_embedding_service_dep)
):
    """등록된 AI 모델의 상태를 가져옵니다."""
    return {
        "openai_embedding": {"status": "active", "type": "embedding"},
        "bilstm_trust": {"status": "active", "type": "trust_analysis"},
        "sentiment_bert": {"status": "active", "type": "sentiment_analysis"},
        "langchain_gpt": {"status": "active", "type": "text_generation"}
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
