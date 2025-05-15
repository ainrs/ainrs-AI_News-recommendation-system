import os
from typing import List, Optional, Union, Dict, Any
from pydantic import AnyHttpUrl, EmailStr
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI News Recommendation System"

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # MongoDB settings
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "news_recommendation")

    # OpenAI settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Data directory
    DATA_DIR: str = os.getenv("DATA_DIR", "./data")

    # Email settings
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "naver")
    MAIL_USERNAME: str = os.getenv("NAVER_MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.getenv("NAVER_MAIL_PASSWORD", "")
    MAIL_FROM: str = os.getenv("NAVER_MAIL_FROM", "")
    MAIL_PORT: int = int(os.getenv("NAVER_MAIL_PORT", "465"))
    MAIL_SERVER: str = os.getenv("NAVER_MAIL_SERVER", "smtp.naver.com")
    MAIL_STARTTLS: bool = os.getenv("NAVER_MAIL_TLS", "False").lower() == "true"
    MAIL_SSL_TLS: bool = os.getenv("NAVER_MAIL_SSL", "True").lower() == "true"
    USE_CREDENTIALS: bool = os.getenv("USE_CREDENTIALS", "True").lower() == "true"

    # Email verification settings
    EMAIL_VERIFICATION_SECRET_KEY: str = os.getenv("EMAIL_VERIFICATION_SECRET_KEY", "your_secret_key_for_verification")
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = int(os.getenv("EMAIL_VERIFICATION_EXPIRE_MINUTES", "4"))

    # RSS feed settings
    RSS_FEEDS: List[str] = [
        # 국내 뉴스 RSS 피드
        "https://www.yna.co.kr/rss/all.xml",           # 연합뉴스
        "https://news.kbs.co.kr/rss/rss.xml",          # KBS 뉴스
        "https://www.ytn.co.kr/_rss/all.xml",          # YTN
        "https://www.hani.co.kr/rss/",                 # 한겨레신문
        "https://www.khan.co.kr/rss/rssdata/kh_total.xml", # 경향신문
        "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml", # 조선일보
        "https://www.donga.com/rss/",                  # 동아일보

        # 해외 뉴스 RSS 피드
        "https://feeds.bbci.co.uk/news/world/rss.xml", # BBC News (World)
        "http://rss.cnn.com/rss/cnn_topstories.rss",   # CNN Top Stories
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", # The New York Times
        "http://feeds.reuters.com/reuters/topNews",     # Reuters Top News
        "https://feeds.npr.org/1001/rss.xml",          # NPR (US News)
        "https://www.aljazeera.com/xml/rss/all.xml",   # Al Jazeera English
        "https://www.theguardian.com/world/rss",       # The Guardian (World)

        # IT/기술 뉴스 RSS 피드 (AI, 클라우드, 빅데이터, 스타트업)
        "https://zdnet.co.kr/rss/all/rss.xml",         # ZDNet Korea
        "https://rss.etnews.com/",                     # 전자신문
        "https://www.bloter.net/feed",                 # 블로터
        "https://feeds.feedburner.com/venturesquare",  # 벤처스퀘어 (스타트업)
        "https://news.hada.io/rss/topics/all",         # 하다(스타트업/테크)
        "https://platum.kr/feed",                      # 플래텀 (스타트업)
        "https://thevc.kr/feed",                       # 더VC (스타트업/투자)
        "https://www.itworld.co.kr/rss/feed",          # IT World
        "https://www.aitimes.com/rss/allArticle.xml",  # AI 타임스
        "https://www.itfind.or.kr/websquare/itfind_rss/ALL.xml",  # IT Find (정보통신기술진흥센터)
        "https://verticalplatform.kr/news/feed",       # 버티컬 플랫폼
    ]

    class Config:
        case_sensitive = True


settings = Settings()
