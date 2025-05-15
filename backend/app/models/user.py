from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, EmailStr

class UserBase(BaseModel):
    """Base user model"""
    username: str
    email: Optional[EmailStr] = None
    is_active: bool = True

class UserCreate(UserBase):
    """Model for creating a user"""
    password: str
    verified: bool = False

class UserVerify(BaseModel):
    """Model for email verification"""
    email: EmailStr
    code: str

class UserInDB(UserBase):
    """User model as stored in database"""
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)
    engagement_score: Optional[float] = None
    verified: bool = False
    password_hash: str

    class Config:
        populate_by_name = True

class UserProfile(BaseModel):
    """User profile model for API responses"""
    id: str
    username: str
    email: Optional[EmailStr] = None
    created_at: datetime
    preferences: Dict[str, Any] = Field(default_factory=dict)
    engagement_score: Optional[float] = None

class UserInteraction(BaseModel):
    """User interaction with news articles"""
    user_id: str
    news_id: str
    interaction_type: str  # click, read, like, share, save, etc.
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Additional fields for advanced interaction tracking
    dwell_time_seconds: Optional[int] = None
    scroll_depth_percent: Optional[int] = None
    interaction_score: Optional[float] = None  # Calculated score based on type and metrics

class UserPreferences(BaseModel):
    """User preferences for personalization"""
    user_id: str
    category_preferences: Dict[str, float] = Field(default_factory=dict)
    source_preferences: Dict[str, float] = Field(default_factory=dict)
    topic_preferences: Dict[str, float] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    # -1 to 1 scales indicating preference
    trust_importance: float = 0.5  # How much user values trustworthy sources
    diversity_preference: float = 0.0  # Negative: filter bubble, Positive: diverse content
    recency_preference: float = 0.3  # How much to favor recent articles

class UserSimilarity(BaseModel):
    """Similarity between two users"""
    user_id_1: str
    user_id_2: str
    similarity_score: float  # 0-1 score
    similarity_type: str  # content-based, interaction-based, combined
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    features_used: List[str] = Field(default_factory=list)  # which features were used to calculate
