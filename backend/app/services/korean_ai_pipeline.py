"""
한국어 AI 파이프라인: KoBERT + KcELECTRA 조합
- KoBERT: 1차 카테고리 분류 및 감정 필터링
- KcELECTRA: 2차 정밀 감정 분석
- 목표: OpenAI 비용 절감 + 카테고리 편향 해결
"""

import logging
import torch
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    BertTokenizer, BertForSequenceClassification,
    ElectraTokenizer, ElectraForSequenceClassification
)
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from sklearn.preprocessing import LabelEncoder
import pickle
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KoreanAIPipeline:
    """
    KoBERT + KcELECTRA 기반 한국어 뉴스 분석 파이프라인
    - 카테고리 분류 (KoBERT)
    - 감정 분석 (KoBERT → KcELECTRA)
    - OpenAI 대체로 비용 절감
    """

    def __init__(self):
        """파이프라인 초기화"""
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"🔧 Korean AI Pipeline 초기화 - Device: {self.device}")

        # 뉴스 카테고리 정의 (프론트엔드와 일치)
        self.categories = [
            "인공지능", "빅데이터", "클라우드", "로봇", "블록체인",
            "메타버스", "IT기업", "스타트업", "AI서비스", "칼럼"
        ]

        # 모델 및 토크나이저 초기화
        self._initialize_models()

    def _initialize_models(self):
        """KoBERT + KcELECTRA 모델 로드"""
        try:
            # 1. KoBERT for 카테고리 분류 (1차 필터링)
            logger.info("📥 KoBERT 모델 로딩...")
            self.kobert_tokenizer = BertTokenizer.from_pretrained('skt/kobert-base-v1')
            self.kobert_model = BertForSequenceClassification.from_pretrained(
                'skt/kobert-base-v1',
                num_labels=len(self.categories)
            )
            self.kobert_model.to(self.device)
            self.kobert_model.eval()

            # 2. KcELECTRA for 정밀 감정 분석 (2차 분석)
            logger.info("📥 KcELECTRA 모델 로딩...")
            self.kcelectra_tokenizer = ElectraTokenizer.from_pretrained('beomi/KcELECTRA-base')
            self.kcelectra_model = ElectraForSequenceClassification.from_pretrained(
                'beomi/KcELECTRA-base',
                num_labels=3  # positive, negative, neutral
            )
            self.kcelectra_model.to(self.device)
            self.kcelectra_model.eval()

            logger.info("✅ 모든 모델 로딩 완료")

        except Exception as e:
            logger.error(f"❌ 모델 로딩 실패: {str(e)}")
            # 백업: 간단한 키워드 기반 분류 사용
            self.use_backup_classification = True
            logger.warning("⚠️ 백업 분류 시스템 사용")

    def classify_category(self, title: str, content: str = "") -> Dict[str, Any]:
        """
        KoBERT 기반 카테고리 분류
        Args:
            title: 뉴스 제목
            content: 뉴스 본문 (선택적)
        Returns:
            Dict: 카테고리, 신뢰도 점수
        """
        try:
            # 텍스트 전처리 (제목 + 본문 앞부분)
            text = title
            if content:
                text += " " + content[:200]  # 메모리 효율성을 위해 200자만 사용

            # KoBERT 토크나이징
            inputs = self.kobert_tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=128  # KoBERT 최적 길이
            ).to(self.device)

            # 추론
            with torch.no_grad():
                outputs = self.kobert_model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                predicted_class = torch.argmax(predictions, dim=-1).item()
                confidence = predictions[0][predicted_class].item()

            category = self.categories[predicted_class]

            # 신뢰도가 낮으면 키워드 기반 백업 사용
            if confidence < 0.6:
                backup_category = self._backup_keyword_classification(title, content)
                if backup_category:
                    category = backup_category
                    confidence = 0.7  # 백업 기본 신뢰도

            return {
                "category": category,
                "confidence": confidence,
                "method": "kobert" if confidence >= 0.6 else "keyword_backup"
            }

        except Exception as e:
            logger.error(f"❌ KoBERT 분류 실패: {str(e)}")
            # 백업 분류
            return {
                "category": self._backup_keyword_classification(title, content),
                "confidence": 0.5,
                "method": "keyword_backup"
            }

    def analyze_sentiment_pipeline(self, title: str, content: str) -> Dict[str, Any]:
        """
        2단계 감정 분석: KoBERT(1차) → KcELECTRA(2차)
        """
        try:
            # 1단계: KoBERT로 빠른 감정 스크리닝
            kobert_result = self._kobert_sentiment_screen(title, content)

            # 2단계: 감정이 명확하지 않거나 강한 경우만 KcELECTRA 정밀 분석
            if kobert_result["needs_detailed_analysis"]:
                logger.info("🔍 KcELECTRA 정밀 감정 분석 실행")
                kcelectra_result = self._kcelectra_detailed_sentiment(title, content)
                return {
                    **kcelectra_result,
                    "pipeline_method": "kobert_kcelectra",
                    "kobert_screening": kobert_result
                }
            else:
                return {
                    **kobert_result,
                    "pipeline_method": "kobert_only"
                }

        except Exception as e:
            logger.error(f"❌ 감정 분석 파이프라인 실패: {str(e)}")
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.3,
                "pipeline_method": "fallback"
            }

    def _kobert_sentiment_screen(self, title: str, content: str) -> Dict[str, Any]:
        """KoBERT 1차 감정 스크리닝 (빠른 필터링)"""
        try:
            # 간단한 키워드 기반 스크리닝
            text = (title + " " + content[:300]).lower()

            # 강한 감정 키워드 탐지
            positive_keywords = ["성공", "증가", "호조", "상승", "개선", "발전", "혁신", "획기적"]
            negative_keywords = ["실패", "감소", "하락", "악화", "문제", "위기", "충격", "논란", "분노"]
            neutral_keywords = ["발표", "계획", "예정", "진행", "개최", "참여", "관련"]

            pos_count = sum(1 for kw in positive_keywords if kw in text)
            neg_count = sum(1 for kw in negative_keywords if kw in text)
            neu_count = sum(1 for kw in neutral_keywords if kw in text)

            # 강한 감정이 감지되면 정밀 분석 필요
            needs_detailed = (pos_count >= 2 or neg_count >= 2)

            if pos_count > neg_count:
                sentiment = "positive"
                score = min(0.7, pos_count * 0.2)
            elif neg_count > pos_count:
                sentiment = "negative"
                score = max(-0.7, -neg_count * 0.2)
            else:
                sentiment = "neutral"
                score = 0.0

            return {
                "sentiment": sentiment,
                "score": score,
                "confidence": 0.6,
                "needs_detailed_analysis": needs_detailed,
                "keyword_counts": {"positive": pos_count, "negative": neg_count, "neutral": neu_count}
            }

        except Exception as e:
            logger.error(f"❌ KoBERT 감정 스크리닝 실패: {str(e)}")
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.3,
                "needs_detailed_analysis": False
            }

    def _kcelectra_detailed_sentiment(self, title: str, content: str) -> Dict[str, Any]:
        """KcELECTRA 정밀 감정 분석 (SNS 기반 학습으로 감정 표현에 민감)"""
        try:
            # 감정 분석에 중요한 부분만 추출 (제목 + 본문 앞부분)
            text = title + " " + content[:400]

            # KcELECTRA 토크나이징
            inputs = self.kcelectra_tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=256  # KcELECTRA 최적 길이
            ).to(self.device)

            # 추론
            with torch.no_grad():
                outputs = self.kcelectra_model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                predicted_class = torch.argmax(predictions, dim=-1).item()
                confidence = predictions[0][predicted_class].item()

            # 클래스 매핑 (0: negative, 1: neutral, 2: positive)
            sentiment_map = {0: "negative", 1: "neutral", 2: "positive"}
            score_map = {0: -0.8, 1: 0.0, 2: 0.8}

            sentiment = sentiment_map[predicted_class]
            score = score_map[predicted_class] * confidence

            return {
                "sentiment": sentiment,
                "score": score,
                "confidence": confidence,
                "model": "kcelectra"
            }

        except Exception as e:
            logger.error(f"❌ KcELECTRA 감정 분석 실패: {str(e)}")
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.3,
                "model": "fallback"
            }

    def _backup_keyword_classification(self, title: str, content: str = "") -> str:
        """백업 키워드 기반 분류 (기존 로직 개선)"""
        text = (title + " " + content).lower()

        # 카테고리별 키워드 가중치 (더 정밀한 분류)
        category_keywords = {
            "인공지능": {
                "high": ["ai", "인공지능", "머신러닝", "딥러닝", "neural", "신경망"],
                "medium": ["자동화", "알고리즘", "학습", "예측", "분석"]
            },
            "빅데이터": {
                "high": ["빅데이터", "데이터", "analytics", "분석", "데이터베이스"],
                "medium": ["통계", "수집", "처리", "저장", "관리"]
            },
            "클라우드": {
                "high": ["클라우드", "cloud", "aws", "azure", "gcp"],
                "medium": ["서버", "호스팅", "infra", "인프라", "네트워크"]
            },
            "로봇": {
                "high": ["로봇", "robot", "드론", "자동화", "제조"],
                "medium": ["기계", "공장", "산업", "제어", "센서"]
            },
            "블록체인": {
                "high": ["블록체인", "blockchain", "암호화폐", "비트코인", "이더리움"],
                "medium": ["crypto", "nft", "디지털", "토큰", "코인"]
            },
            "메타버스": {
                "high": ["메타버스", "metaverse", "가상현실", "vr", "ar", "증강현실"],
                "medium": ["가상", "3d", "게임", "체험", "immersive"]
            },
            "IT기업": {
                "high": ["it기업", "테크", "tech", "소프트웨어", "기업"],
                "medium": ["회사", "스타트업", "기술", "개발", "서비스"]
            },
            "스타트업": {
                "high": ["스타트업", "startup", "벤처", "투자", "펀딩"],
                "medium": ["창업", "사업", "혁신", "신생", "초기"]
            },
            "AI서비스": {
                "high": ["ai서비스", "플랫폼", "서비스", "솔루션", "도구"],
                "medium": ["앱", "application", "software", "시스템", "도입"]
            },
            "칼럼": {
                "high": ["칼럼", "opinion", "column", "기고", "사설"],
                "medium": ["의견", "논평", "분석", "전망", "견해"]
            }
        }

        # 카테고리별 점수 계산
        scores = {}
        for category, keywords in category_keywords.items():
            score = 0
            for word in keywords["high"]:
                score += text.count(word) * 3  # 고가중치 키워드
            for word in keywords["medium"]:
                score += text.count(word) * 1  # 중가중치 키워드
            scores[category] = score

        # 최고 점수 카테고리 반환
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        else:
            return "인공지능"  # 기본값

    def analyze_news_local(self, title: str, content: str) -> Dict[str, Any]:
        """
        통합 뉴스 분석 (OpenAI 대체)
        - 카테고리 분류 (KoBERT)
        - 감정 분석 (KoBERT + KcELECTRA)
        - 키워드 추출 (로컬 알고리즘)
        """
        try:
            logger.info(f"🤖 로컬 AI 분석 시작: {title[:30]}...")

            # 1. 카테고리 분류
            category_result = self.classify_category(title, content)

            # 2. 감정 분석 파이프라인
            sentiment_result = self.analyze_sentiment_pipeline(title, content)

            # 3. 로컬 키워드 추출
            keywords = self._extract_keywords_local(title, content)

            # 4. 중요도 계산 (로컬 알고리즘)
            importance = self._calculate_importance_local(title, content, sentiment_result)

            return {
                "category": category_result["category"],
                "category_confidence": category_result["confidence"],
                "sentiment": sentiment_result["sentiment"],
                "sentiment_score": sentiment_result["score"],
                "keywords": keywords,
                "importance": importance,
                "summary": self._generate_simple_summary(title, content),
                "analysis_method": "korean_ai_pipeline",
                "cost_saved": True
            }

        except Exception as e:
            logger.error(f"❌ 로컬 AI 분석 실패: {str(e)}")
            return {
                "error": str(e),
                "analysis_method": "fallback"
            }

    def _extract_keywords_local(self, title: str, content: str) -> List[str]:
        """로컬 키워드 추출 (TF-IDF 기반)"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            import re

            # 한국어 텍스트 전처리
            text = title + " " + content
            # 한글, 영어, 숫자만 남기기
            text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', text)

            # 불용어 정의
            stop_words = ['이', '그', '저', '것', '수', '등', '및', '또한', '하지만', '그러나', '따라서']

            # TF-IDF 벡터화
            vectorizer = TfidfVectorizer(
                max_features=10,
                stop_words=stop_words,
                ngram_range=(1, 2)
            )

            tfidf_matrix = vectorizer.fit_transform([text])
            feature_names = vectorizer.get_feature_names_out()
            tfidf_scores = tfidf_matrix.toarray()[0]

            # 상위 키워드 추출
            keyword_scores = list(zip(feature_names, tfidf_scores))
            keyword_scores.sort(key=lambda x: x[1], reverse=True)

            keywords = [kw for kw, score in keyword_scores[:8] if score > 0.1]
            return keywords

        except Exception as e:
            logger.error(f"❌ 로컬 키워드 추출 실패: {str(e)}")
            # 백업: 제목에서 명사 추출
            import re
            words = re.findall(r'[가-힣]{2,}', title)
            return words[:5]

    def _calculate_importance_local(self, title: str, content: str, sentiment_result: Dict) -> float:
        """로컬 중요도 계산"""
        importance = 5.0  # 기본값

        # 감정 강도 반영
        sentiment_score = abs(sentiment_result.get("score", 0))
        importance += sentiment_score * 2

        # 제목 길이 반영 (너무 짧거나 긴 제목은 중요도 낮음)
        title_length = len(title)
        if 10 <= title_length <= 50:
            importance += 1.0

        # 본문 길이 반영
        content_length = len(content)
        if content_length > 500:
            importance += 1.0

        # 최대값 제한
        return min(10.0, importance)

    def _generate_simple_summary(self, title: str, content: str) -> str:
        """간단한 로컬 요약 생성"""
        try:
            # 첫 2문장 추출 또는 제목 확장
            sentences = content.split('. ')
            if len(sentences) >= 2:
                return '. '.join(sentences[:2]) + '.'
            elif len(content) > 100:
                return content[:150] + '...'
            else:
                return title
        except:
            return title

# 전역 인스턴스 생성
_korean_ai_pipeline = None

def get_korean_ai_pipeline() -> KoreanAIPipeline:
    """Korean AI Pipeline 싱글톤 인스턴스 반환"""
    global _korean_ai_pipeline
    if _korean_ai_pipeline is None:
        _korean_ai_pipeline = KoreanAIPipeline()
    return _korean_ai_pipeline
