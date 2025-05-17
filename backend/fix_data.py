from app.db.mongodb import news_collection
from pymongo import MongoClient
from app.core.config import settings
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_news_data():
    """기존 뉴스 데이터의 빈 카테고리와 내용을 업데이트합니다."""
    logger.info("🔧 기존 뉴스 데이터 수정 시작...")

    # MongoDB 클라이언트 생성
    client = MongoClient(settings.MONGODB_URI)
    db = client.get_database()

    # 뉴스 컬렉션 가져오기
    news_coll = db["news"]

    # 수정이 필요한 기사 개수 확인
    empty_categories_count = news_coll.count_documents({"$or": [
        {"categories": {"$exists": False}},
        {"categories": []},
        {"categories": None}
    ]})

    empty_content_count = news_coll.count_documents({"$or": [
        {"content": {"$exists": False}},
        {"content": ""},
        {"content": None}
    ]})

    logger.info(f"📊 카테고리가 비어있는 기사: {empty_categories_count}개")
    logger.info(f"📊 내용이 비어있는 기사: {empty_content_count}개")

    # 모든 뉴스 가져오기
    all_news = list(news_coll.find())
    logger.info(f"📊 전체 기사 수: {len(all_news)}개")

    # 수정된 기사 개수
    updated_count = 0

    # 각 기사 처리
    for news in all_news:
        news_id = news["_id"]
        title = news.get("title", "")
        update_data = {}
        needs_update = False

        # 1. 카테고리가 비어있는 경우 업데이트
        if "categories" not in news or not news["categories"]:
            # 제목에서 카테고리 추론
            title_lower = title.lower()
            categories = []

            # 프론트엔드 카테고리와 일치하도록 정의
            # (인공지능, 빅데이터, 클라우드, 로봇, 블록체인, 메타버스, IT기업, 스타트업, AI서비스, 칼럼)
            if "ai" in title_lower or "인공지능" in title_lower or "머신러닝" in title_lower or "딥러닝" in title_lower:
                categories = ["인공지능"]
            elif "빅데이터" in title_lower or "데이터" in title_lower or "data" in title_lower:
                categories = ["빅데이터"]
            elif "클라우드" in title_lower or "cloud" in title_lower:
                categories = ["클라우드"]
            elif "로봇" in title_lower or "robot" in title_lower:
                categories = ["로봇"]
            elif "블록체인" in title_lower or "암호화폐" in title_lower or "blockchain" in title_lower or "crypto" in title_lower:
                categories = ["블록체인"]
            elif "메타버스" in title_lower or "가상현실" in title_lower or "증강현실" in title_lower or "metaverse" in title_lower or "vr" in title_lower or "ar" in title_lower:
                categories = ["메타버스"]
            elif "it" in title_lower or "기업" in title_lower or "회사" in title_lower or "company" in title_lower or "테크" in title_lower:
                categories = ["IT기업"]
            elif "스타트업" in title_lower or "startup" in title_lower or "벤처" in title_lower:
                categories = ["스타트업"]
            elif "서비스" in title_lower or "플랫폼" in title_lower or "service" in title_lower or "platform" in title_lower:
                categories = ["AI서비스"]
            elif "칼럼" in title_lower or "opinion" in title_lower or "column" in title_lower or "기고" in title_lower or "사설" in title_lower:
                categories = ["칼럼"]
            else:
                categories = ["인공지능"]  # 기본값은 인공지능으로 설정

            update_data["categories"] = categories
            needs_update = True

        # 2. 내용이 비어있는 경우 업데이트
        if "content" not in news or not news["content"]:
            # 요약이 있으면 요약을 내용으로 사용
            summary = news.get("summary", "")
            if summary:
                update_data["content"] = summary
            else:
                # 최소한 제목을 내용으로 사용
                update_data["content"] = f"{title} (자세한 내용은 원문을 참조하세요.)"
            needs_update = True

        # 3. 이미지 URL이 없는 경우 기본 이미지 설정
        if "image_url" not in news or not news["image_url"]:
            update_data["image_url"] = "https://via.placeholder.com/300x200?text=No+Image"
            needs_update = True

        # 업데이트가 필요한 경우 진행
        if needs_update:
            # 수정 시간 업데이트
            update_data["updated_at"] = datetime.utcnow()

            # 데이터베이스 업데이트
            result = news_coll.update_one(
                {"_id": news_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                updated_count += 1

    logger.info(f"✅ 기사 업데이트 완료: {updated_count}/{len(all_news)}개 기사 수정됨")

    # 연결 종료
    client.close()

if __name__ == "__main__":
    fix_news_data()
