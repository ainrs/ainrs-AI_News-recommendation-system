from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId

from app.db.mongodb import get_mongodb_database
from app.services.model_controller_service import ModelControllerService
from app.services.scheduler import SchedulerService
from app.services.summary_cache_service import get_summary_cache_service
from app.services.performance_optimizer import get_performance_optimizer

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}}
)

# Dependency for services
async def get_model_controller_service():
    return ModelControllerService()

async def get_scheduler_service():
    return SchedulerService()

# Admin middleware to check admin permission
async def verify_admin(
    user_id: str,
    db = Depends(get_mongodb_database)
):
    """
    관리자 권한을 확인합니다.
    """
    try:
        users_collection = db["users"]
        user = await users_collection.find_one({"_id": ObjectId(user_id)})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )

        return user
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid user ID or error: {str(e)}")

@router.get("/models", response_model=List[Dict[str, Any]])
async def get_all_models(
    user_id: str = Query(..., description="Admin user ID"),
    model_controller: ModelControllerService = Depends(get_model_controller_service),
    admin_user = Depends(verify_admin)
):
    """
    모든 AI 모델 정보를 가져옵니다.
    """
    try:
        models = await model_controller.get_all_models()
        return models
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching models: {str(e)}")

@router.post("/models/{model_id}/toggle", response_model=Dict[str, Any])
async def toggle_model_status(
    model_id: str,
    user_id: str = Query(..., description="Admin user ID"),
    enabled: bool = Body(...),
    model_controller: ModelControllerService = Depends(get_model_controller_service),
    admin_user = Depends(verify_admin)
):
    """
    AI 모델의 활성화 상태를 토글합니다.
    """
    try:
        updated_model = await model_controller.toggle_model(model_id, enabled)
        if not updated_model:
            raise HTTPException(status_code=404, detail="Model not found")

        return updated_model
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error toggling model status: {str(e)}")

@router.post("/models/{model_id}/update-settings", response_model=Dict[str, Any])
async def update_model_settings(
    model_id: str,
    user_id: str = Query(..., description="Admin user ID"),
    settings: Dict[str, Any] = Body(...),
    model_controller: ModelControllerService = Depends(get_model_controller_service),
    admin_user = Depends(verify_admin)
):
    """
    AI 모델의 설정을 업데이트합니다.
    """
    try:
        updated_model = await model_controller.update_model_settings(model_id, settings)
        if not updated_model:
            raise HTTPException(status_code=404, detail="Model not found")

        return updated_model
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating model settings: {str(e)}")

