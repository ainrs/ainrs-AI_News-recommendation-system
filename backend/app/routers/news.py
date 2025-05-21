from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel

from app.db.mongodb import get_mongodb_database
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.bert4rec_service import get_bert4rec_service
from app.services.recommendation_service import RecommendationService
from app.services.langchain_service import LangChainService, get_langchain_service
from app.services.trust_analysis_service import TrustAnalysisService, get_trust_analysis_service
from app.services.sentiment_analysis_service import SentimentAnalysisService, get_sentiment_analysis_service
import re
import asyncio
import logging
from langdetect import detect, LangDetectException

# 로깅 설정
logger = logging.getLogger(__name__)

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news", tags=["news"])

# 고급 분석 및 임베딩 처리를 위한 의존성 주입 함수들
def get_langchain_service_dep():
    return get_langchain_service()

def get_embedding_service_dep():
    return get_embedding_service()

def get_bert4rec_service_dep():
    return get_bert4rec_service()

def get_trust_analysis_service_dep():
    return get_trust_analysis_service()

def get_sentiment_analysis_service_dep():
    return get_sentiment_analysis_service()

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

# 기사 상세 조회 엔드포인트 (사용자가 기사 클릭 시 호출)
@router.get("/{news_id}", response_model=Dict[str, Any])
async def get_news_detail(
    news_id: str,
    user_id: Optional[str] = Query(None),
    db = Depends(get_mongodb_database),
    langchain_service = Depends(get_langchain_service_dep),
    embedding_service = Depends(get_embedding_service_dep),
    bert4rec_service = Depends(get_bert4rec_service_dep),
    trust_service = Depends(get_trust_analysis_service_dep),
    sentiment_service = Depends(get_sentiment_analysis_service_dep)
):
    """
    뉴스 상세 정보를 가져옵니다.
    사용자가 뉴스를 클릭할 때 호출되며, 필요한 경우 고급 AI 분석을 수행합니다.
    """
    try:
        # 뉴스 존재 확인
        news_collection = db["news"]

        # ObjectId로 변환 시도
        try:
            news_id_obj = ObjectId(news_id)
            news = await news_collection.find_one({"_id": news_id_obj})
        except:
            # 실패하면 문자열 ID로 시도
            news = await news_collection.find_one({"_id": news_id})

        if not news:
            raise HTTPException(status_code=404, detail="News not found")

        # 조회수 증가 및 상호작용 기록
        if user_id:
            # 사용자 상호작용 기록
            interaction_data = {
                "user_id": user_id,
                "news_id": str(news["_id"]),
                "type": "view",
                "created_at": datetime.utcnow()
            }

            # 상호작용 저장
            interaction_collection = db["user_interactions"]
            await interaction_collection.insert_one(interaction_data)

            # 뉴스 조회수 증가
            await news_collection.update_one(
                {"_id": news["_id"]},
                {"$inc": {"view_count": 1}}
            )

        # 뉴스가 기본 정보만 있는 경우 (is_basic_info=True) 고급 AI 분석 수행
        if news.get("is_basic_info", False) and news.get("content"):
            try:
                # 분석 시작 로그
                logger.info(f"🔍 기사 ID {news_id}에 대한 고급 분석 시작")

                # 기사의 제목과 내용을 가져옴
                title = news.get("title", "")
                content = news.get("content", "")

                if len(content) >= 300:  # 콘텐츠 길이가 충분한 경우만 AI 처리
                    # 1. 언어 감지 - 최적의 임베딩 모델 선택을 위해
                    detected_lang = "ko"  # 기본값은 한국어
                    try:
                        # 본문 일부만 사용하여 언어 감지 (효율성)
                        sample_text = content[:1000]
                        detected_lang = detect(sample_text)
                        logger.info(f"감지된 언어: {detected_lang}")
                    except LangDetectException:
                        logger.warning("언어 감지 실패, 기본값(한국어)으로 설정")

                    # 2. 병렬로 여러 분석 작업 실행
                    # 병렬 처리를 위한 태스크 생성
                    tasks = []

                    # 2.1 LangChain 분석 (요약, 키워드 추출 등)
                    tasks.append(asyncio.create_task(
                        asyncio.to_thread(
                            langchain_service.analyze_news_sync,
                            title,
                            content
                        )
                    ))

                    # 2.2 임베딩 생성 (언어에 맞는 모델 사용)
                    embedding_model = "news-ko"  # 기본 한국어 모델
                    if detected_lang in ["en", "de", "fr", "es", "it"]:
                        embedding_model = "multilingual"  # 서양어는 다국어 모델

                    tasks.append(asyncio.create_task(
                        asyncio.to_thread(
                            embedding_service.get_embedding_with_model,
                            content,
                            embedding_model
                        )
                    ))

                    # 2.3 신뢰도 분석
                    try:
                        # 신뢰도 분석 비동기 호출 - 코루틴이 아닌 결과를 얻도록 수정
                        tasks.append(asyncio.create_task(
                            trust_service.analyze_trust(
                                title,
                                content
                            )
                        ))
                    except Exception as trust_error:
                        logger.error(f"신뢰도 분석 작업 생성 중 오류: {trust_error}")
                        # 기본값 설정
                        trust_result = {"trust_score": 0.5, "source": "default"}

                    # 2.4 감정 분석 - asyncio.to_thread는 이미 코루틴을 반환하므로 래핑 필요 없음
                    tasks.append(asyncio.create_task(
                        sentiment_service.analyze_sentiment(content)
                    ))

                    # 모든 작업 대기
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # 결과 파싱
                    ai_result = results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])}
                    embedding_result = results[1] if not isinstance(results[1], Exception) else None
                    trust_result = results[2] if not isinstance(results[2], Exception) else None
                    sentiment_result = results[3] if not isinstance(results[3], Exception) else None

                    # 분석 결과가 있으면 업데이트할 데이터 준비
                    update_data = {
                        "is_basic_info": False,  # 완전히 처리된 상태로 표시
                        "updated_at": datetime.utcnow(),
                        "analyzed_at": datetime.utcnow(),
                        "language": detected_lang
                    }

                    # AI 분석 결과 적용
                    if not "error" in ai_result:
                        # 요약 적용
                        update_data["summary"] = ai_result.get("summary", "")
                        update_data["keywords"] = ai_result.get("keywords", [])
                        update_data["ai_enhanced"] = True

                    # 신뢰도 점수 계산 및 저장
                    if trust_result:
                        trust_score = trust_result.get("score", 0.5)
                        update_data["trust_score"] = trust_score
                        update_data["trust_factors"] = trust_result.get("factors", [])
                    else:
                        # LangChain 결과에서 신뢰도 대체 추출
                        update_data["trust_score"] = min(1.0, float(ai_result.get("importance", 5)) / 10.0)

                    # 감정 분석 결과 저장
                    if sentiment_result:
                        sentiment_score = sentiment_result.get("score", 0)
                        update_data["sentiment_score"] = sentiment_score
                        update_data["sentiment_label"] = sentiment_result.get("label", "neutral")
                    else:
                        # LangChain 결과에서 감정 라벨 대체 추출
                        sentiment_label = ai_result.get("sentiment", "neutral")
                        sentiment_score = 0
                        if sentiment_label == "positive":
                            sentiment_score = 0.7
                        elif sentiment_label == "negative":
                            sentiment_score = -0.7
                        update_data["sentiment_score"] = sentiment_score
                        update_data["sentiment_label"] = sentiment_label

                    # 임베딩 결과가 있으면 저장
                    if embedding_result is not None and len(embedding_result) > 0:
                        # 임베딩 저장
                        embedding_doc = {
                            "news_id": str(news["_id"]),
                            "embedding": embedding_result,
                            "model": embedding_model,
                            "created_at": datetime.utcnow()
                        }
                        try:
                            await db["embeddings"].insert_one(embedding_doc)
                            update_data["has_embedding"] = True
                            update_data["embedding_model"] = embedding_model
                        except Exception as e:
                            logger.error(f"임베딩 저장 중 오류: {str(e)}")

                    # 기사 업데이트
                    await news_collection.update_one(
                        {"_id": news["_id"]},
                        {"$set": update_data}
                    )

                    # BERT4Rec 모델에 기사 정보 추가
                    if user_id:
                        try:
                            bert4rec_service.add_interaction(user_id, str(news["_id"]), "view")
                        except Exception as e:
                            logger.error(f"BERT4Rec 상호작용 추가 중 오류: {str(e)}")

                    # 업데이트된 결과 가져오기
                    if isinstance(news["_id"], ObjectId):
                        news = await news_collection.find_one({"_id": news["_id"]})
                    else:
                        news = await news_collection.find_one({"_id": news["_id"]})

                    logger.info(f"✅ 기사 ID {news_id} 고급 분석 완료")
            except Exception as e:
                logger.error(f"AI 분석 중 오류: {str(e)}")
                # 오류가 발생해도 기존 뉴스 데이터 반환

        # MongoDB _id를 문자열로 변환
        if "_id" in news and isinstance(news["_id"], ObjectId):
            news["_id"] = str(news["_id"])

        # 이미지 URL 처리
        if "image_url" in news and news["image_url"]:
            # 상대 경로인 경우 처리
            if news["image_url"].startswith("/") or not (news["image_url"].startswith("http://") or news["image_url"].startswith("https://")):
                # 기본 이미지 URL로 대체
                news["image_url"] = "https://via.placeholder.com/800x400?text=News+Image"

        # 이미지 URL이 없으면 기본 이미지 설정
        if "image_url" not in news or not news["image_url"]:
            news["image_url"] = "https://via.placeholder.com/800x400?text=News+Image"

        return news
    except Exception as e:
        logger.error(f"뉴스 상세 정보 가져오기 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting news: {str(e)}")

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
        # ObjectId로 변환 시도
        try:
            news_id_obj = ObjectId(news_id)
            news = await news_collection.find_one({"_id": news_id_obj})
        except:
            # 실패하면 문자열 ID로 시도
            news = await news_collection.find_one({"_id": news_id})

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
        # ObjectId로 변환 시도
        try:
            news_id_obj = ObjectId(news_id)
            news = await news_collection.find_one({"_id": news_id_obj})
        except:
            # 실패하면 문자열 ID로 시도
            news = await news_collection.find_one({"_id": news_id})

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
        # ObjectId로 변환 시도
        try:
            news_id_obj = ObjectId(news_id)
            news = await news_collection.find_one({"_id": news_id_obj})
        except:
            # 실패하면 문자열 ID로 시도
            news = await news_collection.find_one({"_id": news_id})

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
        # ObjectId로 변환 시도
        try:
            news_id_obj = ObjectId(news_id)
            news = await news_collection.find_one({"_id": news_id_obj})
        except:
            # 실패하면 문자열 ID로 시도
            news = await news_collection.find_one({"_id": news_id})

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
        # ObjectId로 변환 시도
        try:
            news_id_obj = ObjectId(news_id)
            news = await news_collection.find_one({"_id": news_id_obj})
        except:
            # 실패하면 문자열 ID로 시도
            news = await news_collection.find_one({"_id": news_id})

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

