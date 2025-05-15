import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from threading import Lock

from app.services.rss_crawler import run_crawler
from app.services.embedding_service import get_embedding_service
from app.services.rag_service import get_rag_service
from app.db.mongodb import news_collection

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchedulerService:
    """Service for scheduling periodic tasks"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        """Implement singleton pattern"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SchedulerService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the scheduler service"""
        if self._initialized:
            return

        self.scheduler = BackgroundScheduler()
        self.jobs = {}
        self._initialized = True

        # Register default tasks
        self._register_default_tasks()

    def _register_default_tasks(self):
        """Register default scheduled tasks"""
        # Daily news crawling at 6 AM
        self.add_job(
            job_id="daily_news_crawl",
            func=self._crawl_news_task,
            trigger=CronTrigger(hour=6, minute=0),
            description="Daily news crawling at 6 AM"
        )

        # Process latest news articles every 4 hours
        self.add_job(
            job_id="process_latest_news",
            func=self._process_news_task,
            trigger=IntervalTrigger(hours=4),
            description="Process latest news every 4 hours"
        )

        # Index articles for RAG system daily at midnight
        self.add_job(
            job_id="index_articles_for_rag",
            func=self._index_articles_task,
            trigger=CronTrigger(hour=0, minute=0),
            description="Index articles for RAG system daily at midnight"
        )

    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started successfully")

    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shutdown")

    def add_job(self, job_id: str, func: Callable, trigger: Any, description: str = None, replace_existing: bool = True, **kwargs):
        """Add a new job to the scheduler"""
        job = self.scheduler.add_job(
            func=func,
            trigger=trigger,
            id=job_id,
            replace_existing=replace_existing,
            **kwargs
        )

        # next_run_time이 존재하는지 안전하게 확인
        next_run_time = getattr(job, 'next_run_time', None)

        self.jobs[job_id] = {
            "job": job,
            "description": description,
            "last_run": None,
            "next_run": next_run_time
        }

        logger.info(f"Added job: {job_id}, Next run: {next_run_time}")
        return job

    def modify_job(self, job_id: str, **kwargs):
        """Modify an existing job"""
        if job_id in self.jobs:
            self.scheduler.modify_job(job_id=job_id, **kwargs)
            job = self.scheduler.get_job(job_id)

            # next_run_time이 존재하는지 안전하게 확인
            next_run_time = getattr(job, 'next_run_time', None)
            self.jobs[job_id]["next_run"] = next_run_time
            logger.info(f"Modified job: {job_id}, Next run: {next_run_time}")
            return True
        return False

    def remove_job(self, job_id: str):
        """Remove a job from the scheduler"""
        if job_id in self.jobs:
            self.scheduler.remove_job(job_id)
            del self.jobs[job_id]
            logger.info(f"Removed job: {job_id}")
            return True
        return False

    def get_jobs(self):
        """Get all scheduled jobs"""
        jobs_info = []
        for job_id, info in self.jobs.items():
            job = self.scheduler.get_job(job_id)
            if job:
                # next_run_time 속성이 있는지 안전하게 확인
                next_run = None
                if hasattr(job, 'next_run_time') and job.next_run_time:
                    next_run = job.next_run_time.isoformat()

                jobs_info.append({
                    "id": job_id,
                    "description": info["description"],
                    "last_run": info["last_run"],
                    "next_run": next_run
                })
        return jobs_info

    def run_job_now(self, job_id: str):
        """Run a job immediately"""
        if job_id in self.jobs:
            job_info = self.jobs[job_id]
            job_func = self.scheduler.get_job(job_id).func

            try:
                logger.info(f"Running job immediately: {job_id}")
                job_func()
                job_info["last_run"] = datetime.utcnow()
                return True
            except Exception as e:
                logger.error(f"Error running job {job_id}: {e}")
                return False
        return False

    def _update_job_last_run(self, job_id: str):
        """Update the last run time of a job"""
        if job_id in self.jobs:
            self.jobs[job_id]["last_run"] = datetime.utcnow()

    # 비동기 API 메서드
    async def get_all_jobs(self) -> List[Dict[str, Any]]:
        """비동기 방식으로 모든 작업 목록을 가져옵니다."""
        return self.get_jobs()

    async def run_job_now_async(self, job_id: str) -> bool:
        """비동기 방식으로 작업을 즉시 실행합니다."""
        return self.run_job_now(job_id)

    async def set_job(self, job_id: str, job_type: str, interval_minutes: int, enabled: bool) -> Dict[str, Any]:
        """비동기 방식으로 작업을 설정합니다."""
        try:
            # 기존 작업을 제거
            if job_id in self.jobs:
                self.remove_job(job_id)

            # 작업 유형에 따른 함수 선택
            job_func = None
            if job_type == "news_crawl":
                job_func = self._crawl_news_task
            elif job_type == "process_news":
                job_func = self._process_news_task
            elif job_type == "index_articles":
                job_func = self._index_articles_task
            else:
                return {"success": False, "error": f"Unknown job type: {job_type}"}

            # 작업 스케쥴링
            if enabled:
                self.add_job(
                    job_id=job_id,
                    func=job_func,
                    trigger=IntervalTrigger(minutes=interval_minutes),
                    description=f"{job_type} job running every {interval_minutes} minutes"
                )

                job = self.scheduler.get_job(job_id)
                # next_run_time 속성이 있는지 안전하게 확인
                next_run = None
                if hasattr(job, 'next_run_time') and job.next_run_time:
                    next_run = job.next_run_time.isoformat()

                return {
                    "success": True,
                    "job_id": job_id,
                    "job_type": job_type,
                    "interval_minutes": interval_minutes,
                    "enabled": enabled,
                    "next_run": next_run
                }
            else:
                return {
                    "success": True,
                    "job_id": job_id,
                    "job_type": job_type,
                    "interval_minutes": interval_minutes,
                    "enabled": enabled,
                    "next_run": None
                }
        except Exception as e:
            logger.error(f"Error setting job {job_id}: {e}")
            return {"success": False, "error": str(e)}

    # Scheduled task implementations

    def _crawl_news_task(self):
        """Task to crawl news from RSS feeds"""
        try:
            logger.info("Starting scheduled news crawling task")
            start_time = time.time()

            # Run the crawler
            articles_count = run_crawler()

            end_time = time.time()
            logger.info(f"News crawling task completed. Crawled {articles_count} articles in {end_time - start_time:.2f} seconds")

            self._update_job_last_run("daily_news_crawl")
            return articles_count
        except Exception as e:
            logger.error(f"Error in news crawling task: {e}")
            return 0

    def _process_news_task(self):
        """Task to process latest unprocessed news"""
        try:
            logger.info("Starting scheduled news processing task")
            start_time = time.time()

            # Get embedding service
            embedding_service = get_embedding_service()

            # Find unprocessed news (no embedding_id or trust_score)
            unprocessed_news = list(news_collection.find({
                "$or": [
                    {"embedding_id": {"$exists": False}},
                    {"trust_score": {"$exists": False}},
                    {"sentiment_score": {"$exists": False}}
                ]
            }).limit(50))

            if not unprocessed_news:
                logger.info("No unprocessed news found")
                return 0

            logger.info(f"Processing {len(unprocessed_news)} news articles")

            # Process each article
            processed_count = 0
            for news in unprocessed_news:
                news_id = news["_id"]
                try:
                    # Process the news with embeddings, trust and sentiment analysis
                    success, results = embedding_service.process_news_pipeline(news_id)
                    if success:
                        processed_count += 1
                except Exception as e:
                    logger.error(f"Error processing news {news_id}: {e}")

            end_time = time.time()
            logger.info(f"News processing task completed. Processed {processed_count} articles in {end_time - start_time:.2f} seconds")

            self._update_job_last_run("process_latest_news")
            return processed_count
        except Exception as e:
            logger.error(f"Error in news processing task: {e}")
            return 0

    def _index_articles_task(self):
        """Task to index articles for RAG system"""
        try:
            logger.info("Starting scheduled article indexing task")
            start_time = time.time()

            # Get RAG service
            rag_service = get_rag_service()

            # Index articles from the last 2 days
            indexed_count = rag_service.index_news_articles(days=2, store_type="both")

            end_time = time.time()
            logger.info(f"Article indexing task completed. Indexed {indexed_count} articles in {end_time - start_time:.2f} seconds")

            self._update_job_last_run("index_articles_for_rag")
            return indexed_count
        except Exception as e:
            logger.error(f"Error in article indexing task: {e}")
            return 0


# Helper function to get scheduler service instance
def get_scheduler_service() -> SchedulerService:
    """Get scheduler service instance"""
    return SchedulerService()
