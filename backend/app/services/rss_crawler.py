import os
import json
import hashlib
import logging
import requests
import feedparser
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

from app.core.config import settings
from app.db.mongodb import news_collection
from app.models.news import NewsCreate
from app.services.content_processor import get_content_processor
from app.services.langchain_service import get_langchain_service

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Make sure the data directory exists
os.makedirs(settings.DATA_DIR, exist_ok=True)


class RSSCrawler:
    """RSS Feed Crawler for collecting news articles"""

    def __init__(self, rss_feeds: List[str] = None):
        self.rss_feeds = rss_feeds or settings.RSS_FEEDS
        self.content_processor = get_content_processor()
        self.langchain_service = get_langchain_service()  # AI 요약 서비스

    def fetch_rss_feeds(self) -> List[Dict[str, Any]]:
        """Fetch all RSS feeds and extract articles"""
        all_entries = []

        logger.info(f"📡 시작: RSS 피드 {len(self.rss_feeds)}개 수집")

        for feed_url in self.rss_feeds:
            try:
                logger.info(f"📥 RSS 피드 가져오는 중: {feed_url}")
                feed = feedparser.parse(feed_url)

                if hasattr(feed, 'status') and feed.status != 200:
                    logger.error(f"⚠️ RSS 피드 상태 오류: {feed_url}, 상태: {feed.status}")
                    continue

                if not hasattr(feed, 'entries') or len(feed.entries) == 0:
                    logger.warning(f"⚠️ RSS 피드에 항목 없음: {feed_url}")
                    continue

                # Extract source from feed URL
                source = urlparse(feed_url).netloc.replace('www.', '').replace('feeds.', '')
                logger.info(f"✅ 피드 소스: {source}, 기사 수: {len(feed.entries)}개")

                # Process entries
                entry_count = 0
                for entry in feed.entries:
                    try:
                        article = self._process_entry(entry, source)
                        if article:
                            all_entries.append(article)
                            entry_count += 1
                    except Exception as e:
                        logger.error(f"❌ 항목 처리 오류 {entry.get('title', 'unknown')}: {e}")
                        continue

                logger.info(f"✅ 피드 {source}에서 {entry_count}개 기사 처리함")
            except Exception as e:
                logger.error(f"❌ 피드 가져오기 오류 {feed_url}: {e}")
                continue

        logger.info(f"📊 총 {len(all_entries)}개 기사 수집 완료")
        return all_entries

    def _process_entry(self, entry: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """Process a single RSS entry and extract article content with enhanced processing"""
        # Extract URL
        url = entry.get('link')
        if not url:
            return None

        # Check if article already exists in database
        existing = news_collection.find_one({"url": url})
        if existing:
            logger.debug(f"Article already exists in database: {url}")
            return None

        # Extract published date
        published_date = None
        if 'published_parsed' in entry:
            published_date = datetime(*entry.published_parsed[:6])
        elif 'updated_parsed' in entry:
            published_date = datetime(*entry.updated_parsed[:6])
        else:
            published_date = datetime.utcnow()

        # Extract title
        title = entry.get('title', '').strip()
        if not title:
            return None

        # Extract author
        author = None
        if 'author' in entry:
            author = entry.author

        # Extract categories/tags
        categories = []

        # 태그에서 카테고리 추출
        if 'tags' in entry:
            categories = [tag.term for tag in entry.tags if hasattr(tag, 'term')]

        # RSS 소스에 따른 자동 카테고리 지정
        source_categories = {
            'yna.co.kr': ['한국', '연합뉴스'],
            'news.kbs.co.kr': ['한국', 'KBS'],
            'ytn.co.kr': ['한국', 'YTN'],
            'hani.co.kr': ['한국', '한겨레'],
            'khan.co.kr': ['한국', '경향신문'],
            'chosun.com': ['한국', '조선일보'],
            'donga.com': ['한국', '동아일보'],
            'bbc.co.uk': ['해외', 'BBC', '영국'],
            'cnn.com': ['해외', 'CNN', '미국'],
            'nytimes.com': ['해외', 'NYT', '미국', 'New York Times'],
            'reuters.com': ['해외', 'Reuters', '국제'],
            'npr.org': ['해외', 'NPR', '미국'],
            'aljazeera.com': ['해외', 'Al Jazeera', '중동'],
            'theguardian.com': ['해외', 'The Guardian', '영국'],
            # IT/기술 뉴스 사이트 카테고리
            'zdnet.co.kr': ['IT', '기술', 'ZDNet'],
            'etnews.com': ['IT', '기술', '전자신문', '인공지능', '클라우드', '빅데이터'],
            'bloter.net': ['IT', '기술', '블로터', '인공지능', '스타트업'],
            'venturesquare.net': ['스타트업', '투자', '벤처'],
            'hada.io': ['IT', '기술', '스타트업'],
            'platum.kr': ['스타트업', '투자', '서비스'],
            'thevc.kr': ['스타트업', '투자', 'VC'],
            'itworld.co.kr': ['IT', '기술', '인공지능', '클라우드', '빅데이터'],
            'aitimes.com': ['인공지능', 'AI', '머신러닝'],
            'itfind.or.kr': ['IT', '기술', '산업', 'R&D'],
            'verticalplatform.kr': ['IT', '기술', '인공지능', 'AI-서비스'],
        }

        # URL에 포함된 도메인에 따라 카테고리 추가
        for domain, cats in source_categories.items():
            if domain in url:
                categories.extend(cats)

        # 중복 제거
        categories = list(set(categories))

        # Extract summary and content from entry - HTML 마크업 처리
        summary = ''
        content = ''

        # RSS 피드에서 콘텐츠 추출
        if 'content' in entry and entry.content:
            try:
                # content:encoded 태그 처리
                if isinstance(entry.content, list):
                    content_text = entry.content[0].value
                else:
                    content_text = entry.content

                # HTML 파싱하여 태그 정리
                soup = BeautifulSoup(content_text, 'html.parser')

                # 이미지 추출을 위해 저장
                images_from_content = soup.find_all('img')

                # 불필요한 요소 제거
                for tag in soup.find_all(['script', 'style', 'iframe', 'form']):
                    tag.decompose()

                # 콘텐츠 추출
                content = soup.get_text(separator=' ', strip=True)
            except Exception as e:
                logger.error(f"콘텐츠 처리 오류: {e}")
                if isinstance(entry.content, str):
                    content = entry.content

        # summary 처리
        if 'summary' in entry:
            try:
                soup = BeautifulSoup(entry.summary, 'html.parser')
                # 불필요한 요소 제거
                for tag in soup.find_all(['script', 'style', 'iframe', 'form']):
                    tag.decompose()
                summary = soup.get_text(separator=' ', strip=True)
            except Exception as e:
                logger.error(f"요약 처리 오류: {e}")
                summary = entry.summary

        # description 처리 (summary가 없는 경우)
        if not summary and 'description' in entry:
            try:
                soup = BeautifulSoup(entry.description, 'html.parser')
                for tag in soup.find_all(['script', 'style', 'iframe', 'form']):
                    tag.decompose()
                summary = soup.get_text(separator=' ', strip=True)
            except:
                summary = entry.description

        # 이미지 추출 개선 (다양한 소스에서 이미지 찾기)
        image_url = None
        images = []

        # 1. 콘텐츠에서 이미지 찾기 (위에서 추출한 이미지)
        if 'images_from_content' in locals() and images_from_content:
            for img in images_from_content[:3]:  # 최대 3개만 사용
                if img.get('src'):
                    img_url = img['src']
                    # 상대 경로를 절대 경로로 변환
                    if img_url.startswith('/'):
                        parsed_url = urlparse(url)
                        img_url = f"{parsed_url.scheme}://{parsed_url.netloc}{img_url}"

                    if not image_url:  # 첫 번째 이미지를 대표 이미지로 사용
                        image_url = img_url

                    images.append({
                        'src': img_url,
                        'alt': img.get('alt', title)
                    })

        # 2. media_content 확인 (일부 RSS 피드에서 사용)
        if not image_url and 'media_content' in entry:
            media = entry.get('media_content', [])
            if isinstance(media, list) and media and isinstance(media[0], dict) and 'url' in media[0]:
                image_url = media[0]['url']
                images.append({
                    'src': image_url,
                    'alt': title
                })
            elif isinstance(media, dict) and 'url' in media:
                image_url = media['url']
                images.append({
                    'src': image_url,
                    'alt': title
                })

        # 3. media:thumbnail 확인
        if not image_url and hasattr(entry, 'media_thumbnail'):
            media_thumb = entry.media_thumbnail
            if media_thumb and isinstance(media_thumb, list) and len(media_thumb) > 0:
                thumb = media_thumb[0]
                if isinstance(thumb, dict) and 'url' in thumb:
                    image_url = thumb['url']
                    images.append({
                        'src': image_url,
                        'alt': title
                    })

        # 4. 기본 이미지 필드 확인
        if not image_url and hasattr(entry, 'image') and hasattr(entry.image, 'href'):
            image_url = entry.image.href
            images.append({
                'src': image_url,
                'alt': title
            })

        # 콘텐츠에서 이미지 추출 시도
        if 'content' in entry and entry.content:
            for content_item in entry.content:
                if 'value' in content_item:
                    soup = BeautifulSoup(content_item.value, 'html.parser')
                    for img in soup.find_all('img'):
                        if img.get('src'):
                            src = img.get('src')
                            # 상대 경로 확인
                            if not bool(urlparse(src).netloc):
                                src = urljoin(url, src)
                            images.append({
                                'src': src,
                                'alt': img.get('alt', title)
                            })
                            if not image_url:
                                image_url = src
                            break

        # Fetch full article content using enhanced content processor
        content_result = self._fetch_article_content(url)
        content = content_result["content"]

        # 콘텐츠가 빈 경우 기본 요약 또는 콘텐츠 사용
        if not content:
            # Try to use full content if available
            if 'content' in entry and entry.content:
                for content_item in entry.content:
                    if 'value' in content_item:
                        soup = BeautifulSoup(content_item.value, 'html.parser')
                        content = soup.get_text()
                        break

            # Otherwise use summary
            if not content and summary:
                content = summary

        # 생성된 요약이 없으면 entry의 요약 사용
        if not content_result["summary"] and summary:
            content_result["summary"] = summary

        # 추가 이미지 병합
        if content_result["images"]:
            # 이미 가지고 있는 이미지 URL 집합
            existing_urls = {img["src"] for img in images}
            for img in content_result["images"]:
                if img["src"] not in existing_urls:
                    images.append(img)
                    existing_urls.add(img["src"])
                    # 대표 이미지가 없으면 첫 번째 이미지 사용
                    if not image_url:
                        image_url = img["src"]

        # Generate unique ID
        _id = hashlib.md5(url.encode('utf-8')).hexdigest()

        # AI를 사용한 기사 분석 및 요약 (길이가 충분한 경우만)
        ai_enhanced = False
        ai_summary = ""
        ai_keywords = []
        trust_score = 0.5  # 기본값
        sentiment_score = 0  # 기본값

        # 콘텐츠 길이가 충분한 경우만 AI 처리 (비용 및 성능 최적화)
        min_content_length = 300  # 최소 콘텐츠 길이

        if len(content) >= min_content_length:
            try:
                logger.info(f"AI 분석 시작: {url}")
                # AI 요약 및 분석 (LangChain 서비스 활용)
                ai_result = self.langchain_service.analyze_news_sync(title, content)

                if not "error" in ai_result:
                    # AI 요약 적용
                    ai_summary = ai_result.get("summary", "")
                    ai_keywords = ai_result.get("keywords", [])

                    # 추가 분석 결과
                    trust_score = min(1.0, float(ai_result.get("importance", 5)) / 10.0)
                    sentiment_label = ai_result.get("sentiment", "neutral")

                    # 감정 스코어 계산
                    if sentiment_label == "positive":
                        sentiment_score = 0.7
                    elif sentiment_label == "negative":
                        sentiment_score = -0.7

                    # AI 강화 성공 표시
                    ai_enhanced = True
                    logger.info(f"AI 분석 성공: {url}")
                else:
                    logger.warning(f"AI 분석 실패: {ai_result.get('error')}")
            except Exception as e:
                logger.error(f"AI 요약 생성 오류: {str(e)}")
        else:
            logger.info(f"콘텐츠 길이 부족으로 AI 분석 생략 ({len(content)} < {min_content_length}): {url}")

        # 최종 요약 선택 (AI 요약 우선, 없으면 기존 요약 사용)
        final_summary = ai_summary if ai_enhanced and ai_summary else content_result["summary"]

        # Create article object with enhanced data
        article = {
            "_id": _id,
            "title": title,
            "content": content,
            "url": url,
            "source": source,
            "published_date": published_date,
            "author": author,
            "image_url": image_url,
            "categories": categories,
            "summary": final_summary,
            "images": images,
            "word_count": content_result["word_count"] or len(content.split()),
            "keywords": ai_keywords if ai_enhanced else [],
            "ai_enhanced": ai_enhanced,
            "trust_score": trust_score,
            "sentiment_score": sentiment_score,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        return article

    def _fetch_article_content(self, url: str) -> Dict[str, Any]:
        """Fetch and extract the main content from an article URL with enhanced processing"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # 인코딩 추정 처리
            response.encoding = response.apparent_encoding or 'utf-8'

            # ContentProcessor를 사용하여 콘텐츠 향상
            enhanced_content = self.content_processor.enhance_article(response.text, url)

            result = {
                "content": enhanced_content["content"],
                "summary": enhanced_content["summary"],
                "images": enhanced_content["images"],
                "word_count": enhanced_content["word_count"]
            }

            # 만약 콘텐츠가 정상적으로 추출되지 않았다면 대체 방법 시도
            if not enhanced_content["has_content"] or len(enhanced_content["content"]) < 100:
                logger.warning(f"ContentProcessor failed to extract content from {url}, trying fallback method")

                # Parse HTML - 기존 방식으로 재시도
                soup = BeautifulSoup(response.text, 'html.parser')

                # Remove script and style elements
                for script in soup(["script", "style", "header", "footer", "nav", "aside"]):
                    script.extract()

                # Find article content based on common patterns
                article_content = None

                # Try to find article by semantic tags
                article_tag = soup.find('article')
                if article_tag:
                    article_content = article_tag.get_text(separator=' ', strip=True)

                # If no article tag, try common content div patterns
                if not article_content or len(article_content) < 200:
                    content_divs = soup.select('div.content, div.article-content, div.post-content, div.entry-content, div.story')
                    if content_divs:
                        article_content = content_divs[0].get_text(separator=' ', strip=True)

                # If still no content, get all paragraphs within the body
                if not article_content or len(article_content) < 200:
                    paragraphs = soup.select('p')
                    if paragraphs:
                        article_content = ' '.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])

                # If still no content, use the whole body text as a last resort
                if not article_content or len(article_content) < 200:
                    if soup.body:
                        article_content = soup.body.get_text(separator=' ', strip=True)
                    else:
                        article_content = soup.get_text(separator=' ', strip=True)

                # 이미지 추출 (대체 방법)
                fallback_images = []
                for img in soup.find_all('img'):
                    if img.get('src'):
                        src = img.get('src')
                        alt = img.get('alt', '')

                        # 상대 경로 처리
                        if not bool(urlparse(src).netloc):
                            src = urljoin(url, src)

                        fallback_images.append({
                            'src': src,
                            'alt': alt
                        })

                # 결과 업데이트
                result["content"] = article_content
                # 이미지가 추출되지 않았다면 fallback 이미지 사용
                if not result["images"]:
                    result["images"] = fallback_images[:5]  # 상위 5개만 사용

                # 요약이 없다면 생성
                if not result["summary"] and article_content:
                    result["summary"] = self.content_processor.generate_summary(article_content)

            return result

        except Exception as e:
            logger.error(f"Error fetching article content from {url}: {e}")
            return {
                "content": "",
                "summary": "",
                "images": [],
                "word_count": 0,
                "error": str(e)
            }

    def save_articles_to_db(self, articles: List[Dict[str, Any]]) -> int:
        """Save articles to MongoDB"""
        if not articles:
            logger.warning("❌ 저장할 기사가 없습니다.")
            return 0

        logger.info(f"💾 데이터베이스에 {len(articles)}개 기사 저장 시작")

        # 기존 데이터베이스 기사 수 확인
        existing_count = news_collection.count_documents({})
        logger.info(f"📊 현재 DB 기사 수: {existing_count}개")

        # 카테고리별 통계
        categories = {}
        for article in articles:
            category = article.get("category", "미분류")
            if category in categories:
                categories[category] += 1
            else:
                categories[category] = 1

        # 카테고리 통계 출력
        for category, count in categories.items():
            logger.info(f"📂 카테고리 '{category}': {count}개 기사")

        saved_count = 0
        new_count = 0
        for article in articles:
            try:
                result = news_collection.update_one(
                    {"_id": article["_id"]},
                    {"$set": article},
                    upsert=True
                )
                saved_count += 1
                if result.upserted_id:
                    new_count += 1
            except Exception as e:
                logger.error(f"❌ 기사 저장 오류: {e}")
                if "_id" in article and "title" in article:
                    logger.error(f"   - 기사 ID: {article['_id']}, 제목: {article['title'][:30]}...")
                continue

        logger.info(f"✅ 데이터베이스에 총 {saved_count}개 기사 저장됨 (신규: {new_count}개, 업데이트: {saved_count-new_count}개)")
        logger.info(f"📊 저장 후 DB 기사 수: {news_collection.count_documents({})}개")
        return saved_count

    def crawl_and_save(self) -> int:
        """Fetch RSS feeds, crawl article content, and save to database"""
        articles = self.fetch_rss_feeds()
        return self.save_articles_to_db(articles)


# Helper function to run crawler
def run_crawler() -> int:
    """Run the RSS crawler"""
    logger.info("🚀 [크롤러] RSS 수집 시작")
    try:
        crawler = RSSCrawler()
        articles_count = crawler.crawl_and_save()
        logger.info(f"✅ [크롤러] RSS 수집 완료: {articles_count}개 기사 저장됨")
        return articles_count
    except Exception as e:
        logger.error(f"❌ [크롤러] 실행 중 에러 발생: {str(e)}")
        return 0
