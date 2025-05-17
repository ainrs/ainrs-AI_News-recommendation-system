import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import json

# LangChain imports
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# OpenAI imports
from openai import OpenAI

# Models
from app.models.news import NewsInDB
from app.models.embedding import (
    EmbeddingResult,
    TrustAnalysisResult,
    SentimentAnalysisResult
)

# MongoDB
from app.db.mongodb import (
    news_collection,
    embeddings_collection,
    metadata_collection
)

# Services
from app.services.trust_analysis_service import get_trust_analysis_service
from app.services.sentiment_analysis_service import get_sentiment_analysis_service
from app.services.vector_store_service import get_vector_store_service

# Config
from app.core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


class EmbeddingService:
    """Service for generating and managing embeddings for news articles"""

    def __init__(self):
        # 다양한 임베딩 모델 초기화 - 뉴스 및 문맥 최적화
        # 1. 기본 OpenAI 임베딩
        self.openai_embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.OPENAI_API_KEY
        )

        # 2. 뉴스 특화 임베딩 모델 (사용 가능한 경우)
        self.specialized_embeddings = {}

        # 뉴스 특화 임베딩 초기화 시도
        try:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                # sentence-transformers가 없을 경우 자동 설치 시도
                logger.info("sentence-transformers 패키지를 설치 중입니다...")
                import subprocess
                import sys
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers"])
                    logger.info("✅ sentence-transformers 설치 완료. 모델 로딩을 계속합니다.")
                    from sentence_transformers import SentenceTransformer
                except Exception as e:
                    logger.error(f"sentence-transformers 설치 실패: {str(e)}")
                    raise ImportError("sentence-transformers 설치 실패")

            # 한국어 뉴스 텍스트에 특화된 모델
            logger.info("특화 임베딩 모델 로딩 중... (한국어)")
            self.specialized_embeddings["news-ko"] = SentenceTransformer("jhgan/ko-sroberta-multitask")
            logger.info("✅ 한국어 임베딩 모델 로드 성공")

            # 다국어 뉴스 텍스트에 특화된 모델
            logger.info("특화 임베딩 모델 로딩 중... (다국어)")
            self.specialized_embeddings["multilingual"] = SentenceTransformer("sentence-transformers/distiluse-base-multilingual-cased-v1")
            logger.info("✅ 다국어 임베딩 모델 로드 성공")

            # 감정분석에 특화된 임베딩
            logger.info("특화 임베딩 모델 로딩 중... (감정분석)")
            self.specialized_embeddings["sentiment"] = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
            logger.info("✅ 감정분석 임베딩 모델 로드 성공")

            logger.info("✅ 특화 임베딩 모델 초기화 성공")
        except ImportError:
            logger.warning("⚠️ sentence-transformers 패키지를 찾을 수 없습니다. 기본 OpenAI 임베딩만 사용합니다.")
        except Exception as e:
            logger.error(f"특화 임베딩 모델 초기화 중 오류: {str(e)}")

        # 3. 텍스트 스플리터 설정 - 뉴스 기사 구조에 최적화
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )

        # 뉴스 기사용 특수 스플리터 - 헤드라인, 본문, 인용구 등을 고려
        self.news_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=300,
            separators=["\n\n", "\n", ". ", ".\n", "! ", "? ", ".\n\n"]
        )

        # 벡터 저장소 설정
        # Create Chroma directory if it doesn't exist
        self.chroma_dir = os.path.join(settings.DATA_DIR, "chroma")
        os.makedirs(self.chroma_dir, exist_ok=True)

        # FAISS 벡터 저장소 디렉토리 설정 (고성능 벡터 검색)
        self.faiss_dir = os.path.join(settings.DATA_DIR, "faiss")
        os.makedirs(self.faiss_dir, exist_ok=True)

        # Initialize services
        self.trust_analysis_service = get_trust_analysis_service()
        self.sentiment_analysis_service = get_sentiment_analysis_service()
        self.vector_store_service = get_vector_store_service()

        # 다양한 벡터 저장소 초기화
        # Chroma DB (기본)
        self.vectorstore = None
        # FAISS (고성능 벡터 검색)
        self.faiss_vectorstore = None

        # 임베딩 모델 선택 전략 설정
        self.embedding_strategy = self._get_embedding_strategy()

    def _get_embedding_strategy(self):
        """
        사용 가능한 임베딩 모델과 작업 유형에 따른 최적의 모델 선택 전략을 반환합니다.
        """
        # 기본값으로 OpenAI 임베딩 사용
        strategy = {
            "default": self.openai_embeddings,
            "sentiment": self.openai_embeddings,
            "news": self.openai_embeddings,
            "recommendation": self.openai_embeddings,
            "search": self.openai_embeddings,
        }

        # 특화 모델이 있으면 작업별로 최적 모델 할당
        if self.specialized_embeddings:
            # 한국어 뉴스 분석 특화 모델
            if "news-ko" in self.specialized_embeddings:
                strategy["news"] = self.specialized_embeddings["news-ko"]
                logger.info("뉴스 임베딩에 한국어 특화 모델 사용")

            # 감정 분석에 특화된 모델
            if "sentiment" in self.specialized_embeddings:
                strategy["sentiment"] = self.specialized_embeddings["sentiment"]
                logger.info("감정 분석에 특화 임베딩 모델 사용")

            # 다국어 지원 모델 (검색 및 추천에 활용)
            if "multilingual" in self.specialized_embeddings:
                strategy["search"] = self.specialized_embeddings["multilingual"]
                strategy["recommendation"] = self.specialized_embeddings["multilingual"]
                logger.info("검색 및 추천에 다국어 임베딩 모델 사용")

        return strategy

    def get_vectorstore(self):
        """Get or create the vector store"""
        if self.vectorstore is None:
            self.vectorstore = Chroma(
                collection_name="news_embeddings",
                embedding_function=self.openai_embeddings,
                persist_directory=self.chroma_dir
            )
        return self.vectorstore

    def get_embedding_with_model(self, text: str, model_name: str = "default") -> List[float]:
        """
        특정 모델을 지정하여 텍스트의 임베딩을 가져옵니다.

        Args:
            text: 임베딩할 텍스트
            model_name: 사용할 모델 이름 ("default", "news-ko", "multilingual", "sentiment" 등)

        Returns:
            임베딩 벡터
        """
        if not text:
            logger.warning("임베딩할 텍스트가 비어 있습니다.")
            # 기본 임베딩 차원과 동일한 제로 벡터 반환
            return [0.0] * 1536

        # 텍스트 전처리
        text = self._preprocess_text(text)

        try:
            # 지정된 모델 가져오기
            if model_name in self.specialized_embeddings:
                model = self.specialized_embeddings[model_name]
                # SentenceTransformer 모델 사용
                embedding = model.encode(text).tolist()
                return embedding
            else:
                # 모델이 없으면 기본 OpenAI 임베딩 사용
                logger.info(f"지정된 모델 {model_name}을 찾을 수 없어 기본 임베딩 사용")
                return self.openai_embeddings.embed_query(text)
        except Exception as e:
            logger.error(f"임베딩 생성 중 오류 (모델 {model_name}): {str(e)}")
            # 오류 시 기본 OpenAI 임베딩 시도
            return self.openai_embeddings.embed_query(text)

    def get_embedding(self, text: str, task_type: str = "default", fallback: bool = True) -> List[float]:
        """
        단일 텍스트에 대한 임베딩을 가져옵니다.
        작업 유형에 따라 최적화된 임베딩 모델을 선택합니다.

        Args:
            text: 임베딩할 텍스트
            task_type: 임베딩 사용 목적 ("default", "news", "sentiment", "recommendation", "search" 중 하나)
            fallback: 오류 발생 시 대체 임베딩 모델 사용 여부

        Returns:
            임베딩 벡터
        """
        if not text:
            logger.warning("임베딩할 텍스트가 비어 있습니다.")
            # 기본 임베딩 차원과 동일한 제로 벡터 반환
            return [0.0] * 1536

        # 텍스트 전처리 - 특수문자 필터링 및 길이 제한
        text = self._preprocess_text(text)

        # 작업 유형에 따른 최적 임베딩 모델 선택
        model = self.embedding_strategy.get(task_type, self.embedding_strategy["default"])

        try:
            # 선택된 모델로 임베딩 생성
            if isinstance(model, OpenAIEmbeddings):
                # OpenAI 임베딩은 embed_query 메서드 사용
                embedding = model.embed_query(text)
            else:
                # SentenceTransformer 모델은 encode 메서드 사용
                # numpy 배열을 Python 리스트로 변환
                embedding = model.encode(text).tolist()

            # 임베딩 결과 검증
            if not embedding or len(embedding) < 10:  # 최소 차원 검증
                raise ValueError("생성된 임베딩이 유효하지 않습니다.")

            return embedding

        except Exception as primary_error:
            logger.error(f"{task_type} 임베딩 생성 중 오류 발생: {primary_error}")

            # 실패한 경우 fallback이 활성화되어 있으면 다른 모델 시도
            if fallback and model != self.openai_embeddings:
                logger.info(f"대체 임베딩 모델(OpenAI)로 재시도합니다.")
                try:
                    return self.openai_embeddings.embed_query(text)
                except Exception as fallback_error:
                    logger.error(f"대체 임베딩 모델도 실패: {fallback_error}")

            # 임베딩 실패 시 캐시된 임베딩 조회 시도
            cached_embedding = self._get_cached_embedding_for_similar_text(text)
            if cached_embedding:
                logger.info("유사 텍스트의 캐시된 임베딩을 사용합니다.")
                return cached_embedding

            # 최후의 수단: 제로 벡터 대신 랜덤 임베딩 생성
            # (완전한 제로 벡터는 코사인 유사도 계산 시 문제 발생)
            import numpy as np
            logger.warning("임시 랜덤 임베딩을 생성합니다.")
            random_embedding = np.random.normal(0, 0.01, 1536).tolist()
            return random_embedding

    def _preprocess_text(self, text: str) -> str:
        """
        임베딩 생성을 위한 텍스트 전처리를 수행합니다.

        Args:
            text: 원본 텍스트

        Returns:
            str: 전처리된 텍스트
        """
        if not isinstance(text, str):
            # 문자열이 아닌 경우 문자열로 변환
            text = str(text)

        # 텍스트 길이 제한
        if len(text) > 8000:
            text = text[:8000]

        # 불필요한 공백 정리
        text = ' '.join(text.split())

        # HTML 태그 제거 (간단한 방식)
        import re
        text = re.sub(r'<[^>]+>', ' ', text)

        # 특수 URL 인코딩 문자 정리
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')

        return text

    def _get_cached_embedding_for_similar_text(self, text: str) -> List[float]:
        """
        유사한 텍스트의 캐시된 임베딩을 조회합니다.

        Args:
            text: 임베딩이 필요한 텍스트

        Returns:
            List[float]: 캐시된 임베딩 벡터 또는 빈 리스트
        """
        try:
            # 간단한 해시 기반 캐싱 구현
            # 실제 구현에서는 더 정교한 방식 필요 (텍스트 유사도 기반)
            from app.db.mongodb import embeddings_collection

            # 텍스트에서 주요 키워드 추출 (간단한 방식)
            words = text.lower().split()
            keywords = [w for w in words if len(w) > 5][:10]  # 긴 단어 10개 선택

            if not keywords:
                return []

            # 키워드 기반 유사 임베딩 쿼리
            keyword_query = {"$or": [{"text_sample": {"$regex": kw}} for kw in keywords]}
            cached_embedding = embeddings_collection.find_one(keyword_query)

            if cached_embedding and "embedding" in cached_embedding:
                return cached_embedding["embedding"]

        except Exception as e:
            logger.error(f"캐시된 임베딩 조회 중 오류: {e}")

        return []

    def create_embeddings_for_news(self, news_id: str) -> Optional[EmbeddingResult]:
        """Create embeddings for a news article"""
        # Get news article from MongoDB
        news = news_collection.find_one({"_id": news_id})
        if not news:
            logger.error(f"News article with id {news_id} not found")
            return None

        # Create embeddings
        try:
            # Combine title and content
            news_text = f"{news['title']} {news['content']}"

            # Get embeddings using OpenAI
            embedding_vector = self.openai_embeddings.embed_query(news_text)

            # Create document for Chroma
            doc = Document(
                page_content=news_text,
                metadata={
                    "news_id": news_id,
                    "title": news["title"],
                    "source": news["source"],
                    "published_date": news["published_date"],
                    "url": news["url"]
                }
            )

            # Add to vectorstore (Langchain)
            vectorstore = self.get_vectorstore()
            vectorstore.add_documents([doc])
            vectorstore.persist()

            # 벡터 저장소 서비스에도 추가
            try:
                document = {
                    "id": news_id,
                    "title": news["title"],
                    "content": news["content"],
                    "source": news["source"],
                    "published_date": news["published_date"].isoformat() if "published_date" in news else None,
                    "url": news["url"]
                }
                self.vector_store_service.add_documents(
                    documents=[document],
                    embeddings=[embedding_vector],
                    ids=[news_id]
                )
            except Exception as vs_error:
                logger.error(f"벡터 저장소 서비스에 문서 추가 중 오류: {vs_error}")

            # Create embedding result
            result = EmbeddingResult(
                news_id=news_id,
                embedding=embedding_vector,
                model_name="text-embedding-3-small",
                created_at=datetime.utcnow(),
                metadata={
                    "title": news["title"],
                    "source": news["source"]
                }
            )

            # Save to MongoDB
            embedding_id = str(uuid.uuid4())
            embedding_data = result.model_dump()
            embedding_data["_id"] = embedding_id

            embeddings_collection.insert_one(embedding_data)

            # Update news record with embedding_id
            news_collection.update_one(
                {"_id": news_id},
                {"$set": {
                    "embedding_id": embedding_id,
                    "updated_at": datetime.utcnow()
                }}
            )

            return result

        except Exception as e:
            logger.error(f"Error creating embeddings for news {news_id}: {e}")
            return None

    async def perform_trust_analysis(self, news_id: str) -> Optional[TrustAnalysisResult]:
        """Perform trust analysis on a news article using BiLSTM"""
        # Get news article from MongoDB
        news = news_collection.find_one({"_id": news_id})
        if not news:
            logger.error(f"News article with id {news_id} not found")
            return None

        try:
            # Extract relevant text
            title = news["title"]
            content = news["content"]

            # 텍스트 결합
            news_text = f"{title} {content}"

            # BiLSTM 모델을 사용한 신뢰도 분석
            trust_score = await self.trust_analysis_service.calculate_trust_score(news_text)

            # Create result
            result = TrustAnalysisResult(
                news_id=news_id,
                trust_score=trust_score,
                model_name="bilstm-trust-analysis",
                created_at=datetime.utcnow(),
                metadata={
                    "title": news["title"],
                    "source": news["source"]
                }
            )

            # Update news record with trust score
            news_collection.update_one(
                {"_id": news_id},
                {"$set": {
                    "trust_score": trust_score,
                    "updated_at": datetime.utcnow()
                }}
            )

            return result

        except Exception as e:
            logger.error(f"Error performing trust analysis for news {news_id}: {e}")
            return None

    async def perform_sentiment_analysis(self, news_id: str) -> Optional[SentimentAnalysisResult]:
        """Perform sentiment analysis on a news article using Sentiment BERT"""
        # Get news article from MongoDB
        news = news_collection.find_one({"_id": news_id})
        if not news:
            logger.error(f"News article with id {news_id} not found")
            return None

        try:
            # Extract relevant text
            title = news["title"]
            content = news["content"]

            # 텍스트 결합
            news_text = f"{title} {content}"

            # Sentiment BERT 모델을 사용한 감정 분석
            sentiment_result = await self.sentiment_analysis_service.analyze_sentiment(news_text)

            # 결과 추출
            sentiment_score = sentiment_result.get("score", 0.5)
            sentiment_label = sentiment_result.get("label", "NEUTRAL").lower()

            # 양극성 점수로 변환 (-1 ~ 1)
            if sentiment_label == "positive":
                polarity_score = sentiment_score
            elif sentiment_label == "negative":
                polarity_score = -sentiment_score
            else:
                polarity_score = 0.0

            # Create result
            result = SentimentAnalysisResult(
                news_id=news_id,
                sentiment_score=polarity_score,
                sentiment_label=sentiment_label,
                model_name="bert-sentiment-analysis",
                created_at=datetime.utcnow(),
                metadata={
                    "title": news["title"],
                    "source": news["source"],
                    "raw_result": sentiment_result
                }
            )

            # Update news record with sentiment score
            news_collection.update_one(
                {"_id": news_id},
                {"$set": {
                    "sentiment_score": polarity_score,
                    "sentiment_label": sentiment_label,
                    "updated_at": datetime.utcnow()
                }}
            )

            return result

        except Exception as e:
            logger.error(f"Error performing sentiment analysis for news {news_id}: {e}")
            return None

    async def process_news_pipeline(self, news_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Run the full processing pipeline for a news article"""
        results = {}
        success = True

        # Step 1: Create embeddings
        embedding_result = self.create_embeddings_for_news(news_id)
        if embedding_result:
            results["embedding"] = "success"
        else:
            results["embedding"] = "failed"
            success = False

        # Step 2: Trust analysis
        trust_result = await self.perform_trust_analysis(news_id)
        if trust_result:
            results["trust_analysis"] = trust_result.trust_score
        else:
            results["trust_analysis"] = "failed"
            success = False

        # Step 3: Sentiment analysis
        sentiment_result = await self.perform_sentiment_analysis(news_id)
        if sentiment_result:
            results["sentiment_analysis"] = {
                "score": sentiment_result.sentiment_score,
                "label": sentiment_result.sentiment_label
            }
        else:
            results["sentiment_analysis"] = "failed"
            success = False

        return success, results

    def search_similar_news(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for news articles similar to the query"""
        try:
            # LangChain 벡터 저장소 사용 (기존 방식)
            vectorstore = self.get_vectorstore()
            langchain_results = vectorstore.similarity_search_with_score(query, k=limit)

            similar_news = []
            for doc, score in langchain_results:
                news_id = doc.metadata.get("news_id")
                if news_id:
                    news = news_collection.find_one({"_id": news_id})
                    if news:
                        similar_news.append({
                            "id": news["_id"],
                            "title": news["title"],
                            "source": news["source"],
                            "published_date": news["published_date"],
                            "url": news["url"],
                            "trust_score": news.get("trust_score"),
                            "sentiment_score": news.get("sentiment_score"),
                            "similarity_score": float(score)
                        })

            # 벡터 저장소 서비스도 사용해 보고 결과 보강 (결과가 부족한 경우)
            if len(similar_news) < limit:
                # 쿼리 임베딩 생성
                query_embedding = self.get_embedding(query)

                # 벡터 저장소 서비스에서 검색
                vector_results = self.vector_store_service.search_by_vector(
                    query_vector=query_embedding,
                    limit=limit
                )

                # 결과 통합 (중복 방지)
                existing_ids = {item["id"] for item in similar_news}
                for result in vector_results:
                    if result["id"] not in existing_ids and len(similar_news) < limit:
                        news_id = result["id"]
                        news = news_collection.find_one({"_id": news_id})
                        if news:
                            similar_news.append({
                                "id": news["_id"],
                                "title": news["title"],
                                "source": news["source"],
                                "published_date": news["published_date"],
                                "url": news["url"],
                                "trust_score": news.get("trust_score"),
                                "sentiment_score": news.get("sentiment_score"),
                                "similarity_score": result.get("similarity", 0.5)
                            })
                            existing_ids.add(news_id)

            return similar_news

        except Exception as e:
            logger.error(f"Error searching similar news: {e}")
            return []


# Helper function to initialize service
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
