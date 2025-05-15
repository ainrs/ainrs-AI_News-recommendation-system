from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, HttpUrl


class NewsBase(BaseModel):
    """Base news model"""
    title: str
    content: str
    url: HttpUrl
    source: str
    published_date: datetime
    author: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    summary: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class NewsCreate(NewsBase):
    """Model for creating a news article"""
    pass


class NewsInDB(NewsBase):
    """News model as stored in database"""
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    trust_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    embedding_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class NewsResponse(NewsBase):
    """News model for API response"""
    id: str
    created_at: datetime
    updated_at: datetime
    trust_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class NewsSummary(BaseModel):
    """Summary of a news article"""
    id: str
    title: str
    source: str
    published_date: datetime
    summary: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    trust_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    similarity_score: Optional[float] = None
    categories: List[str] = Field(default_factory=list)


class NewsEmbedding(BaseModel):
    """News embedding model"""
    news_id: str
    embedding: List[float]
    embedding_model: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NewsSearchQuery(BaseModel):
    """News search query"""
    query: str
    categories: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_trust_score: Optional[float] = None
    sentiment: Optional[str] = None  # positive, negative, neutral
    limit: int = 10
    skip: int = 0