@router.post("/{news_id}/key-phrases")
async def extract_key_phrases(
    news_id: str,
    limit: int = Query(10, ge=1, le=50),
    db = Depends(get_mongodb_database),
    langchain_service = Depends(get_langchain_service_dep)
):
    """
    뉴스에서 키워드를 추출합니다.
    """
    try:
        # 뉴스 존재 확인
        news_collection = db["news"]

        # ObjectId로 변환 시도
        try:
            news_id_obj = ObjectId(news_id)
            news = await news_collection.find_one({"_id": news_id_obj})
        except:
            # 실패하면 문자열 ID로 시도
            news = await news_collection.find_one({"_id": news_id})

        if not news:
            raise HTTPException(status_code=404, detail="News not found")

        # 이미 키워드가 있으면 반환
        if "keywords" in news and news["keywords"] and len(news["keywords"]) > 0:
            return {
                "news_id": str(news["_id"]),
                "key_phrases": news["keywords"][:limit]
            }

        # 텍스트 준비
        title = news.get("title", "")
        content = news.get("content", "")

        # LangChain 서비스로 키워드 추출
        analysis_result = await langchain_service.analyze_news(title, content)

        # 추출된 키워드
        keywords = analysis_result.get("keywords", [])

        # 키워드 저장
        if keywords:
            await news_collection.update_one(
                {"_id": news["_id"]},
                {"$set": {"keywords": keywords, "updated_at": datetime.utcnow()}}
            )

        return {
            "news_id": str(news["_id"]),
            "key_phrases": keywords[:limit]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting key phrases: {str(e)}")

@router.post("/{news_id}/summarize")
async def summarize_news(
    news_id: str,
    max_length: int = Query(200, ge=50, le=500),
    db = Depends(get_mongodb_database),
    langchain_service = Depends(get_langchain_service_dep)
):
    """
    뉴스 내용을 요약합니다.
    """
    try:
        # 뉴스 존재 확인
        news_collection = db["news"]

        # ObjectId로 변환 시도
        try:
            news_id_obj = ObjectId(news_id)
            news = await news_collection.find_one({"_id": news_id_obj})
        except:
            # 실패하면 문자열 ID로 시도
            news = await news_collection.find_one({"_id": news_id})

        if not news:
            raise HTTPException(status_code=404, detail="News not found")

        # 이미 요약이 있고 길이가 적절하면 반환
        if "summary" in news and news["summary"] and len(news["summary"]) <= max_length:
            return {
                "news_id": str(news["_id"]),
                "summary": news["summary"]
            }

        # 텍스트 준비
        title = news.get("title", "")
        content = news.get("content", "")

        # LangChain 서비스로 요약 생성
        analysis_result = await langchain_service.analyze_news(title, content)

        # 생성된 요약
        summary = analysis_result.get("summary", "")

        # 길이 제한
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        # 요약 저장
        if summary:
            await news_collection.update_one(
                {"_id": news["_id"]},
                {"$set": {"summary": summary, "updated_at": datetime.utcnow()}}
            )

        return {
            "news_id": str(news["_id"]),
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error summarizing news: {str(e)}")
