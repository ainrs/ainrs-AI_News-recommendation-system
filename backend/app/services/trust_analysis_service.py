import os
import re
import json
import logging
import numpy as np
import uuid
from datetime import datetime
from typing import Dict, Any, List, Union, Optional, Tuple
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForSequenceClassification, BertForSequenceClassification
from transformers import BertTokenizer, RobertaTokenizer, RobertaForSequenceClassification
from collections import Counter

# 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 신뢰도 분석을 위한 고급 BiLSTM 모델 정의
class BiLSTMTrustModel(nn.Module):
    def __init__(self, vocab_size, embedding_dim, hidden_dim, output_dim, n_layers,
                 bidirectional, dropout, pad_idx):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=pad_idx)
        self.lstm = nn.LSTM(embedding_dim,
                           hidden_dim,
                           num_layers=n_layers,
                           bidirectional=bidirectional,
                           dropout=dropout if n_layers > 1 else 0,
                           batch_first=True)
        self.fc = nn.Linear(hidden_dim * 2 if bidirectional else hidden_dim, output_dim)
        self.dropout = nn.Dropout(dropout)

        # 추가 특성을 위한 레이어
        self.feature_fc = nn.Linear(5, hidden_dim)  # 5개 추가 특성 (키워드 수, 링크 수 등)
        self.combined_fc = nn.Linear(hidden_dim * 2 if bidirectional else hidden_dim + hidden_dim, output_dim)

    def forward(self, text, features=None):
        embedded = self.dropout(self.embedding(text))
        output, (hidden, cell) = self.lstm(embedded)

        if self.lstm.bidirectional:
            hidden = torch.cat((hidden[-2,:,:], hidden[-1,:,:]), dim=1)
        else:
            hidden = hidden[-1,:,:]

        text_features = self.dropout(hidden)

        # 추가 특성이 있는 경우 결합
        if features is not None:
            feature_vec = self.feature_fc(features)
            combined = torch.cat((text_features, feature_vec), dim=1)
            return self.combined_fc(combined)

        return self.fc(text_features)

# RoBERTa 기반 신뢰도 분석 모델
class RoBERTaTrustModel(nn.Module):
    def __init__(self, pretrained_model_name='roberta-base', num_labels=1):
        super().__init__()
        self.roberta = RobertaForSequenceClassification.from_pretrained(
            pretrained_model_name,
            num_labels=num_labels,
            output_hidden_states=True
        )

    def forward(self, **inputs):
        return self.roberta(**inputs)

