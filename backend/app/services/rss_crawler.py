import os
import json
import hashlib
import logging
import requests
import feedparser
import uuid
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
                        # 기본 정보만 빠르게 추출하여 저장 (AI 분석 없이)
                        article = self._process_entry_basic(entry, source)
                        if article and not article.get('existing', False):
                            # 기본 정보로 DB에 저장 (빠른 UI 표시용)
                            try:
                                # _id가 없으면 새로 생성
                                if '_id' not in article:
                                    article['_id'] = hashlib.md5(article['url'].encode('utf-8')).hexdigest()

                                logger.info(f"🔄 기본 정보로 기사 저장: {article['title'][:30]}...")
                                news_collection.insert_one(article)

                                # 수집된 기사 목록에 추가 (AI 분석은 나중에 사용자가 클릭할 때 수행)
                                all_entries.append(article)
                                entry_count += 1
                            except Exception as db_error:
                                logger.error(f"❌ 기본 기사 DB 저장 오류: {str(db_error)}")
                        elif article and article.get('existing', False):
                            # 이미 존재하는 항목도 목록에 추가
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

        # 수집된 기사가 없는 경우 디버깅
        if len(all_entries) == 0:
            logger.warning("⚠️ 수집된 기사가 없습니다! RSS 피드 URL과 파싱 로직을 확인하세요.")
        else:
            # 첫 번째 기사 정보 출력 (디버깅용)
            first_article = all_entries[0]
            logger.info(f"🔍 첫 번째 기사 정보: 제목='{first_article.get('title', '제목 없음')[:30]}...', URL={first_article.get('url', 'URL 없음')}")

        return all_entries

    def _process_entry_basic(self, entry: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """빠르게 기본 정보만 추출하여 기사 객체 생성 (콜드 스타트 문제 해결용)"""
        # Extract URL
        url = entry.get('link')
        if not url:
            return None

        # Check if article already exists in database
        existing = news_collection.find_one({"url": url})
        if existing:
            logger.info(f"📋 기사가 이미 DB에 존재합니다: {url}")
            return {
                "_id": existing["_id"],
                "url": url,
                "title": entry.get('title', '').strip(),
                "source": source,
                "existing": True  # 기존 기사임을 표시
            }

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

        # Extract basic summary
        summary = ''
        if 'summary' in entry:
            soup = BeautifulSoup(entry.summary, 'html.parser')
            summary = soup.get_text(separator=' ', strip=True)

        # Extract basic image (빠른 처리용)
        image_url = ''
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            media_thumb = entry.media_thumbnail
            if isinstance(media_thumb, list) and len(media_thumb) > 0:
                thumb = media_thumb[0]
                if isinstance(thumb, dict) and 'url' in thumb:
                    image_url = thumb['url']

        # 카테고리 정보 추출
        categories = []
        # 항목의 태그나 카테고리 필드가 있는 경우
        if hasattr(entry, 'tags') and entry.tags:
            for tag in entry.tags:
                if hasattr(tag, 'term'):
                    categories.append(tag.term)

        # 카테고리가 비어있는 경우 기본 카테고리 추가
        if not categories:
            # 소스와 제목에서 카테고리 추론
            title_lower = title.lower() if title else ""

            # 프론트엔드 카테고리와 일치하도록 정의
            # (인공지능, 빅데이터, 클라우드, 로봇, 블록체인, 메타버스, IT기업, 스타트업, AI서비스, 칼럼)
            if "ai" in title_lower or "인공지능" in title_lower or "머신러닝" in title_lower or "딥러닝" in title_lower:
                categories = ["인공지능"]
            elif "빅데이터" in title_lower or "데이터" in title_lower or "data" in title_lower:
                categories = ["빅데이터"]
            elif "클라우드" in title_lower or "cloud" in title_lower:
                categories = ["클라우드"]
            elif "로봇" in title_lower or "robot" in title_lower:
                categories = ["로봇"]
            elif "블록체인" in title_lower or "암호화폐" in title_lower or "blockchain" in title_lower or "crypto" in title_lower:
                categories = ["블록체인"]
            elif "메타버스" in title_lower or "가상현실" in title_lower or "증강현실" in title_lower or "metaverse" in title_lower or "vr" in title_lower or "ar" in title_lower:
                categories = ["메타버스"]
            elif "it" in title_lower or "기업" in title_lower or "회사" in title_lower or "company" in title_lower or "테크" in title_lower:
                categories = ["IT기업"]
            elif "스타트업" in title_lower or "startup" in title_lower or "벤처" in title_lower:
                categories = ["스타트업"]
            elif "서비스" in title_lower or "플랫폼" in title_lower or "service" in title_lower or "platform" in title_lower:
                categories = ["AI서비스"]
            elif "칼럼" in title_lower or "opinion" in title_lower or "column" in title_lower or "기고" in title_lower or "사설" in title_lower:
                categories = ["칼럼"]
            else:
                categories = ["인공지능"]  # 기본값은 인공지능으로 설정

        # ID 생성
        _id = hashlib.md5(url.encode('utf-8')).hexdigest()

        # 내용(content) 추출 시도
        content = ""
        # 1. content 필드 확인
        if hasattr(entry, 'content') and entry.content:
            if isinstance(entry.content, list) and len(entry.content) > 0:
                if hasattr(entry.content[0], 'value'):
                    content_html = entry.content[0].value
                    soup = BeautifulSoup(content_html, 'html.parser')
                    content = soup.get_text(separator=' ', strip=True)

        # 2. content가 없으면 description 필드 확인
        if not content and hasattr(entry, 'description'):
            soup = BeautifulSoup(entry.description, 'html.parser')
            content = soup.get_text(separator=' ', strip=True)

        # 3. 여전히 내용이 없으면 summary 필드 확인
        if not content and summary:
            content = summary

        # 4. 그래도 내용이 없으면 최소한 제목을 내용으로 사용
        if not content:
            content = title + " (내용 없음)"

        # 기본 정보만으로 빠르게 기사 객체 생성
        basic_article = {
            "_id": _id,
            "title": title,
            "url": url,
            "source": source,
            "published_date": published_date,
            "summary": summary[:500] if summary else title[:100],  # 간단한 요약만
            "image_url": image_url or "https://via.placeholder.com/300x200?text=No+Image",
            "categories": categories,
            "content": content,  # 내용 추가
            "author": entry.get('author', source),  # 작성자가 없으면 출처를 작성자로 사용
            "ai_enhanced": False,  # 아직 AI 처리 안됨
            "trust_score": 0.5,  # 기본값
            "sentiment_score": 0,  # 기본값
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_basic_info": True  # 기본 정보만 있는 상태 표시
        }

        logger.info(f"✅ 기본 정보 기사 추출 완료: {title[:30]}...")
        return basic_article

    def _process_entry(self, entry: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """Process a single RSS entry and extract article content with enhanced processing"""
        # Extract URL
        url = entry.get('link')
        if not url:
            return None

        # Check if article already exists in database
        existing = news_collection.find_one({"url": url})
        if existing:
            logger.info(f"📋 기사가 이미 DB에 존재합니다: {url}")
            # 기존 기사도 반환하여 업데이트 기회 제공
            return {
                "_id": existing["_id"],
                "url": url,
                "title": entry.get('title', '').strip(),
                "source": source,
                "existing": True  # 기존 기사임을 표시
            }

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
            "updated_at": datetime.utcnow(),
            "is_basic_info": False  # 전체 정보 처리 완료 표시
        }

        # 이미 DB에 기본 정보로 저장되어 있다면 업데이트
        try:
            update_result = news_collection.update_one(
                {"_id": _id},
                {"$set": article}
            )

            if update_result.modified_count > 0:
                logger.info(f"🔄 AI 분석 완료 후 기사 업데이트: {title[:30]}...")
            else:
                # 업데이트된 것이 없으면 새로 삽입
                logger.info(f"🆕 AI 분석 완료 기사 신규 저장: {title[:30]}...")
                news_collection.insert_one(article)
        except Exception as db_error:
            logger.error(f"❌ 기사 DB 저장/업데이트 오류: {str(db_error)}")

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
                # 기존 기사인 경우 처리 방식 변경
                if article.get('existing', False):
                    logger.info(f"🔄 기존 기사 건너뜀: {article.get('title', '제목 없음')[:30]}...")
                    continue

                # article에서 _id 키 존재 확인
                if "_id" not in article:
                    article["_id"] = str(uuid.uuid4())  # 고유 ID 생성
                    logger.info(f"🆔 새 ID 생성: {article['_id']}")

                logger.info(f"📝 MongoDB에 기사 저장 시도: {article.get('title', '제목 없음')[:30]}...")

                # MongoDB에 저장 시도
                result = news_collection.update_one(
                    {"_id": article["_id"]},
                    {"$set": article},
                    upsert=True
                )
                saved_count += 1

                if result.upserted_id:
                    new_count += 1
                    logger.info(f"✅ 새 기사 저장 성공: {article.get('title', '제목 없음')[:30]}")
                else:
                    logger.info(f"🔄 기존 기사 업데이트: {article.get('title', '제목 없음')[:30]}")
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
        logger.info("📥 RSS 피드 가져오기 시작...")
        articles = self.fetch_rss_feeds()
        logger.info(f"📄 수집된 기사 수: {len(articles)}개")

        if not articles:
            logger.warning("⚠️ 수집된 기사가 없습니다. DB 저장 단계 건너뜁니다.")
            return 0

        logger.info("💾 데이터베이스에 기사 저장 시작...")
        saved_count = self.save_articles_to_db(articles)
        logger.info(f"✅ 저장 완료: {saved_count}개 기사가 DB에 저장됨")
        return saved_count


# Helper function to run crawler
def run_crawler() -> int:
    """Run the RSS crawler"""
    logger.info("🚀 [크롤러] RSS 수집 시작")
    try:
        crawler = RSSCrawler()
        logger.info("🔍 크롤러 인스턴스 생성 완료, 크롤링 시작...")
        articles_count = crawler.crawl_and_save()
        logger.info(f"✅ [크롤러] RSS 수집 완료: {articles_count}개 기사 저장됨")

        # 실제 저장된 기사 수 확인
        db_articles_count = news_collection.count_documents({})
        logger.info(f"📊 실제 DB 저장 기사 수: {db_articles_count}개")

        return articles_count
    except Exception as e:
        logger.error(f"❌ [크롤러] 실행 중 에러 발생: {str(e)}")
        return 0
