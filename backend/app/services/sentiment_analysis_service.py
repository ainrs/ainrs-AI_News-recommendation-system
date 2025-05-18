import os
from typing import Dict, Any, List, Union
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

class SentimentAnalysisService:
    def __init__(self, model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"):
        """
        감정 분석 서비스 초기화

        Args:
            model_name: 사용할 모델 이름 또는 경로
        """
        try:
            # 모델과 토크나이저 로드
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            print(f"감정 분석 모델 로드 완료: {model_name}")
        except Exception as e:
            print(f"감정 분석 모델 로드 중 오류 발생: {e}")
            self.model = None
            self.tokenizer = None
            print("더미 감정 분석 서비스를 사용합니다.")

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        텍스트의 감정을 분석합니다. 실제 모델을 통한 분석을 수행합니다.
        로컬 모델 실패 시 다양한 백업 옵션을 제공합니다.

        Args:
            text: 분석할 텍스트

        Returns:
            감정 분석 결과 (점수 및 라벨)
        """
        try:
            # 빈 텍스트 처리
            if not text:
                return {
                    "label": "NEUTRAL",
                    "score": 0.5,
                    "positive": 0.3,
                    "neutral": 0.7,
                    "negative": 0.0,
                    "source": "empty_input"
                }

        # 모델이 로드되지 않은 경우 로드 시도
        if not hasattr(self, 'model') or self.model is None:
            try:
                # 모델 로드 재시도
                model_name = "distilbert-base-uncased-finetuned-sst-2-english"
                self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
                self.model.to(self.device)
                self.model.eval()
                print(f"감정 분석 모델 로드 성공: {model_name}")
            except Exception as model_error:
                print(f"감정 분석 모델 로드 재시도 실패: {model_error}")
                # 외부 서비스 연결 시도
                return await self._fallback_sentiment_analysis(text)

        try:
            # 텍스트 토큰화
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # 모델 실행
            with torch.no_grad():
                outputs = self.model(**inputs)

            # 결과 가공
            logits = outputs.logits
            probabilities = torch.nn.functional.softmax(logits, dim=-1)
            probs = probabilities.cpu().numpy()[0]

            # SST-2 데이터셋 기준: 0 = 부정, 1 = 긍정
            # 3가지 감정으로 변환 (positive, neutral, negative)
            if len(probs) == 2:  # 이진 분류 모델
                positive = float(probs[1])
                negative = float(probs[0])
                neutral = 1.0 - (positive + negative)

                # 감정 라벨 결정
                if positive > 0.6:
                    label = "POSITIVE"
                    score = positive
                elif negative > 0.6:
                    label = "NEGATIVE"
                    score = negative
                else:
                    label = "NEUTRAL"
                    score = neutral

            else:  # 다중 분류 모델
                # 다중 감정 모델의 경우에 맞게 처리 (필요시 조정)
                positive = float(probs[2]) if len(probs) > 2 else 0.0
                neutral = float(probs[1]) if len(probs) > 1 else 0.0
                negative = float(probs[0]) if len(probs) > 0 else 0.0

                # 가장 높은 확률의 감정 선택
                max_prob = max(positive, neutral, negative)
                if max_prob == positive:
                    label = "POSITIVE"
                    score = positive
                elif max_prob == negative:
                    label = "NEGATIVE"
                    score = negative
                else:
                    label = "NEUTRAL"
                    score = neutral

            result = {
                "label": label,
                "score": float(score),
                "positive": float(positive),
                "neutral": float(neutral),
                "negative": float(negative),
                "source": "model"
            }
            # 로깅 추가
            print(f"감정 분석 완료: {result['label']}, 점수 = {result['score']}")
            return result

        except Exception as e:
            print(f"감정 분석 중 오류 발생: {e}")

            # 오류 발생 시 백업 방식 시도
            try:
                fallback_result = await self._fallback_sentiment_analysis(text)
                if fallback_result:
                    return fallback_result
            except Exception as fallback_error:
                print(f"백업 감정 분석도 실패: {fallback_error}")

            # 모든 백업 방식 실패 시 기본값 반환
            return {
                "label": "NEUTRAL",
                "score": 0.5,
                "positive": 0.0,
                "neutral": 1.0,
                "negative": 0.0,
                "error": str(e),
                "source": "error_recovery"
            }

    async def _fallback_sentiment_analysis(self, text: str) -> Dict[str, Any]:
        """
        외부 서비스나 대체 방식을 통한 감정 분석 수행 - 로컬 모델 실패 시 호출

        Args:
            text: 분석할 텍스트

        Returns:
            감정 분석 결과
        """
        # 1. 랭체인 서비스를 통한 감정 분석 시도
        try:
            from app.services.langchain_service import get_langchain_service
            lc_service = get_langchain_service()

            # 랭체인의 감정 분석 기능 호출
            sentiment_result = await lc_service.analyze_sentiment("", text)
            # 결과가 코루틴인 경우 처리
            if hasattr(sentiment_result, '__await__'):
                sentiment_result = await sentiment_result

            if isinstance(sentiment_result, dict) and "sentiment" in sentiment_result:
                sentiment_info = sentiment_result["sentiment"]
                return {
                    "label": sentiment_info.get("label", "NEUTRAL").upper(),
                    "score": sentiment_info.get("score", 0.5),
                    "positive": sentiment_info.get("positive", 0.3),
                    "neutral": sentiment_info.get("neutral", 0.5),
                    "negative": sentiment_info.get("negative", 0.2),
                    "source": "langchain"
                }
        except Exception as lc_error:
            print(f"랭체인 감정 분석 시도 실패: {lc_error}")

        # 2. 임베딩 서비스를 통한 분석 시도
        try:
            from app.services.embedding_service import get_embedding_service
            emb_service = get_embedding_service()

            # 감정 분석 특화 임베딩 생성
            embedding = await emb_service.get_embedding(text, task_type="sentiment")

            # 임베딩 기반 간단한 감정 분석 (임베딩 차원의 첫 부분이 감정 정보를 가지고 있다고 가정)
            # 이것은 실제로는 매우 단순한 방식이며, 제대로 된 구현은 더 복잡할 수 있음
            if embedding and len(embedding) > 10:
                # 임베딩의 첫 몇 차원 사용
                sentiment_score = sum(embedding[:5]) / 5  # 첫 5개 차원의 평균
                sentiment_score = (sentiment_score + 1) / 2  # -1~1 범위를 0~1로 변환

                if sentiment_score > 0.6:
                    label = "POSITIVE"
                    positive = sentiment_score
                    negative = 0.1
                    neutral = 1.0 - positive - negative
                elif sentiment_score < 0.4:
                    label = "NEGATIVE"
                    negative = 1.0 - sentiment_score
                    positive = 0.1
                    neutral = 1.0 - positive - negative
                else:
                    label = "NEUTRAL"
                    neutral = 0.6
                    positive = 0.2
                    negative = 0.2

                return {
                    "label": label,
                    "score": sentiment_score,
                    "positive": positive,
                    "neutral": neutral,
                    "negative": negative,
                    "source": "embedding"
                }
        except Exception as emb_error:
            print(f"임베딩 기반 감정 분석 시도 실패: {emb_error}")

        # 3. 규칙 기반 감정 분석 (최후의 방법)
        try:
            # 간단한 키워드 기반 감정 분석
            positive_words = [
                "좋은", "훌륭한", "멋진", "행복", "기쁨", "즐거움", "만족", "성공",
                "발전", "혁신", "좋아", "좋다", "좋았", "희망", "긍정"
            ]
            negative_words = [
                "나쁜", "슬픈", "화난", "분노", "실망", "좌절", "우울", "실패",
                "하락", "어려움", "문제", "싫어", "싫다", "걱정", "부정"
            ]

            # 단어 빈도 계산
            positive_count = sum(text.lower().count(word) for word in positive_words)
            negative_count = sum(text.lower().count(word) for word in negative_words)
            total = max(1, positive_count + negative_count)

            # 감정 점수 및 레이블 결정
            if positive_count > negative_count * 2:
                label = "POSITIVE"
                score = 0.7 + (positive_count / total) * 0.3
                positive = score
                negative = 0.1
                neutral = 1.0 - positive - negative
            elif negative_count > positive_count * 2:
                label = "NEGATIVE"
                score = 0.3 - (negative_count / total) * 0.3
                negative = 1.0 - score
                positive = 0.1
                neutral = 1.0 - positive - negative
            else:
                label = "NEUTRAL"
                score = 0.5 + (positive_count - negative_count) / (total * 4)
                neutral = 0.7
                positive = 0.2 * (1 + (positive_count / total))
                negative = 1.0 - neutral - positive

            return {
                "label": label,
                "score": score,
                "positive": positive,
                "neutral": neutral,
                "negative": negative,
                "source": "rule_based"
            }
        except Exception as rule_error:
            print(f"규칙 기반 감정 분석 실패: {rule_error}")

        # 모든 방법 실패 시 None 반환
        return None

# 서비스 인스턴스를 가져오는 헬퍼 함수
_sentiment_analysis_service = None

def get_sentiment_analysis_service() -> SentimentAnalysisService:
    """
    SentimentAnalysisService 인스턴스를 가져옵니다. (싱글톤 패턴)
    """
    global _sentiment_analysis_service
    if _sentiment_analysis_service is None:
        _sentiment_analysis_service = SentimentAnalysisService()
    return _sentiment_analysis_service