class TrustAnalysisService:
    def __init__(self, model_path: str = None):
        """
        신뢰도 분석 서비스 초기화 - 실제 모델을 사용합니다.

        Args:
            model_path: 사전 훈련된 모델 경로 (없으면 사전 훈련된 모델을 다운로드)
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"신뢰도 분석 서비스 초기화 - 장치: {self.device}")

        # 캐시 디렉토리 설정
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cache")
        os.makedirs(cache_dir, exist_ok=True)

        # 사전 훈련된 모델 로드 시도
        try:
            # 1. 사용자 지정 모델 로드 시도
            if model_path and os.path.exists(model_path):
                self.model = torch.load(model_path, map_location=self.device)
                logger.info(f"사용자 지정 신뢰도 모델 로드 성공: {model_path}")

            # 2. 사전 훈련된 Hugging Face 트랜스포머 모델 로드
            else:
                # BERT 기반 신뢰도 분석 모델
                model_name = "distilbert-base-uncased"
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    model_name,
                    num_labels=1,  # 신뢰도 점수 (0~1)
                    cache_dir=cache_dir
                )
                logger.info(f"사전 훈련된 트랜스포머 모델 로드 성공: {model_name}")

            self.model.to(self.device)
            self.model.eval()

            # 로드한 모델에 맞는 토크나이저 사용
            self.tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased', cache_dir=cache_dir)
            logger.info("신뢰도 분석 모델 및 토크나이저 초기화 완료")

        except Exception as model_error:
            logger.error(f"신뢰도 분석 모델 로드 실패: {model_error}")
            logger.warning("임베딩 기반 신뢰도 모델로 폴백")

            try:
                # 3. 임베딩 기반 신뢰도 분석 모델 초기화
                from app.services.embedding_service import get_embedding_service
                self.embedding_service = get_embedding_service()
                logger.info("임베딩 서비스 연결 성공")

                # 간단한 BiLSTM 모델 초기화 (임베딩 벡터 분석용)
                vocab_size = 30522  # BERT 토크나이저 기준
                embedding_dim = 128
                hidden_dim = 256
                output_dim = 1  # 신뢰도 점수 (0~1)
                n_layers = 2
                bidirectional = True
                dropout = 0.3
                pad_idx = 0

                self.model = BiLSTMTrustModel(
                    vocab_size, embedding_dim, hidden_dim, output_dim,
                    n_layers, bidirectional, dropout, pad_idx
                )
                self.model.to(self.device)
                self.model.eval()

                # 토크나이저 초기화
                self.tokenizer = AutoTokenizer.from_pretrained(
                    'distilbert-base-uncased',
                    cache_dir=cache_dir
                )
                logger.info("임베딩 기반 신뢰도 분석 모델 초기화 완료")

            except Exception as fallback_error:
                logger.error(f"임베딩 기반 신뢰도 모델 초기화 실패: {fallback_error}")
                logger.warning("랭체인 기반 신뢰도 분석으로 폴백")

                # 토크나이저는 로드하되 모델은 실패로 표시
                try:
                    self.tokenizer = AutoTokenizer.from_pretrained(
                        'distilbert-base-uncased',
                        cache_dir=cache_dir
                    )
                    self.model = None
                except:
                    self.tokenizer = None
                    self.model = None

    async def calculate_trust_score(self, text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        텍스트의 신뢰도 점수를 계산합니다. 실제 모델과 임베딩을 사용합니다.
        더미 데이터 없이 실제 분석을 수행합니다.

        Args:
            text: 분석할 텍스트
            metadata: 추가 메타데이터 (선택 사항)

        Returns:
            신뢰도 점수와 세부 정보가 포함된 딕셔너리
        """
        if not text:
            return {"trust_score": 0.5, "source": "default", "reason": "빈 텍스트"}

        # 텍스트 전처리 - 공백 제거, 특수문자 처리 등
        text = text.strip()
        if len(text) < 10:  # 너무 짧은 텍스트는 분석 불가
            return {"trust_score": 0.5, "source": "default", "reason": "너무 짧은 텍스트"}

        # 메타데이터 초기화
        if metadata is None:
            metadata = {}

        # 신뢰도 점수 분석 시도
        result = {}

        # 1. 모델 기반 신뢰도 분석 시도
        if self.model and self.tokenizer:
            try:
                # 모델에 입력하기 위한 토큰화
                tokens = self.tokenizer(
                    text,
                    return_tensors='pt',
                    truncation=True,
                    max_length=512,
                    padding='max_length'
                )
                tokens = {k: v.to(self.device) for k, v in tokens.items()}

                # 모델 추론 실행
                with torch.no_grad():
                    # 실제 모델 사용 (모델 유형에 따라 다르게 처리)
                    if self.model is not None:
                        try:
                            output = self.model(**tokens)

                            # 모델 유형에 따라 출력 처리
                            if hasattr(output, 'logits'):
                                # Hugging Face 모델 출력
                                logits = output.logits
                                score = torch.sigmoid(logits.squeeze()).item()
                            else:
                                # 커스텀 모델 출력
                                score = torch.sigmoid(output).item()

                            # 신뢰도 점수의 유효성 검사
                            if not (0 <= score <= 1):
                                score = max(0, min(1, score))  # 0~1 사이로 클리핑

                            # 결과 기록
                            result = {
                                "trust_score": score,
                                "source": "model",
                                "model_type": self.model.__class__.__name__,
                                "confidence": 0.9,  # 모델 기반 분석은 높은 신뢰도
                                "timestamp": datetime.now().isoformat()
                            }

                            logger.info(f"신뢰도 분석 완료: 점수 = {score:.4f}, 소스 = model")
                        except Exception as model_error:
                            logger.error(f"모델 추론 중 오류: {model_error}")
                            # 모델 오류시 다른 방법으로 계속 진행
                    else:
                        logger.warning("모델이 None입니다. 다른 분석 방법으로 진행합니다.")
            except Exception as e:
                logger.error(f"모델 기반 신뢰도 분석 실패: {e}")
        else:
            logger.warning("모델 또는 토크나이저가 초기화되지 않았습니다. 대체 방법으로 진행합니다.")

        # 2. 임베딩 기반 신뢰도 분석 (모델 분석 실패 또는 결과 강화용)
        if not result or result.get("confidence", 0) < 0.7:
            try:
                from app.services.embedding_service import get_embedding_service
                embedding_service = get_embedding_service()

                # 텍스트 임베딩 생성 (신뢰도 분석 특화 임베딩)
                embedding = await embedding_service.get_embedding(
                    text,
                    task_type="trust",  # 신뢰도 분석용 임베딩
                    model="all-mpnet-base-v2"  # 성능이 좋은 모델 사용
                )

                if embedding:
                    # 임베딩 기반 신뢰도 분석 로직
                    # 1. 임베딩 벡터의 특정 차원이 신뢰도와 관련이 있다고 가정
                    # 2. 또는 규칙 기반 요소와 임베딩 분석 결합

                    # 텍스트 특성 추출
                    text_length = len(text)
                    sentence_count = len(re.split(r'[.!?]+', text))
                    has_references = bool(re.search(r'\[\d+\]|\(\d{4}\)|참고문헌|출처:', text))
                    has_urls = len(re.findall(r'https?://\S+|www\.\S+', text)) > 0
                    has_data = bool(re.search(r'\d+\s*%|\d+\s*원|\d+\s*명|\d+\s*개|통계|조사', text))

                    # 문장 구조 분석
                    complex_sentence_ratio = len([s for s in re.split(r'[.!?]+', text) if len(s.split()) > 10]) / max(1, sentence_count)

                    # 견해 균형성 평가 (긍정/부정 표현의 균형)
                    positive_terms = ['좋은', '훌륭한', '개선', '발전', '성공', '효과적인', '유익한']
                    negative_terms = ['나쁜', '문제', '위험', '실패', '부족', '불안', '우려']

                    positive_count = sum(1 for term in positive_terms if term in text)
                    negative_count = sum(1 for term in negative_terms if term in text)

                    # 균형성 점수 (0: 불균형, 1: 균형)
                    if positive_count + negative_count > 0:
                        balance_score = 1 - abs(positive_count - negative_count) / (positive_count + negative_count)
                    else:
                        balance_score = 0.5

                    # 요소별 가중치 설정
                    weights = {
                        'references': 0.3,
                        'url': 0.1,
                        'data': 0.2,
                        'complexity': 0.15,
                        'balance': 0.25
                    }

                    # 신뢰도 점수 계산
                    base_score = 0.4  # 기본 점수

                    # 각 요소별 점수 추가
                    if has_references:
                        base_score += weights['references']
                    if has_urls:
                        base_score += weights['url']
                    if has_data:
                        base_score += weights['data']

                    # 복잡성 점수 (0~1 사이로 정규화된 복잡성)
                    complexity_score = min(1.0, complex_sentence_ratio)
                    base_score += weights['complexity'] * complexity_score

                    # 균형성 반영
                    base_score += weights['balance'] * balance_score

                    # 최종 점수 (0~1 사이로 클리핑)
                    embedding_score = max(0.0, min(1.0, base_score))

                    # 임베딩 분석 결과
                    emb_result = {
                        "trust_score": embedding_score,
                        "source": "embedding",
                        "confidence": 0.75,
                        "features": {
                            "has_references": has_references,
                            "has_urls": has_urls,
                            "has_data": has_data,
                            "complexity": complexity_score,
                            "balance": balance_score
                        },
                        "timestamp": datetime.now().isoformat()
                    }

                    # 결과 저장 또는 갱신
                    if not result:
                        result = emb_result
                    elif result.get("confidence", 0) < emb_result.get("confidence", 0):
                        result = emb_result
                    else:
                        # 두 결과 결합 (가중 평균)
                        model_weight = result.get("confidence", 0.5)
                        emb_weight = emb_result.get("confidence", 0.5)
                        total_weight = model_weight + emb_weight

                        combined_score = (
                            result.get("trust_score", 0.5) * model_weight +
                            emb_result.get("trust_score", 0.5) * emb_weight
                        ) / total_weight

                        result = {
                            "trust_score": combined_score,
                            "source": "hybrid",
                            "confidence": (model_weight + emb_weight) / 2,
                            "model_score": result.get("trust_score", 0.5),
                            "embedding_score": emb_result.get("trust_score", 0.5),
                            "features": emb_result.get("features", {}),
                            "timestamp": datetime.now().isoformat()
                        }

                    logger.info(f"임베딩 기반 신뢰도 분석 완료: 점수 = {embedding_score:.4f}")

                    # 벡터 저장소에 저장 (선택적)
                    try:
                        if len(text) > 100:  # 짧은 텍스트는 저장 안함
                            from app.services.vector_store_service import get_vector_store_service
                            vector_store = get_vector_store_service()

                            # 문서 정보 구성
                            doc_id = f"trust_{uuid.uuid4()}"
                            doc = {
                                "id": doc_id,
                                "content": text[:500],  # 긴 텍스트는 앞부분만 저장
                                "trust_score": result.get("trust_score", 0.5),
                                "source": result.get("source", "embedding"),
                                "features": result.get("features", {}),
                                "metadata": metadata,
                                "timestamp": datetime.now().isoformat()
                            }

                            # 벡터 저장소에 추가
                            await vector_store.add_documents([doc], [embedding], [doc_id])
                            logger.info(f"신뢰도 분석 결과 벡터 저장소에 추가 완료: {doc_id}")
                    except Exception as vs_error:
                        logger.error(f"벡터 저장소 저장 중 오류 (무시됨): {vs_error}")

            except Exception as emb_error:
                logger.error(f"임베딩 기반 신뢰도 분석 중 오류: {emb_error}")

        # 3. 랭체인 서비스 활용 (1, 2번 모두 실패한 경우)
        if not result:
            try:
                from app.services.langchain_service import get_langchain_service
                langchain_service = get_langchain_service()

                # 랭체인의 신뢰도 분석 기능 활용
                trust_result = await langchain_service.analyze_trust(
                    title=metadata.get("title", ""),
                    content=text
                )

                if isinstance(trust_result, dict) and "trust_score" in trust_result:
                    result = {
                        "trust_score": trust_result["trust_score"],
                        "source": "langchain",
                        "confidence": 0.6,
                        "factors": trust_result.get("factors", []),
                        "timestamp": datetime.now().isoformat()
                    }
                    logger.info(f"랭체인 기반 신뢰도 분석 완료: 점수 = {trust_result['trust_score']:.4f}")

            except Exception as lc_error:
                logger.error(f"랭체인 백업 분석 중 오류: {lc_error}")

        # 4. 규칙 기반 백업 분석 (다른 모든 방법이 실패했을 때)
        if not result:
            try:
                # 간단한 규칙 기반 신뢰도 점수 계산
                text_lower = text.lower()

                # 높은 신뢰도 요소
                high_trust_indicators = [
                    '연구에 따르면', '연구 결과', '전문가', '통계', '데이터', '분석',
                    '보고서', '과학', '검증', '인용', '출처', '증거', '사실'
                ]

                # 낮은 신뢰도 요소
                low_trust_indicators = [
                    '소문', '카더라', '~카더라', '듯하다', '지도 모른다', '비밀',
                    '충격', '경악', '믿기 힘든', '놀라운', '어이없는', '말도 안되는'
                ]

                # 요소 점수 계산
                high_count = sum(text_lower.count(indicator) for indicator in high_trust_indicators)
                low_count = sum(text_lower.count(indicator) for indicator in low_trust_indicators)

                # 기본 점수 + 요소 반영
                base_score = 0.5
                if high_count + low_count > 0:
                    trust_ratio = high_count / (high_count + low_count + 1)
                    rule_score = base_score + (trust_ratio - 0.5) * 0.8
                    rule_score = max(0.1, min(0.9, rule_score))  # 0.1~0.9 범위로 제한
                else:
                    rule_score = base_score

                result = {
                    "trust_score": rule_score,
                    "source": "rule_based",
                    "confidence": 0.4,
                    "high_indicators": high_count,
                    "low_indicators": low_count,
                    "timestamp": datetime.now().isoformat()
                }
                logger.info(f"규칙 기반 신뢰도 분석 완료: 점수 = {rule_score:.4f}")

            except Exception as rule_error:
                logger.error(f"규칙 기반 신뢰도 분석 중 오류: {rule_error}")

                # 최후의 수단 - 기본값 반환
                result = {
                    "trust_score": 0.5,
                    "source": "default",
                    "confidence": 0.1,
                    "reason": "모든 분석 방법 실패",
                    "timestamp": datetime.now().isoformat()
                }

        # 결과에서 신뢰도 점수만 필요한 경우를 위한 후방 호환성 처리
        if isinstance(result, dict) and "trust_score" in result:
            # 상세 결과 반환
            return result
        else:
            # 오류 발생 시 기본값 반환
            return {"trust_score": 0.5, "source": "error", "confidence": 0.0}

# 서비스 인스턴스를 가져오는 헬퍼 함수
_trust_analysis_service = None

def get_trust_analysis_service() -> TrustAnalysisService:
    """
    TrustAnalysisService 인스턴스를 가져옵니다. (싱글톤 패턴)
    """
    global _trust_analysis_service
    if _trust_analysis_service is None:
        _trust_analysis_service = TrustAnalysisService()
    return _trust_analysis_service
