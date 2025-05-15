import re
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests
try:
    import html2text
except ImportError:
    # 개발 환경을 위한 동적 임포트
    import sys
    import subprocess
    print("html2text 패키지가 필요합니다. 설치를 시도합니다...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "html2text"])
    import html2text
import json
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentProcessor:
    """
    뉴스 기사 콘텐츠를 처리하여 사용자 친화적인 형태로 변환하는 서비스
    """

    def __init__(self):
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.ignore_tables = False
        self.html_converter.body_width = 0  # 줄 바꿈 방지

        # 일반적인 뉴스 기사에서 제거할 요소들
        self.elements_to_remove = [
            'header', 'footer', 'nav', 'aside', 'script', 'style',
            'iframe', 'form', 'button', 'noscript', 'meta',
            'ins', 'svg', '.advertisement', '.ad-container', '.comment-section',
            '.social-share', '.newsletter', '.related-articles',
            '.subscription', '.paywall', '.popup', '.cookie-notice'
        ]

        # 유효한 이미지 확장자
        self.valid_image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

    def clean_html(self, html_content: str) -> str:
        """
        HTML 콘텐츠를 정리하고 필요없는 요소들을 제거합니다.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # 불필요한 요소 제거
            for element in self.elements_to_remove:
                for tag in soup.select(element):
                    tag.decompose()

            # 빈 문단 제거
            for p in soup.find_all('p'):
                if not p.text.strip():
                    p.decompose()

            # 광고, 구독 관련 요소 추가 확인 및 제거
            for tag in soup.find_all(['div', 'section']):
                if tag.attrs and 'class' in tag.attrs:
                    classes = ' '.join(tag.get('class', []))
                    if any(term in classes.lower() for term in ['ad', 'ads', 'advertisement', 'banner', 'subscribe', 'popup']):
                        tag.decompose()

                # id 속성으로도 확인
                if tag.has_attr('id') and any(term in tag['id'].lower() for term in ['ad', 'ads', 'banner', 'subscribe']):
                    tag.decompose()

            return str(soup)
        except Exception as e:
            logger.error(f"HTML 정리 중 오류 발생: {e}")
            return html_content

    def extract_main_content(self, html_content: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        HTML에서 주요 콘텐츠와 이미지를 추출합니다.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # 메인 콘텐츠 후보들
            content_candidates = []

            # 1. article 태그 확인
            article = soup.find('article')
            if article:
                content_candidates.append((article, len(article.get_text())))

            # 2. 일반적인 콘텐츠 컨테이너 확인
            for selector in ['.article-content', '.entry-content', '.post-content', '.story-content', '.news-content', 'main', '.main-content']:
                containers = soup.select(selector)
                for container in containers:
                    content_candidates.append((container, len(container.get_text())))

            # 3. 텍스트 콘텐츠가 가장 많은 div 확인
            divs = soup.find_all('div')
            for div in divs:
                if len(div.find_all('p')) > 3:  # 최소 3개 이상의 문단이 있는 경우
                    content_candidates.append((div, len(div.get_text())))

            # 콘텐츠가 가장 많은 요소 선택
            content_candidates.sort(key=lambda x: x[1], reverse=True)

            main_content_html = ""
            if content_candidates:
                main_content_element = content_candidates[0][0]
                main_content_html = str(main_content_element)
            else:
                # 후보가 없으면 전체 본문의 p 태그만 수집
                paragraphs = soup.find_all('p')
                if paragraphs:
                    main_content_html = ''.join(str(p) for p in paragraphs)
                else:
                    main_content_html = str(soup.body) if soup.body else str(soup)

            # 이미지 추출
            images = []
            for img in soup.find_all('img'):
                if img.get('src'):
                    src = img.get('src')
                    alt = img.get('alt', '')

                    # 이미지 URL이 상대 경로인 경우 처리
                    if not bool(urlparse(src).netloc):
                        # base_url이 있다고 가정
                        base_url = getattr(soup, '_base_url', '')
                        if base_url:
                            src = urljoin(base_url, src)

                    # 유효한 이미지 확장자 확인
                    _, ext = os.path.splitext(src.split('?')[0])
                    if ext.lower() in self.valid_image_extensions:
                        images.append({
                            'src': src,
                            'alt': alt
                        })

            # HTML2Text로 변환
            markdown_content = self.html_converter.handle(main_content_html)

            return markdown_content, images
        except Exception as e:
            logger.error(f"메인 콘텐츠 추출 중 오류 발생: {e}")
            return "", []

    def format_content(self, content: str) -> str:
        """
        마크다운 형식의 콘텐츠를 정리합니다.
        """
        try:
            # 여러 줄 바꿈 정리
            content = re.sub(r'\n{3,}', '\n\n', content)

            # 특수문자 정리
            content = re.sub(r'&nbsp;', ' ', content)
            content = re.sub(r'&amp;', '&', content)
            content = re.sub(r'&lt;', '<', content)
            content = re.sub(r'&gt;', '>', content)

            # 불필요한 공백 제거
            content = re.sub(r' {2,}', ' ', content)

            return content.strip()
        except Exception as e:
            logger.error(f"콘텐츠 포맷팅 중 오류 발생: {e}")
            return content

    def generate_summary(self, content: str, title: str = "", max_length: int = 200) -> str:
        """
        콘텐츠의 요약을 생성합니다. (간단한 규칙 기반 접근법)
        """
        try:
            # 매우 짧은 콘텐츠는 그대로 반환
            if len(content) <= max_length:
                return content

            # 문장 추출
            sentences = re.split(r'(?<=[.!?])\s+', content)

            if not sentences:
                return ""

            # 첫 문장은 항상 포함
            summary = [sentences[0]]
            current_length = len(sentences[0])

            # 중요 키워드 추출 (제목에서)
            keywords = []
            if title:
                # 불용어 제거
                stopwords = ['a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'by', '의', '에', '은', '는', '이', '가', '을', '를', '그', '및']
                keywords = [word.lower() for word in re.findall(r'\b\w+\b', title) if word.lower() not in stopwords]

            # 키워드가 포함된 문장 또는 첫 몇 문장 선택
            for sentence in sentences[1:]:
                # 최대 길이 체크
                if current_length + len(sentence) > max_length:
                    break

                # 키워드 체크
                if keywords and any(keyword in sentence.lower() for keyword in keywords):
                    summary.append(sentence)
                    current_length += len(sentence)
                # 아니면 처음 3개 문장까지만 추가
                elif len(summary) < 3:
                    summary.append(sentence)
                    current_length += len(sentence)

            return ' '.join(summary)
        except Exception as e:
            logger.error(f"요약 생성 중 오류 발생: {e}")
            if content and len(content) > max_length:
                return content[:max_length] + "..."
            return content

    def enhance_article(self, html_content: str, base_url: str = "") -> Dict[str, Any]:
        """
        뉴스 기사 HTML을 처리하여 향상된 콘텐츠로 반환합니다.
        """
        try:
            # HTML 정리
            cleaned_html = self.clean_html(html_content)

            # BeautifulSoup에 base_url 설정
            soup = BeautifulSoup(cleaned_html, 'html.parser')
            soup._base_url = base_url

            # 주요 콘텐츠 및 이미지 추출
            markdown_content, images = self.extract_main_content(str(soup))

            # 콘텐츠 포맷팅
            formatted_content = self.format_content(markdown_content)

            # 요약 생성
            title = soup.title.text if soup.title else ""
            summary = self.generate_summary(formatted_content, title)

            # 결과 반환
            return {
                "content": formatted_content,
                "summary": summary,
                "images": images,
                "has_content": bool(formatted_content.strip()),
                "word_count": len(formatted_content.split()),
                "processing_date": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"기사 향상 중 오류 발생: {e}")
            return {
                "content": html_content,
                "summary": "",
                "images": [],
                "has_content": True,
                "error": str(e),
                "processing_date": datetime.utcnow().isoformat()
            }

    def process_rss_item(self, item: Dict[str, Any], fetch_full_content: bool = True) -> Dict[str, Any]:
        """
        RSS 피드 항목을 처리하여 향상된 기사로 변환합니다.
        """
        try:
            result = {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "published_date": item.get("published_date", datetime.utcnow()),
                "source": item.get("source", ""),
                "author": item.get("author", ""),
                "categories": item.get("categories", []),
                "summary": item.get("summary", ""),
                "content": item.get("content", ""),
                "images": []
            }

            # 기본 이미지 확인
            if item.get("image_url"):
                result["images"].append({
                    "src": item["image_url"],
                    "alt": item.get("title", "")
                })

            # 전체 콘텐츠 가져오기
            if fetch_full_content and item.get("link"):
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml',
                        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                    }
                    response = requests.get(item["link"], headers=headers, timeout=10)

                    if response.status_code == 200:
                        # 인코딩 추정
                        response.encoding = response.apparent_encoding

                        # 콘텐츠 향상
                        enhanced = self.enhance_article(response.text, item["link"])

                        # 결과 업데이트
                        if enhanced["has_content"]:
                            result["content"] = enhanced["content"]
                            result["summary"] = enhanced["summary"] or result["summary"]

                            # 이미지 병합 (중복 제거)
                            existing_urls = {img["src"] for img in result["images"]}
                            for img in enhanced["images"]:
                                if img["src"] not in existing_urls:
                                    result["images"].append(img)
                                    existing_urls.add(img["src"])
                except Exception as fetch_error:
                    logger.error(f"전체 콘텐츠 가져오기 실패: {item['link']} - {fetch_error}")

            # 요약이 없으면 생성
            if not result["summary"] and result["content"]:
                result["summary"] = self.generate_summary(result["content"], result["title"])

            return result
        except Exception as e:
            logger.error(f"RSS 항목 처리 중 오류 발생: {e}")
            return item

# 싱글톤 인스턴스 관리
_content_processor = None

def get_content_processor() -> ContentProcessor:
    """
    ContentProcessor 인스턴스를 가져옵니다.
    """
    global _content_processor
    if _content_processor is None:
        _content_processor = ContentProcessor()
    return _content_processor