@router.get("/models/{model_id}/usage", response_model=Dict[str, Any])
async def get_model_usage(
    model_id: str,
    user_id: str = Query(..., description="Admin user ID"),
    days: int = Query(7, ge=1, le=90),
    model_controller: ModelControllerService = Depends(get_model_controller_service),
    admin_user = Depends(verify_admin),
    db = Depends(get_mongodb_database)
):
    """
    AI 모델 사용 통계를 가져옵니다.
    """
    try:
        # 날짜 범위 설정
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        usage_collection = db["model_usage"]

        # 일별 모델 사용 통계 쿼리
        pipeline = [
            {
                "$match": {
                    "model_id": model_id,
                    "timestamp": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$timestamp"},
                        "month": {"$month": "$timestamp"},
                        "day": {"$dayOfMonth": "$timestamp"}
                    },
                    "count": {"$sum": 1},
                    "avg_latency": {"$avg": "$latency"},
                    "total_tokens": {"$sum": "$tokens_used"},
                    "errors": {"$sum": {"$cond": [{"$eq": ["$status", "error"]}, 1, 0]}}
                }
            },
            {
                "$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}
            }
        ]

        cursor = usage_collection.aggregate(pipeline)

        daily_usage = []
        async for day in cursor:
            date_str = f"{day['_id']['year']}-{day['_id']['month']:02d}-{day['_id']['day']:02d}"
            daily_usage.append({
                "date": date_str,
                "count": day["count"],
                "avg_latency": day["avg_latency"],
                "total_tokens": day["total_tokens"],
                "errors": day["errors"],
                "success_rate": (day["count"] - day["errors"]) / day["count"] * 100 if day["count"] > 0 else 0
            })

        # 모델 정보 가져오기
        model = await model_controller.get_model_by_id(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        # 집계 정보 계산
        total_calls = sum(day["count"] for day in daily_usage)
        total_errors = sum(day["errors"] for day in daily_usage)
        total_tokens = sum(day["total_tokens"] for day in daily_usage)
        avg_latency = sum(day["avg_latency"] * day["count"] for day in daily_usage) / total_calls if total_calls > 0 else 0

        return {
            "model_id": model_id,
            "model_name": model.get("name", "Unknown"),
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": days
            },
            "summary": {
                "total_calls": total_calls,
                "total_errors": total_errors,
                "success_rate": (total_calls - total_errors) / total_calls * 100 if total_calls > 0 else 0,
                "total_tokens": total_tokens,
                "avg_latency": avg_latency
            },
            "daily_usage": daily_usage
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching model usage: {str(e)}")

@router.get("/stats/users", response_model=Dict[str, Any])
async def get_user_stats(
    user_id: str = Query(..., description="Admin user ID"),
    days: int = Query(30, ge=1, le=365),
    admin_user = Depends(verify_admin),
    db = Depends(get_mongodb_database)
):
    """
    사용자 통계를 가져옵니다.
    """
    try:
        # 날짜 범위 설정
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        users_collection = db["users"]
        interactions_collection = db["user_interactions"]

        # 총 사용자 수
        total_users = await users_collection.count_documents({})

        # 활성 사용자 수 (지정된 기간 내 상호작용이 있는 사용자)
        active_users_cursor = interactions_collection.aggregate([
            {
                "$match": {
                    "timestamp": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": "$user_id"
                }
            },
            {
                "$count": "active_count"
            }
        ])

        active_users_result = await active_users_cursor.to_list(length=1)
        active_users = active_users_result[0]["active_count"] if active_users_result else 0

        # 신규 사용자 수
        new_users = await users_collection.count_documents({
            "created_at": {"$gte": start_date, "$lte": end_date}
        })

        # 일별 사용자 상호작용 통계
        daily_interactions_cursor = interactions_collection.aggregate([
            {
                "$match": {
                    "timestamp": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$timestamp"},
                        "month": {"$month": "$timestamp"},
                        "day": {"$dayOfMonth": "$timestamp"},
                        "type": "$type"
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1, "_id.type": 1}
            }
        ])

        # 일별 데이터 구조화
        daily_data = {}
        async for interaction in daily_interactions_cursor:
            date_str = f"{interaction['_id']['year']}-{interaction['_id']['month']:02d}-{interaction['_id']['day']:02d}"

            if date_str not in daily_data:
                daily_data[date_str] = {
                    "date": date_str,
                    "view": 0,
                    "like": 0,
                    "share": 0,
                    "save": 0,
                    "comment": 0,
                    "total": 0
                }

            int_type = interaction["_id"]["type"]
            daily_data[date_str][int_type] = interaction["count"]
            daily_data[date_str]["total"] += interaction["count"]

        # 결과 반환
        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": days
            },
            "summary": {
                "total_users": total_users,
                "active_users": active_users,
                "new_users": new_users,
                "activity_rate": active_users / total_users * 100 if total_users > 0 else 0
            },
            "daily_interactions": list(daily_data.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user stats: {str(e)}")

@router.get("/stats/news", response_model=Dict[str, Any])
async def get_news_stats(
    user_id: str = Query(..., description="Admin user ID"),
    days: int = Query(30, ge=1, le=365),
    admin_user = Depends(verify_admin),
    db = Depends(get_mongodb_database)
):
    """
    뉴스 통계를 가져옵니다.
    """
    try:
        # 날짜 범위 설정
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        news_collection = db["news"]

        # 총 뉴스 수
        total_news = await news_collection.count_documents({})

        # 기간 내 새로운 뉴스 수
        new_news = await news_collection.count_documents({
            "published_at": {"$gte": start_date, "$lte": end_date}
        })

        # 카테고리별 뉴스 수
        category_stats_cursor = news_collection.aggregate([
            {
                "$match": {
                    "published_at": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$unwind": "$categories"
            },
            {
                "$group": {
                    "_id": "$categories",
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"count": -1}
            }
        ])

        categories = []
        async for category in category_stats_cursor:
            categories.append({
                "name": category["_id"],
                "count": category["count"]
            })

        # 소스별 뉴스 수
        source_stats_cursor = news_collection.aggregate([
            {
                "$match": {
                    "published_at": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": "$source",
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"count": -1}
            }
        ])

        sources = []
        async for source in source_stats_cursor:
            sources.append({
                "name": source["_id"],
                "count": source["count"]
            })

        # 일별 뉴스 통계
        daily_news_cursor = news_collection.aggregate([
            {
                "$match": {
                    "published_at": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$published_at"},
                        "month": {"$month": "$published_at"},
                        "day": {"$dayOfMonth": "$published_at"}
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}
            }
        ])

        daily_news = []
        async for day in daily_news_cursor:
            date_str = f"{day['_id']['year']}-{day['_id']['month']:02d}-{day['_id']['day']:02d}"
            daily_news.append({
                "date": date_str,
                "count": day["count"]
            })

        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": days
            },
            "summary": {
                "total_news": total_news,
                "new_news": new_news,
                "categories_count": len(categories),
                "sources_count": len(sources)
            },
            "categories": categories,
            "sources": sources,
            "daily_news": daily_news
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching news stats: {str(e)}")

@router.post("/scheduler/set-job", response_model=Dict[str, Any])
async def set_scheduler_job(
    user_id: str = Query(..., description="Admin user ID"),
    job_id: str = Body(...),
    job_type: str = Body(...),
    interval_minutes: int = Body(..., ge=1),
    enabled: bool = Body(...),
    scheduler_service: SchedulerService = Depends(get_scheduler_service),
    admin_user = Depends(verify_admin)
):
    """
    스케줄러 작업을 설정합니다.
    """
    try:
        result = await scheduler_service.set_job(
            job_id=job_id,
            job_type=job_type,
            interval_minutes=interval_minutes,
            enabled=enabled
        )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting scheduler job: {str(e)}")

@router.get("/scheduler/jobs", response_model=List[Dict[str, Any]])
async def get_scheduler_jobs(
    user_id: str = Query(..., description="Admin user ID"),
    scheduler_service: SchedulerService = Depends(get_scheduler_service),
    admin_user = Depends(verify_admin)
):
    """
    모든 스케줄러 작업을 가져옵니다.
    """
    try:
        jobs = await scheduler_service.get_all_jobs()
        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting scheduler jobs: {str(e)}")

@router.post("/scheduler/run-job-now", status_code=status.HTTP_202_ACCEPTED)
async def run_scheduler_job_now(
    user_id: str = Query(..., description="Admin user ID"),
    job_id: str = Body(...),
    scheduler_service: SchedulerService = Depends(get_scheduler_service),
    admin_user = Depends(verify_admin)
):
    """
    스케줄러 작업을 즉시 실행합니다.
    """
    try:
        await scheduler_service.run_job_now(job_id)

        return {"message": f"Job {job_id} triggered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering job: {str(e)}")

# ============ 캐시 관리 API ============

@router.get("/cache/stats")
async def get_cache_stats(
    user_id: str = Query(..., description="Admin user ID"),
    admin_user = Depends(verify_admin)
):
    """
    캐시 통계를 조회합니다.
    """
    try:
        cache_service = get_summary_cache_service()
        if not cache_service:
            return {"error": "캐시 서비스가 초기화되지 않았습니다"}

        stats = await cache_service.get_cache_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 통계 조회 오류: {str(e)}")

@router.post("/cache/cleanup")
async def cleanup_expired_cache(
    user_id: str = Query(..., description="Admin user ID"),
    admin_user = Depends(verify_admin)
):
    """
    만료된 캐시를 정리합니다.
    """
    try:
        cache_service = get_summary_cache_service()
        if not cache_service:
            return {"error": "캐시 서비스가 초기화되지 않았습니다"}

        deleted_count = await cache_service.cleanup_expired_cache()
        return {
            "success": True,
            "message": f"만료된 캐시 {deleted_count}개 정리 완료",
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 정리 오류: {str(e)}")

@router.delete("/cache/clear")
async def clear_all_cache(
    user_id: str = Query(..., description="Admin user ID"),
    confirm: bool = Query(False, description="확인 플래그"),
    admin_user = Depends(verify_admin)
):
    """
    모든 캐시를 삭제합니다. (개발/테스트용)
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="confirm=true로 설정해야 실행됩니다")

    try:
        cache_service = get_summary_cache_service()
        if not cache_service:
            return {"error": "캐시 서비스가 초기화되지 않았습니다"}

        deleted_count = await cache_service.clear_all_cache()
        return {
            "success": True,
            "message": f"전체 캐시 {deleted_count}개 삭제 완료",
            "deleted_count": deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 삭제 오류: {str(e)}")

# 성능 모니터링 엔드포인트들
@router.get("/performance/stats", response_model=Dict[str, Any])
async def get_performance_stats(
    user_id: str = Query(..., description="Admin user ID"),
    admin_user = Depends(verify_admin)
):
    """
    시스템 성능 통계를 조회합니다.
    """
    try:
        performance_optimizer = get_performance_optimizer()
        stats = performance_optimizer.get_performance_stats()
        return {
            "success": True,
            "performance_stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"성능 통계 조회 오류: {str(e)}")

@router.post("/performance/optimize", response_model=Dict[str, Any])
async def optimize_performance(
    user_id: str = Query(..., description="Admin user ID"),
    admin_user = Depends(verify_admin)
):
    """
    메모리 최적화를 수동으로 실행합니다.
    """
    try:
        performance_optimizer = get_performance_optimizer()
        memory_before = performance_optimizer.get_memory_usage()

        await performance_optimizer.optimize_memory()

        memory_after = performance_optimizer.get_memory_usage()
        memory_saved = memory_before["rss_mb"] - memory_after["rss_mb"]

        return {
            "success": True,
            "message": "메모리 최적화 완료",
            "memory_before_mb": memory_before["rss_mb"],
            "memory_after_mb": memory_after["rss_mb"],
            "memory_saved_mb": memory_saved,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"성능 최적화 오류: {str(e)}")

@router.get("/performance/memory", response_model=Dict[str, Any])
async def get_memory_usage(
    user_id: str = Query(..., description="Admin user ID"),
    admin_user = Depends(verify_admin)
):
    """
    현재 메모리 사용량을 조회합니다.
    """
    try:
        performance_optimizer = get_performance_optimizer()
        memory_usage = performance_optimizer.get_memory_usage()

        return {
            "success": True,
            "memory_usage": memory_usage,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메모리 사용량 조회 오류: {str(e)}")

@router.post("/performance/batch-size", response_model=Dict[str, Any])
async def update_batch_size(
    user_id: str = Query(..., description="Admin user ID"),
    action: str = Body(..., description="increase 또는 decrease"),
    admin_user = Depends(verify_admin)
):
    """
    배치 크기를 수동으로 조정합니다.
    """
    try:
        performance_optimizer = get_performance_optimizer()
        old_batch_size = performance_optimizer.batch_size

        if action == "increase":
            performance_optimizer.increase_batch_size()
        elif action == "decrease":
            performance_optimizer.decrease_batch_size()
        else:
            raise HTTPException(status_code=400, detail="action은 'increase' 또는 'decrease'여야 합니다")

        new_batch_size = performance_optimizer.batch_size

        return {
            "success": True,
            "message": f"배치 크기 조정 완료: {old_batch_size} -> {new_batch_size}",
            "old_batch_size": old_batch_size,
            "new_batch_size": new_batch_size,
            "max_batch_size": performance_optimizer.max_batch_size,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"배치 크기 조정 오류: {str(e)}")
