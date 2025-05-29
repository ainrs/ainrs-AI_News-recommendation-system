"""
성능 최적화 서비스
- 메모리 사용량 최적화
- 배치 처리 개선
- 가비지 컬렉션 최적화
- 캐시 관리 최적화
"""

import gc
import logging
import psutil
import asyncio
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime, timedelta
from collections import deque
import sys
import tracemalloc
from functools import wraps
import time

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """성능 최적화 서비스"""

    def __init__(self):
        self.memory_threshold = 80  # 메모리 사용률 80% 이상 시 최적화
        self.batch_size = 25  # 기본 배치 크기 (20개에서 25개로 증가)
        self.max_batch_size = 50  # 최대 배치 크기
        self.processing_history = deque(maxlen=100)  # 최근 100개 처리 기록
        self.start_memory_trace()

    def start_memory_trace(self):
        """메모리 추적 시작"""
        try:
            tracemalloc.start()
            logger.info("메모리 추적 시작됨")
        except Exception as e:
            logger.warning(f"메모리 추적 시작 실패: {e}")

    def get_memory_usage(self) -> Dict[str, float]:
        """현재 메모리 사용량 조회"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

            return {
                "rss_mb": memory_info.rss / 1024 / 1024,  # 실제 메모리 사용량 (MB)
                "vms_mb": memory_info.vms / 1024 / 1024,  # 가상 메모리 사용량 (MB)
                "percent": memory_percent,
                "available_mb": psutil.virtual_memory().available / 1024 / 1024
            }
        except Exception as e:
            logger.error(f"메모리 사용량 조회 실패: {e}")
            return {"rss_mb": 0, "vms_mb": 0, "percent": 0, "available_mb": 0}

    def memory_monitor(self, func):
        """메모리 사용량 모니터링 데코레이터"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_memory = self.get_memory_usage()
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                end_memory = self.get_memory_usage()
                end_time = time.time()

                # 성능 통계 기록
                stats = {
                    "function": func.__name__,
                    "start_time": start_time,
                    "duration": end_time - start_time,
                    "memory_delta": end_memory["rss_mb"] - start_memory["rss_mb"],
                    "peak_memory": end_memory["rss_mb"]
                }
                self.processing_history.append(stats)

                # 메모리 사용량이 높으면 최적화 수행
                if end_memory["percent"] > self.memory_threshold:
                    await self.optimize_memory()

                return result

            except Exception as e:
                logger.error(f"{func.__name__} 실행 중 오류: {e}")
                await self.optimize_memory()  # 오류 시에도 메모리 정리
                raise

        return wrapper

    async def optimize_memory(self):
        """메모리 최적화 수행"""
        try:
            logger.info("메모리 최적화 시작")
            start_memory = self.get_memory_usage()

            # 1. 가비지 컬렉션 강제 실행
            collected = gc.collect()

            # 2. 세대별 가비지 컬렉션
            for generation in range(3):
                gc.collect(generation)

            # 3. 메모리 정리 후 상태 확인
            end_memory = self.get_memory_usage()
            freed_mb = start_memory["rss_mb"] - end_memory["rss_mb"]

            logger.info(f"메모리 최적화 완료: {collected}개 객체 수집, {freed_mb:.2f}MB 해제")

        except Exception as e:
            logger.error(f"메모리 최적화 실패: {e}")

    def get_optimal_batch_size(self, data_size: int, memory_usage: float) -> int:
        """현재 상황에 최적화된 배치 크기 계산"""
        try:
            # 메모리 사용률에 따른 배치 크기 조정
            if memory_usage > 85:
                # 메모리 사용률이 높으면 작은 배치
                optimal_size = max(10, self.batch_size // 2)
            elif memory_usage < 50:
                # 메모리 여유가 있으면 큰 배치
                optimal_size = min(self.max_batch_size, self.batch_size * 2)
            else:
                # 일반적인 상황에서는 기본 크기
                optimal_size = self.batch_size

            # 데이터 크기를 고려한 최종 조정
            optimal_size = min(optimal_size, data_size, self.max_batch_size)

            logger.info(f"최적 배치 크기 계산: {optimal_size} (메모리: {memory_usage:.1f}%, 데이터: {data_size}개)")
            return optimal_size

        except Exception as e:
            logger.error(f"배치 크기 계산 실패: {e}")
            return self.batch_size

    def batch_iterator(self, data: List[Any], batch_size: Optional[int] = None) -> Iterator[List[Any]]:
        """효율적인 배치 이터레이터"""
        if batch_size is None:
            memory_usage = self.get_memory_usage()["percent"]
            batch_size = self.get_optimal_batch_size(len(data), memory_usage)

        for i in range(0, len(data), batch_size):
            yield data[i:i + batch_size]

    async def process_in_batches(self, data: List[Any], process_func, max_concurrent: int = 3) -> List[Any]:
        """배치별 병렬 처리"""
        all_results = []
        memory_usage = self.get_memory_usage()["percent"]
        batch_size = self.get_optimal_batch_size(len(data), memory_usage)

        logger.info(f"배치 처리 시작: {len(data)}개 아이템, 배치 크기: {batch_size}")

        # 세마포어로 동시 처리 수 제한
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_batch(batch):
            async with semaphore:
                try:
                    return await process_func(batch)
                except Exception as e:
                    logger.error(f"배치 처리 실패: {e}")
                    return []

        # 배치별로 태스크 생성
        tasks = []
        for batch in self.batch_iterator(data, batch_size):
            tasks.append(process_batch(batch))

        # 배치들을 병렬로 처리
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 수집 및 오류 처리
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"배치 처리 중 예외: {result}")
            elif isinstance(result, list):
                all_results.extend(result)

        # 처리 완료 후 메모리 정리
        if self.get_memory_usage()["percent"] > self.memory_threshold:
            await self.optimize_memory()

        logger.info(f"배치 처리 완료: {len(all_results)}개 결과")
        return all_results

    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 조회"""
        try:
            if not self.processing_history:
                return {"message": "처리 기록 없음"}

            recent_records = list(self.processing_history)[-20:]  # 최근 20개

            avg_duration = sum(r["duration"] for r in recent_records) / len(recent_records)
            avg_memory_delta = sum(r["memory_delta"] for r in recent_records) / len(recent_records)
            max_memory = max(r["peak_memory"] for r in recent_records)

            current_memory = self.get_memory_usage()

            return {
                "current_memory": current_memory,
                "average_duration": avg_duration,
                "average_memory_delta": avg_memory_delta,
                "peak_memory_mb": max_memory,
                "batch_size": self.batch_size,
                "max_batch_size": self.max_batch_size,
                "processing_history_count": len(self.processing_history),
                "recent_functions": [r["function"] for r in recent_records[-5:]]
            }

        except Exception as e:
            logger.error(f"성능 통계 조회 실패: {e}")
            return {"error": str(e)}

    async def adaptive_delay(self, load_factor: float = 1.0):
        """부하에 따른 적응적 지연"""
        memory_usage = self.get_memory_usage()["percent"]

        if memory_usage > 90:
            # 메모리 사용률이 매우 높으면 긴 지연
            delay = 0.5 * load_factor
        elif memory_usage > 80:
            # 메모리 사용률이 높으면 중간 지연
            delay = 0.2 * load_factor
        elif memory_usage > 70:
            # 메모리 사용률이 보통이면 짧은 지연
            delay = 0.1 * load_factor
        else:
            # 메모리 여유가 있으면 지연 없음
            delay = 0

        if delay > 0:
            await asyncio.sleep(delay)

    def should_increase_batch_size(self) -> bool:
        """배치 크기를 증가시킬 수 있는지 판단"""
        memory_usage = self.get_memory_usage()["percent"]

        # 메모리 사용률이 낮고 현재 배치 크기가 최대가 아닌 경우
        return (memory_usage < 60 and
                self.batch_size < self.max_batch_size and
                len(self.processing_history) > 10)

    def increase_batch_size(self):
        """배치 크기 증가"""
        if self.should_increase_batch_size():
            old_size = self.batch_size
            self.batch_size = min(self.batch_size + 5, self.max_batch_size)
            logger.info(f"배치 크기 증가: {old_size} -> {self.batch_size}")

    def decrease_batch_size(self):
        """배치 크기 감소"""
        memory_usage = self.get_memory_usage()["percent"]
        if memory_usage > 85 and self.batch_size > 10:
            old_size = self.batch_size
            self.batch_size = max(self.batch_size - 5, 10)
            logger.info(f"배치 크기 감소: {old_size} -> {self.batch_size}")

# 전역 인스턴스
_performance_optimizer = None

def get_performance_optimizer() -> PerformanceOptimizer:
    """성능 최적화 서비스 인스턴스 가져오기"""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer
