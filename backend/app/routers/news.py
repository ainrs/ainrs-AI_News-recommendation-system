from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel

from app.db.mongodb import get_mongodb_database
from app.services.embedding_service import EmbeddingService
from app.services.recommendation_service import RecommendationService
from app.services.langchain_service import LangChainService
from app.services.trust_analysis_service import TrustAnalysisService
from app.services.sentiment_analysis_service import SentimentAnalysisService

router = APIRouter(prefix="/news", tags=["news"])

# 댓글 관련 모델
class CommentCreate(BaseModel):
    user_id: str
    content: str
    parent_id: Optional[str] = None  # 대댓글인 경우

class CommentResponse(BaseModel):
    id: str
    news_id: str
    user_id: str
    user_name: str
    content: str
    created_at: datetime
    likes: int = 0
    replies: Optional[List["CommentResponse"]] = None

# 댓글 엔드포인트
@router.get("/{news_id}/comments", response_model=List[CommentResponse])
async def get_comments(
    news_id: str,
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db = Depends(get_mongodb_database)
):
    """
    뉴스 댓글을 가져옵니다.
    """
    try:
        # 뉴스 존재 확인
        news_collection = db["news"]
        news = await news_collection.find_one({"_id": ObjectId(news_id)})
        if not news:
            raise HTTPException(status_code=404, detail="News not found")

        # 댓글 가져오기
        comment_collection = db["comments"]
        comments = []

        # 최상위 댓글만 가져오기
        cursor = comment_collection.find({
            "news_id": news_id,
            "parent_id": None  # 최상위 댓글만
        }).sort("created_at", -1).skip(skip).limit(limit)

        async for comment in cursor:
            # 사용자 정보 가져오기
            user_collection = db["users"]
            user = await user_collection.find_one({"_id": comment["user_id"]})
            user_name = user["name"] if user else "Unknown User"

            # 대댓글 가져오기
            replies = []
            replies_cursor = comment_collection.find({
                "news_id": news_id,
                "parent_id": str(comment["_id"])
            }).sort("created_at", 1)

            async for reply in replies_cursor:
                reply_user = await user_collection.find_one({"_id": reply["user_id"]})
                reply_user_name = reply_user["name"] if reply_user else "Unknown User"

                replies.append({
                    "id": str(reply["_id"]),
                    "news_id": reply["news_id"],
                    "user_id": reply["user_id"],
                    "user_name": reply_user_name,
                    "content": reply["content"],
                    "created_at": reply["created_at"],
                    "likes": reply.get("likes", 0),
                    "replies": []
                })

            comments.append({
                "id": str(comment["_id"]),
                "news_id": comment["news_id"],
                "user_id": comment["user_id"],
                "user_name": user_name,
                "content": comment["content"],
                "created_at": comment["created_at"],
                "likes": comment.get("likes", 0),
                "replies": replies
            })

        return comments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching comments: {str(e)}")

@router.post("/{news_id}/comments", response_model=CommentResponse)
async def create_comment(
    news_id: str,
    comment: CommentCreate,
    db = Depends(get_mongodb_database)
):
    """
    뉴스에 댓글을 작성합니다.
    """
    try:
        # 뉴스 존재 확인
        news_collection = db["news"]
        news = await news_collection.find_one({"_id": ObjectId(news_id)})
        if not news:
            raise HTTPException(status_code=404, detail="News not found")

        # 사용자 존재 확인
        user_collection = db["users"]
        user = await user_collection.find_one({"_id": comment.user_id})
        if not user:
            # 사용자가 없으면 기본 사용자 생성 (실제 앱에서는 인증 필요)
            user = {
                "_id": comment.user_id,
                "name": "User " + comment.user_id[-4:],
                "created_at": datetime.utcnow()
            }
            await user_collection.insert_one(user)

        user_name = user["name"]

        # 부모 댓글 존재 확인 (대댓글인 경우)
        if comment.parent_id:
            comment_collection = db["comments"]
            parent_comment = await comment_collection.find_one({"_id": ObjectId(comment.parent_id)})
            if not parent_comment:
                raise HTTPException(status_code=404, detail="Parent comment not found")

        # 댓글 생성
        comment_data = {
            "news_id": news_id,
            "user_id": comment.user_id,
            "content": comment.content,
            "parent_id": comment.parent_id,
            "created_at": datetime.utcnow(),
            "likes": 0
        }

        comment_collection = db["comments"]
        result = await comment_collection.insert_one(comment_data)
        comment_id = str(result.inserted_id)

        # 상호작용 기록
        interaction_data = {
            "user_id": comment.user_id,
            "news_id": news_id,
            "type": "comment",
            "timestamp": datetime.utcnow(),
            "metadata": {
                "comment_id": comment_id
            }
        }

        interaction_collection = db["user_interactions"]
        await interaction_collection.insert_one(interaction_data)

        # 댓글 수 업데이트
        await news_collection.update_one(
            {"_id": ObjectId(news_id)},
            {"$inc": {"comment_count": 1}}
        )

        return {
            "id": comment_id,
            "news_id": news_id,
            "user_id": comment.user_id,
            "user_name": user_name,
            "content": comment.content,
            "created_at": comment_data["created_at"],
            "likes": 0,
            "replies": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating comment: {str(e)}")

@router.post("/{news_id}/comments/{comment_id}/like")
async def like_comment(
    news_id: str,
    comment_id: str,
    user_id: str = Body(...),
    db = Depends(get_mongodb_database)
):
    """
    댓글에 좋아요를 추가합니다.
    """
    try:
        # 댓글 존재 확인
        comment_collection = db["comments"]
        comment = await comment_collection.find_one({"_id": ObjectId(comment_id)})
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")

        # 이미 좋아요를 눌렀는지 확인
        like_collection = db["comment_likes"]
        existing_like = await like_collection.find_one({
            "comment_id": comment_id,
            "user_id": user_id
        })

        if existing_like:
            # 이미 좋아요를 누른 경우, 좋아요 취소
            await like_collection.delete_one({
                "comment_id": comment_id,
                "user_id": user_id
            })

            # 댓글 좋아요 수 감소
            await comment_collection.update_one(
                {"_id": ObjectId(comment_id)},
                {"$inc": {"likes": -1}}
            )

            return {"message": "Comment like removed", "liked": False}
        else:
            # 좋아요 추가
            like_data = {
                "comment_id": comment_id,
                "user_id": user_id,
                "news_id": news_id,
                "created_at": datetime.utcnow()
            }

            await like_collection.insert_one(like_data)

            # 댓글 좋아요 수 증가
            await comment_collection.update_one(
                {"_id": ObjectId(comment_id)},
                {"$inc": {"likes": 1}}
            )

            return {"message": "Comment liked successfully", "liked": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error liking comment: {str(e)}")

# 뉴스 좋아요 엔드포인트
@router.post("/{news_id}/like")
async def like_news(
    news_id: str,
    user_id: str = Body(...),
    db = Depends(get_mongodb_database)
):
    """
    뉴스에 좋아요를 추가합니다.
    """
    try:
        # 뉴스 존재 확인
        news_collection = db["news"]
        news = await news_collection.find_one({"_id": ObjectId(news_id)})
        if not news:
            raise HTTPException(status_code=404, detail="News not found")

        # 상호작용 컬렉션
        interaction_collection = db["user_interactions"]

        # 이미 좋아요를 눌렀는지 확인
        existing_like = await interaction_collection.find_one({
            "news_id": news_id,
            "user_id": user_id,
            "type": "like"
        })

        if existing_like:
            # 이미 좋아요를 누른 경우, 좋아요 취소
            await interaction_collection.delete_one({
                "news_id": news_id,
                "user_id": user_id,
                "type": "like"
            })

            # 뉴스 좋아요 수 감소
            await news_collection.update_one(
                {"_id": ObjectId(news_id)},
                {"$inc": {"like_count": -1}}
            )

            return {"message": "News like removed", "liked": False}
        else:
            # 좋아요 상호작용 추가
            interaction_data = {
                "user_id": user_id,
                "news_id": news_id,
                "type": "like",
                "timestamp": datetime.utcnow()
            }

            await interaction_collection.insert_one(interaction_data)

            # 뉴스 좋아요 수 증가
            await news_collection.update_one(
                {"_id": ObjectId(news_id)},
                {"$inc": {"like_count": 1}}
            )

            return {"message": "News liked successfully", "liked": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error liking news: {str(e)}")

# 북마크 엔드포인트
@router.post("/{news_id}/bookmark")
async def bookmark_news(
    news_id: str,
    user_id: str = Body(...),
    bookmarked: bool = Body(...),
    db = Depends(get_mongodb_database)
):
    """
    뉴스를 북마크합니다.
    """
    try:
        # 뉴스 존재 확인
        news_collection = db["news"]
        news = await news_collection.find_one({"_id": ObjectId(news_id)})
        if not news:
            raise HTTPException(status_code=404, detail="News not found")

        # 상호작용 컬렉션
        interaction_collection = db["user_interactions"]
        bookmark_collection = db["bookmarks"]

        # 북마크 상태 확인
        existing_bookmark = await bookmark_collection.find_one({
            "news_id": news_id,
            "user_id": user_id
        })

        if bookmarked and not existing_bookmark:
            # 북마크 추가
            bookmark_data = {
                "user_id": user_id,
                "news_id": news_id,
                "created_at": datetime.utcnow()
            }

            await bookmark_collection.insert_one(bookmark_data)

            # 상호작용 기록
            interaction_data = {
                "user_id": user_id,
                "news_id": news_id,
                "type": "bookmark",
                "timestamp": datetime.utcnow()
            }

            await interaction_collection.insert_one(interaction_data)

            return {"message": "News bookmarked successfully", "bookmarked": True}

        elif not bookmarked and existing_bookmark:
            # 북마크 제거
            await bookmark_collection.delete_one({
                "news_id": news_id,
                "user_id": user_id
            })

            return {"message": "News bookmark removed", "bookmarked": False}

        # 이미 요청된 상태와 동일하면 그대로 반환
        return {"message": "Bookmark status unchanged", "bookmarked": bookmarked}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error bookmarking news: {str(e)}")

# 뉴스 통계 엔드포인트
@router.get("/{news_id}/stats")
async def get_news_stats(
    news_id: str,
    db = Depends(get_mongodb_database)
):
    """
    뉴스의 상호작용 통계를 가져옵니다.
    """
    try:
        # 뉴스 존재 확인
        news_collection = db["news"]
        news = await news_collection.find_one({"_id": ObjectId(news_id)})
        if not news:
            raise HTTPException(status_code=404, detail="News not found")

        # 상호작용 컬렉션
        interaction_collection = db["user_interactions"]
        comment_collection = db["comments"]

        # 통계 계산
        views_count = await interaction_collection.count_documents({
            "news_id": news_id,
            "type": "view"
        })

        likes_count = await interaction_collection.count_documents({
            "news_id": news_id,
            "type": "like"
        })

        shares_count = await interaction_collection.count_documents({
            "news_id": news_id,
            "type": "share"
        })

        comments_count = await comment_collection.count_documents({
            "news_id": news_id
        })

        # 통계 저장
        await news_collection.update_one(
            {"_id": ObjectId(news_id)},
            {"$set": {
                "view_count": views_count,
                "like_count": likes_count,
                "share_count": shares_count,
                "comment_count": comments_count,
                "stats_updated_at": datetime.utcnow()
            }}
        )

        return {
            "views": views_count,
            "likes": likes_count,
            "shares": shares_count,
            "comments": comments_count,
            "updated_at": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting news stats: {str(e)}")
