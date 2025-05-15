from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field
from datetime import datetime


class EmbeddingBase(BaseModel):
    """Base embedding model"""
    model_name: str
    dimensions: int


class OpenAIEmbeddingConfig(EmbeddingBase):
    """OpenAI embedding model configuration"""
    model_name: str = "text-embedding-3-small"
    dimensions: int = 1536
    api_key: Optional[str] = None
    batch_size: int = 100


class BiLSTMEmbeddingConfig(EmbeddingBase):
    """BiLSTM embedding model configuration for trust analysis"""
    model_name: str = "bilstm-trust"
    dimensions: int = 768
    model_path: str = "models/bilstm-trust"
    vocab_path: Optional[str] = None
    max_length: int = 512


class SentimentBERTConfig(EmbeddingBase):
    """Sentiment BERT model configuration"""
    model_name: str = "bert-sentiment"
    dimensions: int = 768
    model_path: str = "models/bert-sentiment"
    vocab_path: Optional[str] = None
    max_length: int = 512


class EmbeddingResult(BaseModel):
    """Embedding result model"""
    news_id: str
    embedding: List[float]
    model_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrustAnalysisResult(BaseModel):
    """Trust analysis result model"""
    news_id: str
    trust_score: float
    model_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SentimentAnalysisResult(BaseModel):
    """Sentiment analysis result model"""
    news_id: str
    sentiment_score: float  # -1 to 1 (negative to positive)
    sentiment_label: str  # negative, neutral, positive
    model_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EmbeddingRequest(BaseModel):
    """Request for creating embeddings"""
    news_ids: List[str]
    model_name: Optional[str] = "text-embedding-3-small"


class TrustAnalysisRequest(BaseModel):
    """Request for trust analysis"""
    news_ids: List[str]
    model_name: Optional[str] = "bilstm-trust"


class SentimentAnalysisRequest(BaseModel):
    """Request for sentiment analysis"""
    news_ids: List[str]
    model_name: Optional[str] = "bert-sentiment"
