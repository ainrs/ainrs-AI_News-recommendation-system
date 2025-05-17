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
        고급 파싱 기법으로 더 정확하고 안정적인 추출을 수행합니다.
        """
        try:
            # html_content 유효성 검사
            if html_content is None or not isinstance(html_content, str) or not html_content.strip():
                logger.warning("HTML 콘텐츠가 없거나 유효하지 않습니다.")
                return "", []

            # 안정적인 파싱을 위해 lxml 파서 사용 (더 빠르고 견고함)
            try:
                from lxml import etree
                soup = BeautifulSoup(html_content, 'lxml')
            except ImportError:
                # lxml이 설치되지 않은 경우 기본 파서 사용
                soup = BeautifulSoup(html_content, 'html.parser')
                logger.info("lxml 패키지가 없어 html.parser를 사용합니다.")

            # 메인 콘텐츠 후보들
            content_candidates = []

            # 고급 콘텐츠 추출을 위한 readability 라이브러리 시도
            try:
                from readability import Document
                doc = Document(html_content)
                readable_html = doc.summary()
                readable_soup = BeautifulSoup(readable_html, 'lxml' if 'lxml' in str(soup.__class__) else 'html.parser')
                # readability가 추출한 컨텐츠를 최우선 후보로 추가
                if readable_soup.text and len(readable_soup.text.strip()) > 100:
                    content_candidates.append((readable_soup, len(readable_soup.text) * 1.5))  # 가중치 부여
            except ImportError:
                logger.info("readability 라이브러리가 없어 고급 콘텐츠 추출을 건너뜁니다.")
            except Exception as e:
                logger.warning(f"readability 처리 중 오류: {e}")

            # 1. article 태그 확인 (가장 일반적인 뉴스 컨테이너)
            articles = soup.find_all('article')
            for article in articles:
                if article and article.text and len(article.text.strip()) > 100:
                    content_candidates.append((article, len(article.text)))

            # 2. 일반적인 콘텐츠 컨테이너 확인 (다양한 사이트의 일반적인 클래스 포함)
            for selector in [
                '.article-content', '.entry-content', '.post-content', '.story-content',
                '.news-content', '.article-body', '.content-body', '.story-body',
                '.article__body', '.article__content', '.post__content', '.post-body',
                'main', '.main-content', '.main-article', '#content', '#main-content'
            ]:
                try:
                    containers = soup.select(selector)
                    for container in containers:
                        if container and hasattr(container, 'get_text') and container.get_text().strip():
                            content_candidates.append((container, len(container.get_text())))
                except Exception as e:
                    logger.debug(f"선택자 '{selector}' 처리 중 오류: {e}")

            # 3. 텍스트 콘텐츠가 가장 많은 div 확인 (더 정교한 방식으로)
            divs = soup.find_all('div')
            for div in divs:
                try:
                    # 텍스트 내용이 있는 p 태그 개수 확인
                    p_tags = div.find_all('p')
                    text_p_tags = [p for p in p_tags if p.text.strip()]

                    # 최소 3개 이상의 문단이 있고, 전체 텍스트가 일정 길이 이상인 경우
                    if len(text_p_tags) >= 3 and len(div.get_text().strip()) > 200:
                        # 중첩된 div를 피하기 위해 부모-자식 관계 확인
                        parent_divs = [candidate[0] for candidate in content_candidates if candidate[0].name == 'div']
                        is_child = any(div in parent_div.find_all('div', recursive=True) for parent_div in parent_divs)

                        if not is_child:  # 이미 추가된 div의 자식이 아닌 경우만 추가
                            content_candidates.append((div, len(div.get_text())))
                except Exception as e:
                    logger.debug(f"div 처리 중 오류: {e}")

            # 콘텐츠 품질 점수 계산 및 정렬
            scored_candidates = []
            for element, text_length in content_candidates:
                try:
                    # 기본 점수는 텍스트 길이
                    score = text_length

                    # p 태그 수에 따른 가중치 (더 많은 p 태그는 더 좋은 컨텐츠를 의미할 수 있음)
                    p_count = len(element.find_all('p'))
                    score += p_count * 10

                    # 제목 태그(h1, h2 등)가 있으면 가중치 부여
                    headings = len(element.find_all(['h1', 'h2', 'h3', 'h4']))
                    score += headings * 50

                    # 이미지가 있으면 가중치 부여
                    images = len(element.find_all('img'))
                    score += images * 30

                    scored_candidates.append((element, score))
                except Exception as e:
                    logger.debug(f"점수 계산 중 오류: {e}")
                    scored_candidates.append((element, text_length))  # 오류 시 원래 점수 사용

            # 점수가 높은 순으로 정렬
            scored_candidates.sort(key=lambda x: x[1], reverse=True)

            main_content_html = ""

            # 변수명이 변경되었으므로 수정
            if scored_candidates:
                # 최고 점수 후보 선택
                main_content_element = scored_candidates[0][0]

                # 불필요한 요소 제거 후 HTML 추출
                for tag in main_content_element.find_all(['script', 'style', 'iframe', 'ins', 'footer', 'nav']):
                    tag.decompose()

                # 광고 관련 클래스 제거
                for tag in main_content_element.find_all(class_=lambda c: c and any(ad in c.lower() for ad in ['ad', 'banner', 'sponsor', 'popup', 'subscribe'])):
                    tag.decompose()

                main_content_html = str(main_content_element)
            else:
                # 백업 메커니즘: 후보가 없으면 더 일반적인 방법으로 시도
                try:
                    # 1. newspaper3k 라이브러리 사용 시도
                    try:
                        from newspaper import fulltext
                        text = fulltext(html_content)
                        if text and len(text) > 200:
                            return text, self._extract_images(soup)
                    except ImportError:
                        logger.info("newspaper3k 라이브러리가 없어 건너뜁니다.")
                    except Exception as e:
                        logger.debug(f"newspaper3k 처리 중 오류: {e}")

                    # 2. p 태그만 수집
                    paragraphs = soup.find_all('p')
                    if paragraphs:
                        # 너무 짧은 p 태그는 제외 (메뉴, 저작권 등)
                        valid_p_tags = [p for p in paragraphs if len(p.text.strip()) > 20]
                        if valid_p_tags:
                            main_content_html = ''.join(str(p) for p in valid_p_tags)
                        else:
                            main_content_html = ''.join(str(p) for p in paragraphs)
                    else:
                        # 3. 마지막 수단: body 또는 전체 HTML
                        main_content_html = str(soup.body) if soup.body else str(soup)
                except Exception as e:
                    logger.error(f"백업 콘텐츠 추출 중 오류: {e}")
                    main_content_html = html_content  # 원본 반환

            # 이미지 추출
            images = self._extract_images(soup)

            # HTML2Text로 변환
            markdown_content = self.html_converter.handle(main_content_html)

            return markdown_content, images
        except Exception as e:
            logger.error(f"메인 콘텐츠 추출 중 오류 발생: {e}")
            return "", []

    def _extract_images(self, soup):
        """
        HTML에서 이미지를 추출하는 내부 헬퍼 함수
        """
        images = []
        try:
            for img in soup.find_all('img'):
                try:
                    if img.get('src'):
                        src = img.get('src')
                        alt = img.get('alt', '')
                        title = img.get('title', '')
                        width = img.get('width', 0)
                        height = img.get('height', 0)

                        # 이미지 URL이 상대 경로인 경우 처리
                        if not bool(urlparse(src).netloc):
                            # base_url 확인
                            base_tags = soup.find_all('base', href=True)
                            base_url = base_tags[0]['href'] if base_tags else getattr(soup, '_base_url', '')
                            if base_url:
                                src = urljoin(base_url, src)

                        # 이미지 크기가 너무 작으면 아이콘이나 버튼일 가능성이 높음
                        try:
                            w = int(width) if width else 0
                            h = int(height) if height else 0
                            if w > 0 and h > 0 and (w < 50 or h < 50):
                                continue
                        except (ValueError, TypeError):
                            pass

                        # 유효한 이미지 확장자 확인
                        _, ext = os.path.splitext(src.split('?')[0])
                        if ext.lower() in self.valid_image_extensions:
                            # 중복 이미지 제거
                            if not any(img_info['src'] == src for img_info in images):
                                images.append({
                                    'src': src,
                                    'alt': alt,
                                    'title': title
                                })
                except Exception as e:
                    logger.debug(f"이미지 처리 중 오류: {e}")
                    continue  # 한 이미지의 오류가 전체 처리를 멈추지 않도록

            # 크고 중요한 이미지를 더 우선적으로 선택 (데이터 속성 점수 부여)
            for i, img_info in enumerate(images):
                try:
                    src = img_info['src']
                    # 'featured', 'hero', 'main' 등의 키워드가 포함된 이미지는 더 높은 점수
                    score = 0
                    keywords = ['featured', 'hero', 'main', 'lead', 'thumbnail', 'cover']
                    if any(kw in src.lower() for kw in keywords):
                        score += 10
                    # 'logo', 'icon', 'button' 등의 키워드가 포함된 이미지는 낮은 점수
                    negative = ['logo', 'icon', 'button', 'banner', 'ad', 'avatar']
                    if any(kw in src.lower() for kw in negative):
                        score -= 10
                    # 파일명이 숫자만인 경우 (일반적으로 중요한 이미지)
                    filename = os.path.basename(src.split('?')[0])
                    name, _ = os.path.splitext(filename)
                    if name.isdigit() and len(name) > 4:
                        score += 5

                    img_info['score'] = score
                except:
                    img_info['score'] = 0

            # 점수로 정렬하고 상위 이미지만 유지
            images.sort(key=lambda x: x.get('score', 0), reverse=True)
            # 점수 필드 제거
            for img in images:
                if 'score' in img:
                    del img['score']

            return images
        except Exception as e:
            logger.error(f"이미지 추출 중 오류: {e}")
            return []

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
