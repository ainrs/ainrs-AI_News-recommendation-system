"""
스마트 필터링 서비스
- RSS 400개 → 카테고리별 균형 맞춘 우선순위 선별
- 중복 제거 및 품질 평가
- 정치 쏠림 해결
"""

import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
from difflib import SequenceMatcher
import re
from datetime import datetime
import numpy as np

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartFilteringService:
    """
    스마트 필터링 서비스
    - 카테고리별 균형 수집
    - 품질 기반 우선순위
    - 중복 제거
    """

    def __init__(self):
        """필터링 서비스 초기화"""

        # 카테고리별 목표 기사 수 (총 50개 → 카테고리 균형)
        self.category_targets = {
            "인공지능": 8,      # AI 관련 (높은 관심도)
            "빅데이터": 6,      # 데이터 관련
            "클라우드": 5,      # 클라우드 관련
            "로봇": 4,          # 로봇/자동화
            "블록체인": 4,      # 블록체인/암호화폐
            "메타버스": 4,      # VR/AR/메타버스
            "IT기업": 6,        # IT 기업 뉴스
            "스타트업": 5,      # 스타트업/투자
            "AI서비스": 4,      # AI 서비스/플랫폼
            "칼럼": 4           # 전문가 칼럼
        }

        # 신뢰할 수 있는 언론사 가중치
        self.source_weights = {
            "yna.co.kr": 1.0,           # 연합뉴스
            "ytn.co.kr": 0.9,           # YTN
            "kbs.co.kr": 0.9,           # KBS
            "news.chosun.com": 0.8,     # 조선일보
            "hani.co.kr": 0.8,          # 한겨레
            "khan.co.kr": 0.8,          # 경향신문
            "donga.com": 0.8,           # 동아일보
            "etnews.com": 0.9,          # 전자신문 (IT 전문)
            "zdnet.co.kr": 0.9,         # ZDNet (IT 전문)
            "bloter.net": 0.7,          # 블로터
            "itworld.co.kr": 0.8,       # IT World
        }

        # 품질 평가 키워드
        self.quality_keywords = {
            "high_quality": ["발표", "공개", "출시", "개발", "연구", "분석", "보고서", "조사", "발견"],
            "medium_quality": ["계획", "예정", "검토", "논의", "회의", "협의"],
            "low_quality": ["추측", "소문", "예상", "관측", "추정"]
        }

    def filter_articles_smart(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        스마트 필터링 메인 함수
        Args:
            articles: RSS에서 수집한 전체 기사 리스트
        Returns:
            필터링된 우선순위 기사 리스트
        """
        try:
            logger.info(f"🔍 스마트 필터링 시작: {len(articles)}개 기사")

            # 1단계: 중복 제거
            unique_articles = self._remove_duplicates(articles)
            logger.info(f"📋 중복 제거 후: {len(unique_articles)}개 기사")

            # 2단계: 카테고리별 분류 및 개선
            categorized_articles = self._categorize_articles(unique_articles)

            # 3단계: 품질 점수 계산
            scored_articles = self._calculate_quality_scores(categorized_articles)

            # 4단계: 카테고리별 균형 선별
            balanced_articles = self._balance_categories(scored_articles)
            logger.info(f"⚖️ 카테고리 균형 조정 후: {len(balanced_articles)}개 기사")

            # 5단계: 최종 우선순위 정렬
            final_articles = self._final_priority_sort(balanced_articles)

            # 통계 출력
            self._log_filtering_stats(articles, final_articles)

            return final_articles

        except Exception as e:
            logger.error(f"❌ 스마트 필터링 실패: {str(e)}")
            # 실패 시 원본의 앞부분 반환
            return articles[:50]

    def _remove_duplicates(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 기사 제거"""
        try:
            unique_articles = []
            seen_urls = set()
            seen_titles = {}

            for article in articles:
                url = article.get('url', '')
                title = article.get('title', '')

                # URL 중복 체크
                if url in seen_urls:
                    continue

                # 제목 유사도 체크 (90% 이상 유사하면 중복)
                is_similar = False
                for seen_title in seen_titles.keys():
                    similarity = SequenceMatcher(None, title.lower(), seen_title.lower()).ratio()
                    if similarity > 0.9:
                        is_similar = True
                        # 더 긴 제목을 선택
                        if len(title) > len(seen_title):
                            # 기존 기사를 새 기사로 교체
                            unique_articles = [a for a in unique_articles if a.get('title') != seen_title]
                            seen_titles.pop(seen_title)
                        else:
                            break

                if not is_similar:
                    seen_urls.add(url)
                    seen_titles[title] = True
                    unique_articles.append(article)

            return unique_articles

        except Exception as e:
            logger.error(f"❌ 중복 제거 실패: {str(e)}")
            return articles

    def _categorize_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """기사 카테고리 분류 개선"""
        try:
            categorized = []

            for article in articles:
                title = article.get('title', '').lower()
                content = article.get('content', '').lower()
                url = article.get('url', '')

                # 기존 카테고리가 있으면 유지, 없으면 새로 분류
                existing_categories = article.get('categories', [])

                if not existing_categories or existing_categories == ['인공지능']:
                    # 더 정밀한 카테고리 분류
                    new_category = self._classify_category_improved(title, content, url)
                    article['categories'] = [new_category]
                    article['category_method'] = 'smart_filtering'
                else:
                    article['category_method'] = 'existing'

                categorized.append(article)

            return categorized

        except Exception as e:
            logger.error(f"❌ 카테고리 분류 실패: {str(e)}")
            return articles

    def _classify_category_improved(self, title: str, content: str, url: str) -> str:
        """개선된 카테고리 분류"""
        text = title + " " + content

        # 카테고리별 키워드 점수 계산 (가중치 적용)
        category_scores = {
            "인공지능": self._score_keywords(text, [
                ("ai", 3), ("인공지능", 3), ("머신러닝", 3), ("딥러닝", 3),
                ("신경망", 2), ("알고리즘", 2), ("자동화", 2), ("학습", 1)
            ]),
            "빅데이터": self._score_keywords(text, [
                ("빅데이터", 3), ("데이터", 3), ("analytics", 3), ("분석", 2),
                ("데이터베이스", 2), ("정보", 1), ("통계", 2), ("수집", 1)
            ]),
            "클라우드": self._score_keywords(text, [
                ("클라우드", 3), ("cloud", 3), ("aws", 3), ("azure", 3), ("gcp", 3),
                ("서버", 2), ("호스팅", 2), ("인프라", 2), ("saas", 2)
            ]),
            "로봇": self._score_keywords(text, [
                ("로봇", 3), ("robot", 3), ("드론", 3), ("자동화", 2),
                ("제조", 2), ("공장", 1), ("산업용", 2), ("기계", 1)
            ]),
            "블록체인": self._score_keywords(text, [
                ("블록체인", 3), ("blockchain", 3), ("암호화폐", 3), ("비트코인", 3),
                ("이더리움", 3), ("nft", 3), ("코인", 2), ("crypto", 2)
            ]),
            "메타버스": self._score_keywords(text, [
                ("메타버스", 3), ("metaverse", 3), ("가상현실", 3), ("vr", 3), ("ar", 3),
                ("증강현실", 3), ("3d", 2), ("가상", 2), ("immersive", 2)
            ]),
            "IT기업": self._score_keywords(text, [
                ("it기업", 3), ("테크", 3), ("tech", 3), ("소프트웨어", 2),
                ("기업", 2), ("회사", 1), ("개발", 2), ("서비스", 1)
            ]),
            "스타트업": self._score_keywords(text, [
                ("스타트업", 3), ("startup", 3), ("벤처", 3), ("투자", 3),
                ("펀딩", 3), ("창업", 2), ("신생", 2), ("초기", 1)
            ]),
            "AI서비스": self._score_keywords(text, [
                ("ai서비스", 3), ("플랫폼", 2), ("서비스", 2), ("솔루션", 2),
                ("앱", 2), ("application", 2), ("도구", 1), ("시스템", 1)
            ]),
            "칼럼": self._score_keywords(text, [
                ("칼럼", 3), ("opinion", 3), ("column", 3), ("기고", 3), ("사설", 3),
                ("의견", 2), ("논평", 2), ("분석", 1), ("전망", 1)
            ])
        }

        # URL 기반 추가 점수
        for domain, category in [
            ("etnews.com", "IT기업"), ("zdnet.co.kr", "IT기업"),
            ("bloter.net", "스타트업"), ("aitimes.com", "인공지능"),
            ("venturesquare.net", "스타트업"), ("platum.kr", "스타트업")
        ]:
            if domain in url:
                category_scores[category] += 2

        # 최고 점수 카테고리 선택
        best_category = max(category_scores, key=category_scores.get)
        max_score = category_scores[best_category]

        # 점수가 너무 낮으면 기본값
        if max_score < 2:
            return "IT기업"  # 기본값을 IT기업으로 변경 (인공지능 쏠림 방지)

        return best_category

    def _score_keywords(self, text: str, keywords_weights: List[Tuple[str, int]]) -> int:
        """키워드 가중치 점수 계산"""
        score = 0
        for keyword, weight in keywords_weights:
            count = text.count(keyword)
            score += count * weight
        return score

    def _calculate_quality_scores(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """품질 점수 계산"""
        try:
            for article in articles:
                title = article.get('title', '')
                content = article.get('content', '')
                url = article.get('url', '')
                source = article.get('source', '')

                score = 5.0  # 기본 점수

                # 1. 출처 신뢰도
                source_weight = 0.5
                for domain, weight in self.source_weights.items():
                    if domain in url:
                        source_weight = weight
                        break
                score += source_weight * 2

                # 2. 제목 품질
                title_score = self._evaluate_title_quality(title)
                score += title_score

                # 3. 내용 품질
                content_score = self._evaluate_content_quality(content)
                score += content_score

                # 4. 최신성 (발행일 기준)
                recency_score = self._evaluate_recency(article.get('published_date'))
                score += recency_score

                article['quality_score'] = round(score, 2)
                article['score_breakdown'] = {
                    'source': source_weight * 2,
                    'title': title_score,
                    'content': content_score,
                    'recency': recency_score
                }

            return articles

        except Exception as e:
            logger.error(f"❌ 품질 점수 계산 실패: {str(e)}")
            return articles

    def _evaluate_title_quality(self, title: str) -> float:
        """제목 품질 평가"""
        score = 0.0

        # 제목 길이 (10-60자가 적당)
        length = len(title)
        if 10 <= length <= 60:
            score += 1.0
        elif length > 60:
            score += 0.5

        # 특수문자나 의문문 패턴
        if '?' in title or '!' in title:
            score += 0.5

        # 부정적 단어 (클릭베이트 감소)
        clickbait_words = ['충격', '놀라운', '반전', '대박', '미친']
        if any(word in title for word in clickbait_words):
            score -= 0.5

        # 품질 키워드
        for keyword in self.quality_keywords['high_quality']:
            if keyword in title:
                score += 0.3

        return max(0, score)

    def _evaluate_content_quality(self, content: str) -> float:
        """내용 품질 평가"""
        score = 0.0

        # 내용 길이
        length = len(content)
        if length > 500:
            score += 1.5
        elif length > 200:
            score += 1.0
        elif length > 100:
            score += 0.5

        # 품질 키워드 비율
        high_quality_count = sum(1 for kw in self.quality_keywords['high_quality'] if kw in content)
        low_quality_count = sum(1 for kw in self.quality_keywords['low_quality'] if kw in content)

        score += high_quality_count * 0.2
        score -= low_quality_count * 0.3

        return max(0, score)

    def _evaluate_recency(self, published_date) -> float:
        """최신성 평가"""
        try:
            if not published_date:
                return 0.5

            if isinstance(published_date, str):
                from datetime import datetime
                published_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))

            now = datetime.utcnow()
            diff_hours = (now - published_date.replace(tzinfo=None)).total_seconds() / 3600

            # 24시간 이내: 1.0, 48시간 이내: 0.5, 그 이후: 0.2
            if diff_hours <= 24:
                return 1.0
            elif diff_hours <= 48:
                return 0.5
            else:
                return 0.2

        except Exception:
            return 0.5

    def _balance_categories(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """카테고리별 균형 선별"""
        try:
            # 카테고리별 기사 그룹화
            category_groups = defaultdict(list)
            for article in articles:
                categories = article.get('categories', ['기타'])
                category = categories[0] if categories else '기타'
                category_groups[category].append(article)

            # 카테고리별 정렬 (품질 점수 기준)
            for category in category_groups:
                category_groups[category].sort(
                    key=lambda x: x.get('quality_score', 0),
                    reverse=True
                )

            # 균형 선별
            balanced_articles = []
            for category, target_count in self.category_targets.items():
                available_articles = category_groups.get(category, [])
                selected_count = min(target_count, len(available_articles))

                selected = available_articles[:selected_count]
                balanced_articles.extend(selected)

                logger.info(f"📂 {category}: {selected_count}/{target_count}개 선별 (available: {len(available_articles)})")

            # 부족한 경우 다른 카테고리에서 보충
            total_selected = len(balanced_articles)
            target_total = sum(self.category_targets.values())

            if total_selected < target_total:
                remaining_articles = []
                for category, articles_list in category_groups.items():
                    if category not in self.category_targets:
                        remaining_articles.extend(articles_list)
                    else:
                        # 이미 선별된 것 제외
                        selected_urls = {a['url'] for a in balanced_articles if a.get('categories', [''])[0] == category}
                        extra = [a for a in articles_list if a['url'] not in selected_urls]
                        remaining_articles.extend(extra)

                # 품질 점수 기준 정렬 후 부족한 만큼 추가
                remaining_articles.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
                need_more = target_total - total_selected
                balanced_articles.extend(remaining_articles[:need_more])

            return balanced_articles

        except Exception as e:
            logger.error(f"❌ 카테고리 균형 조정 실패: {str(e)}")
            return articles[:50]

    def _final_priority_sort(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """최종 우선순위 정렬"""
        try:
            # 복합 점수 계산 (품질 + 다양성)
            for article in articles:
                base_score = article.get('quality_score', 5.0)

                # 카테고리 다양성 보너스
                category = article.get('categories', [''])[0]
                if category in ['로봇', '메타버스', '블록체인']:  # 상대적으로 적은 카테고리
                    base_score += 0.5

                article['final_score'] = base_score

            # 최종 정렬
            articles.sort(key=lambda x: x.get('final_score', 0), reverse=True)

            return articles

        except Exception as e:
            logger.error(f"❌ 최종 정렬 실패: {str(e)}")
            return articles

    def _log_filtering_stats(self, original_articles: List, filtered_articles: List):
        """필터링 통계 출력"""
        try:
            logger.info("📊 스마트 필터링 통계:")
            logger.info(f"   원본: {len(original_articles)}개 → 선별: {len(filtered_articles)}개")

            # 카테고리별 분포
            category_dist = Counter()
            for article in filtered_articles:
                categories = article.get('categories', ['기타'])
                category_dist[categories[0]] += 1

            logger.info("📂 카테고리별 분포:")
            for category, count in category_dist.items():
                target = self.category_targets.get(category, 0)
                logger.info(f"   {category}: {count}개 (목표: {target})")

            # 평균 품질 점수
            if filtered_articles:
                avg_quality = sum(a.get('quality_score', 0) for a in filtered_articles) / len(filtered_articles)
                logger.info(f"📈 평균 품질 점수: {avg_quality:.2f}")

        except Exception as e:
            logger.error(f"❌ 통계 출력 실패: {str(e)}")

# 전역 인스턴스
_smart_filtering_service = None

def get_smart_filtering_service() -> SmartFilteringService:
    """SmartFilteringService 싱글톤 인스턴스 반환"""
    global _smart_filtering_service
    if _smart_filtering_service is None:
        _smart_filtering_service = SmartFilteringService()
    return _smart_filtering_service
