#!/usr/bin/env python3
import asyncio
import logging
import json
import sys
from datetime import datetime
from pprint import pprint

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()

# 필요한 패키지 확인
try:
    import html2text
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    logger.error("필요한 패키지가 없습니다. 'pip install -r requirements.txt'를 실행하여 설치하세요.")
    sys.exit(1)

# 서비스 임포트
from app.services.rss_crawler import RSSCrawler
from app.services.content_processor import get_content_processor
from app.core.config import settings

async def test_content_processor():
    """콘텐츠 프로세서 테스트"""
    logger.info("콘텐츠 프로세서 테스트 중...")

    # 콘텐츠 프로세서 초기화
    content_processor = get_content_processor()

    # 샘플 URL로 테스트
    test_urls = [
        "https://www.bbc.com/news/world-us-canada-68712975",  # BBC
        "https://edition.cnn.com/2023/04/21/politics/us-ukraine-munitions-russia-war/index.html",  # CNN
        "https://www.aljazeera.com/news/2023/4/21/us-house-passes-republican-bill-to-ban-transgender-athletes",  # Al Jazeera
    ]

    for url in test_urls:
        try:
            # URL 접속
            logger.info(f"URL 접속 중: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # 인코딩 처리
            response.encoding = response.apparent_encoding or 'utf-8'

            # HTML 콘텐츠 처리
            result = content_processor.enhance_article(response.text, url)

            # 결과 출력
            logger.info(f"✅ {url} 처리 완료")
            logger.info(f"- 요약: {result['summary'][:100]}...")
            logger.info(f"- 단어 수: {result['word_count']}")
            logger.info(f"- 이미지 수: {len(result['images'])}")

            # 첫 번째 이미지 URL 출력
            if result['images']:
                logger.info(f"- 첫 번째 이미지: {result['images'][0]['src']}")

        except Exception as e:
            logger.error(f"❌ {url} 처리 중 오류 발생: {e}")

    return True

async def test_rss_crawler():
    """RSS 크롤러 테스트"""
    logger.info("RSS 크롤러 테스트 중...")

    # RSS 크롤러 초기화
    crawler = RSSCrawler()

    # RSS 피드 목록 확인
    logger.info(f"RSS 피드 목록: {crawler.rss_feeds}")

    # 첫 번째 피드만 사용하여 테스트
    test_feed = crawler.rss_feeds[0] if crawler.rss_feeds else None
    if not test_feed:
        logger.error("테스트할 RSS 피드가 없습니다.")
        return False

    try:
        # RSS 피드 가져오기
        logger.info(f"테스트 피드: {test_feed}")
        feed = feedparser.parse(test_feed)

        if not feed.entries:
            logger.warning(f"피드에 항목이 없습니다: {test_feed}")
            return False

        # 첫 번째 항목만 처리
        source = urlparse(test_feed).netloc.replace('www.', '').replace('feeds.', '')
        entry = feed.entries[0]

        # 항목 처리
        logger.info(f"항목 처리 중: {entry.get('title', '제목 없음')}")
        article = crawler._process_entry(entry, source)

        if not article:
            logger.warning("항목 처리 실패")
            return False

        # 결과 출력
        logger.info(f"✅ 항목 처리 완료: {article['title']}")
        logger.info(f"- URL: {article['url']}")
        logger.info(f"- 출처: {article['source']}")
        logger.info(f"- 카테고리: {article.get('categories', [])}")
        logger.info(f"- 요약: {article.get('summary', '')[:100]}...")
        logger.info(f"- 이미지 URL: {article.get('image_url', 'N/A')}")
        logger.info(f"- 이미지 수: {len(article.get('images', []))}")

        # 본문 일부 출력
        content_preview = article['content'][:200] + '...' if article.get('content') else 'N/A'
        logger.info(f"- 본문 미리보기: {content_preview}")

        return True
    except Exception as e:
        logger.error(f"RSS 크롤러 테스트 중 오류 발생: {e}")
        return False

async def main():
    """테스트 실행"""
    logger.info("==== 향상된 RSS 크롤러 및 콘텐츠 프로세서 테스트 시작 ====")

    # 콘텐츠 프로세서 테스트
    content_processor_result = await test_content_processor()

    # RSS 크롤러 테스트
    crawler_result = await test_rss_crawler()

    # 결과 요약
    logger.info("\n==== 테스트 결과 ====")
    logger.info(f"콘텐츠 프로세서: {'성공' if content_processor_result else '실패'}")
    logger.info(f"RSS 크롤러: {'성공' if crawler_result else '실패'}")

    overall = content_processor_result and crawler_result
    logger.info(f"\n전체 테스트 결과: {'✅ 모든 테스트 통과' if overall else '❌ 일부 테스트 실패'}")

    return overall

if __name__ == "__main__":
    import feedparser  # 이 위치에서 임포트하여 전역 초기화되도록 함

    result = asyncio.run(main())
    sys.exit(0 if result else 1)
