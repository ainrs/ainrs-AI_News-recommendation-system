#!/usr/bin/env python3
import logging
import asyncio
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()

# MongoDB
from app.db.mongodb import news_collection, get_mongodb_database
from app.services.rss_crawler import RSSCrawler, run_crawler
from app.core.config import settings

async def test_mongodb_connection():
    """MongoDB 연결 테스트 및 컬렉션 확인"""
    logger.info("MongoDB 연결 테스트 중...")

    try:
        db = await get_mongodb_database()

        # ping 테스트
        result = await db.command("ping")
        if result:
            logger.info("✅ MongoDB 연결 성공!")

        # 컬렉션 확인
        collections = await db.list_collection_names()
        logger.info(f"컬렉션 목록: {collections}")

        # 뉴스 컬렉션 데이터 확인
        news_count = await db["news"].count_documents({})
        logger.info(f"'news' 컬렉션 문서 수: {news_count}")

        return True
    except Exception as e:
        logger.error(f"❌ MongoDB 연결 실패: {str(e)}")
        return False

def test_rss_crawler():
    """RSS 크롤러 테스트"""
    logger.info("RSS 크롤러 테스트 중...")

    try:
        # RSS 피드 목록 확인
        logger.info(f"등록된 RSS 피드: {settings.RSS_FEEDS}")

        # 크롤러 실행
        crawler = RSSCrawler()
        articles = crawler.fetch_rss_feeds()

        if not articles:
            logger.warning("❌ RSS 피드에서 뉴스 기사를 가져오지 못했습니다.")
            return False

        logger.info(f"✅ RSS 피드에서 {len(articles)}개의 기사를 가져왔습니다.")

        # 첫 번째 기사 내용 확인
        if articles:
            logger.info("첫 번째 기사 정보:")
            article = articles[0]
            logger.info(f"- 제목: {article['title']}")
            logger.info(f"- 출처: {article['source']}")
            logger.info(f"- URL: {article['url']}")
            logger.info(f"- 본문 길이: {len(article['content'])} 자")

        # 데이터베이스에 저장
        saved_count = crawler.save_articles_to_db(articles)
        logger.info(f"✅ {saved_count}개의 기사를 데이터베이스에 저장했습니다.")

        return True
    except Exception as e:
        logger.error(f"❌ RSS 크롤러 실행 중 오류 발생: {str(e)}")
        return False

async def test_openai_api():
    """OpenAI API 연결 테스트"""
    logger.info("OpenAI API 연결 테스트 중...")

    try:
        from app.services.embedding_service import get_embedding_service

        embedding_service = get_embedding_service()
        embedding = embedding_service.get_embedding("테스트 텍스트입니다. OpenAI API가 정상 작동하는지 확인합니다.")

        if embedding and len(embedding) > 0:
            logger.info(f"✅ OpenAI API 연결 성공! 임베딩 차원: {len(embedding)}")
            return True
        else:
            logger.error("❌ OpenAI API에서 임베딩을 생성하지 못했습니다.")
            return False
    except Exception as e:
        logger.error(f"❌ OpenAI API 연결 중 오류 발생: {str(e)}")
        return False

async def test_news_search():
    """뉴스 검색 기능 테스트"""
    logger.info("뉴스 검색 기능 테스트 중...")

    try:
        from app.services.embedding_service import get_embedding_service

        # MongoDB에서 뉴스 개수 확인
        db = await get_mongodb_database()
        news_count = await db["news"].count_documents({})

        if news_count == 0:
            logger.warning("❌ 데이터베이스에 뉴스가 없습니다. 검색 테스트를 건너뜁니다.")
            return False

        # 임베딩 서비스 초기화
        embedding_service = get_embedding_service()

        # 뉴스 검색
        query = "latest news"
        results = embedding_service.search_similar_news(query, limit=3)

        if not results:
            logger.warning("⚠️ 뉴스 검색 결과가 없습니다.")
            return False

        logger.info(f"✅ 검색 결과: {len(results)}개의 뉴스 기사 찾음")
        logger.info("검색 결과 샘플:")
        for i, result in enumerate(results[:3]):
            logger.info(f"{i+1}. {result['title']} (유사도: {result.get('similarity_score', 'N/A')})")

        return True
    except Exception as e:
        logger.error(f"❌ 뉴스 검색 테스트 중 오류 발생: {str(e)}")
        return False

async def main():
    """테스트 스크립트 진입점"""
    logger.info("====== RSS 크롤러 및 데이터베이스 테스트 시작 ======")

    # 단계 1: MongoDB 연결 테스트
    mongodb_ok = await test_mongodb_connection()

    if not mongodb_ok:
        logger.error("MongoDB 연결 실패. 테스트를 종료합니다.")
        return False

    # 단계 2: OpenAI API 테스트
    openai_ok = await test_openai_api()

    # 단계 3: RSS 크롤러 테스트
    rss_ok = test_rss_crawler()

    # 단계 4: 뉴스 검색 테스트
    search_ok = await test_news_search()

    # 결과 정리
    logger.info("\n====== 테스트 결과 요약 ======")
    logger.info(f"MongoDB 연결: {'✅ 성공' if mongodb_ok else '❌ 실패'}")
    logger.info(f"OpenAI API 연결: {'✅ 성공' if openai_ok else '❌ 실패'}")
    logger.info(f"RSS 크롤러: {'✅ 성공' if rss_ok else '❌ 실패'}")
    logger.info(f"뉴스 검색: {'✅ 성공' if search_ok else '❌ 실패'}")

    all_ok = mongodb_ok and openai_ok and rss_ok and search_ok
    logger.info(f"\n전체 테스트 결과: {'✅ 모든 테스트 통과' if all_ok else '❌ 일부 테스트 실패'}")

    # 서버 시작 가능 여부 안내
    if all_ok:
        logger.info("서버를 시작하여 프론트엔드와 연결할 수 있습니다.")
    else:
        if not mongodb_ok:
            logger.info("MongoDB 연결 문제를 해결해야 합니다. .env 파일의 MONGODB_URI 설정을 확인하세요.")
        if not openai_ok:
            logger.info("OpenAI API 연결 문제를 해결해야 합니다. .env 파일의 OPENAI_API_KEY 설정을 확인하세요.")
        if not rss_ok:
            logger.info("RSS 크롤러가 정상 작동하지 않습니다. 네트워크 연결과 RSS 피드 URL을 확인하세요.")

    return all_ok

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
