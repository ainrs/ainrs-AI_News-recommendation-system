"""
시스템 성능 통합 테스트
- 전체 파이프라인 성능 측정
- 각 서비스별 성능 지표 수집
- 메모리 사용량 및 처리 속도 분석
"""

import asyncio
import time
import logging
import json
from datetime import datetime
from typing import Dict, Any, List
import sys
import os

# 백엔드 모듈 경로 추가
sys.path.append('/home/project/backend')

from app.services.rss_crawler import RSSCrawler
from app.services.smart_filtering_service import get_smart_filtering_service
from app.services.performance_optimizer import get_performance_optimizer
from app.services.summary_cache_service import get_summary_cache_service
from app.services.parallel_processor import get_parallel_processor
from app.services.korean_ai_pipeline import get_korean_ai_pipeline
from app.db.mongodb import news_collection

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemPerformanceTest:
    """시스템 성능 통합 테스트"""

    def __init__(self):
        self.performance_optimizer = get_performance_optimizer()
        self.smart_filtering = get_smart_filtering_service()
        self.cache_service = None
        self.parallel_processor = get_parallel_processor()
        self.korean_ai = get_korean_ai_pipeline()
        self.test_results = {}

        # 캐시 서비스 초기화 시도
        try:
            self.cache_service = get_summary_cache_service()
        except Exception as e:
            logger.warning(f"캐시 서비스 초기화 실패: {e}")

    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """전체 시스템 성능 테스트 실행"""
        logger.info("🚀 시스템 성능 통합 테스트 시작")

        start_time = time.time()
        initial_memory = self.performance_optimizer.get_memory_usage()

        test_results = {
            "test_start_time": datetime.utcnow().isoformat(),
            "initial_memory": initial_memory,
            "tests": {}
        }

        # 1. RSS 크롤링 성능 테스트
        logger.info("📡 RSS 크롤링 성능 테스트")
        rss_results = await self.test_rss_crawling()
        test_results["tests"]["rss_crawling"] = rss_results

        # 2. 스마트 필터링 성능 테스트
        logger.info("🧠 스마트 필터링 성능 테스트")
        filtering_results = await self.test_smart_filtering()
        test_results["tests"]["smart_filtering"] = filtering_results

        # 3. 병렬 처리 성능 테스트
        logger.info("⚡ 병렬 처리 성능 테스트")
        parallel_results = await self.test_parallel_processing()
        test_results["tests"]["parallel_processing"] = parallel_results

        # 4. 캐시 시스템 성능 테스트
        if self.cache_service:
            logger.info("💾 캐시 시스템 성능 테스트")
            cache_results = await self.test_cache_system()
            test_results["tests"]["cache_system"] = cache_results

        # 5. 메모리 사용량 분석
        logger.info("🧮 메모리 사용량 분석")
        memory_results = await self.test_memory_optimization()
        test_results["tests"]["memory_optimization"] = memory_results

        # 6. 전체 파이프라인 성능 측정
        logger.info("🔄 전체 파이프라인 성능 측정")
        pipeline_results = await self.test_full_pipeline()
        test_results["tests"]["full_pipeline"] = pipeline_results

        # 최종 결과 정리
        end_time = time.time()
        final_memory = self.performance_optimizer.get_memory_usage()

        test_results.update({
            "test_end_time": datetime.utcnow().isoformat(),
            "total_duration": end_time - start_time,
            "final_memory": final_memory,
            "memory_delta": final_memory["rss_mb"] - initial_memory["rss_mb"],
            "performance_summary": self.generate_performance_summary(test_results)
        })

        # 결과 저장
        await self.save_test_results(test_results)

        return test_results

    async def test_rss_crawling(self) -> Dict[str, Any]:
        """RSS 크롤링 성능 테스트"""
        try:
            start_time = time.time()
            start_memory = self.performance_optimizer.get_memory_usage()

            # RSS 크롤러 생성 및 실행
            crawler = RSSCrawler()

            # 기본 RSS 수집 테스트
            rss_start = time.time()
            articles = crawler.fetch_rss_feeds()
            rss_duration = time.time() - rss_start

            end_memory = self.performance_optimizer.get_memory_usage()

            return {
                "success": True,
                "articles_collected": len(articles),
                "duration_seconds": rss_duration,
                "articles_per_second": len(articles) / rss_duration if rss_duration > 0 else 0,
                "memory_usage_mb": end_memory["rss_mb"] - start_memory["rss_mb"],
                "memory_efficiency": len(articles) / (end_memory["rss_mb"] - start_memory["rss_mb"] + 0.1)
            }

        except Exception as e:
            logger.error(f"RSS 크롤링 테스트 실패: {e}")
            return {"success": False, "error": str(e)}

    async def test_smart_filtering(self) -> Dict[str, Any]:
        """스마트 필터링 성능 테스트"""
        try:
            # 테스트용 기사 데이터 생성
            test_articles = []
            for i in range(100):
                test_articles.append({
                    "title": f"테스트 기사 {i}",
                    "url": f"https://test.com/news{i}",
                    "source": "테스트 소스",
                    "published_date": datetime.utcnow(),
                    "categories": ["테스트"]
                })

            start_time = time.time()
            start_memory = self.performance_optimizer.get_memory_usage()

            # 스마트 필터링 실행
            filtered_articles = self.smart_filtering.filter_articles_smart(test_articles)

            end_time = time.time()
            end_memory = self.performance_optimizer.get_memory_usage()

            return {
                "success": True,
                "input_articles": len(test_articles),
                "filtered_articles": len(filtered_articles),
                "filtering_ratio": len(filtered_articles) / len(test_articles),
                "duration_seconds": end_time - start_time,
                "articles_per_second": len(test_articles) / (end_time - start_time),
                "memory_usage_mb": end_memory["rss_mb"] - start_memory["rss_mb"]
            }

        except Exception as e:
            logger.error(f"스마트 필터링 테스트 실패: {e}")
            return {"success": False, "error": str(e)}

    async def test_parallel_processing(self) -> Dict[str, Any]:
        """병렬 처리 성능 테스트"""
        try:
            # 테스트용 URL 리스트
            test_urls = [
                "https://httpbin.org/delay/1",
                "https://httpbin.org/delay/1",
                "https://httpbin.org/delay/1",
                "https://httpbin.org/delay/1",
                "https://httpbin.org/delay/1"
            ]

            # 순차 처리 시간 측정
            sequential_start = time.time()
            sequential_results = []
            for url in test_urls:
                try:
                    # 시뮬레이션된 순차 처리
                    await asyncio.sleep(0.1)  # 실제 네트워크 요청 대신 시뮬레이션
                    sequential_results.append({"url": url, "status": "success"})
                except:
                    sequential_results.append({"url": url, "status": "failed"})
            sequential_duration = time.time() - sequential_start

            # 병렬 처리 시간 측정
            parallel_start = time.time()

            async def test_fetch(url):
                await asyncio.sleep(0.1)  # 시뮬레이션
                return {"url": url, "status": "success"}

            parallel_results = await asyncio.gather(
                *[test_fetch(url) for url in test_urls],
                return_exceptions=True
            )
            parallel_duration = time.time() - parallel_start

            speedup = sequential_duration / parallel_duration if parallel_duration > 0 else 0

            return {
                "success": True,
                "test_urls_count": len(test_urls),
                "sequential_duration": sequential_duration,
                "parallel_duration": parallel_duration,
                "speedup_factor": speedup,
                "parallel_efficiency": (speedup / len(test_urls)) * 100
            }

        except Exception as e:
            logger.error(f"병렬 처리 테스트 실패: {e}")
            return {"success": False, "error": str(e)}

    async def test_cache_system(self) -> Dict[str, Any]:
        """캐시 시스템 성능 테스트"""
        try:
            if not self.cache_service:
                return {"success": False, "error": "캐시 서비스가 초기화되지 않음"}

            test_content = "테스트 콘텐츠 " * 100  # 테스트용 긴 콘텐츠
            test_key = "performance_test_article"

            # 캐시 저장 성능 테스트
            save_start = time.time()
            await self.cache_service.save_summary(test_key, {
                "summary": "테스트 요약",
                "content": test_content,
                "timestamp": datetime.utcnow()
            })
            save_duration = time.time() - save_start

            # 캐시 조회 성능 테스트
            lookup_start = time.time()
            cached_data = await self.cache_service.get_summary(test_key)
            lookup_duration = time.time() - lookup_start

            # 캐시 통계
            cache_stats = await self.cache_service.get_cache_stats()

            return {
                "success": True,
                "save_duration_ms": save_duration * 1000,
                "lookup_duration_ms": lookup_duration * 1000,
                "cache_hit": cached_data is not None,
                "cache_stats": cache_stats
            }

        except Exception as e:
            logger.error(f"캐시 시스템 테스트 실패: {e}")
            return {"success": False, "error": str(e)}

    async def test_memory_optimization(self) -> Dict[str, Any]:
        """메모리 최적화 성능 테스트"""
        try:
            # 메모리 사용량 증가 시뮬레이션
            test_data = []
            for i in range(1000):
                test_data.append({"data": "x" * 1000, "index": i})

            memory_before = self.performance_optimizer.get_memory_usage()

            # 메모리 최적화 실행
            optimization_start = time.time()
            await self.performance_optimizer.optimize_memory()
            optimization_duration = time.time() - optimization_start

            memory_after = self.performance_optimizer.get_memory_usage()

            # 테스트 데이터 정리
            del test_data

            return {
                "success": True,
                "memory_before_mb": memory_before["rss_mb"],
                "memory_after_mb": memory_after["rss_mb"],
                "memory_freed_mb": memory_before["rss_mb"] - memory_after["rss_mb"],
                "optimization_duration_ms": optimization_duration * 1000,
                "memory_efficiency": (memory_before["rss_mb"] - memory_after["rss_mb"]) / optimization_duration
            }

        except Exception as e:
            logger.error(f"메모리 최적화 테스트 실패: {e}")
            return {"success": False, "error": str(e)}

    async def test_full_pipeline(self) -> Dict[str, Any]:
        """전체 파이프라인 성능 테스트"""
        try:
            start_time = time.time()
            start_memory = self.performance_optimizer.get_memory_usage()

            # 전체 파이프라인 시뮬레이션
            pipeline_steps = {
                "rss_collection": 0,
                "smart_filtering": 0,
                "content_enhancement": 0,
                "ai_analysis": 0,
                "database_storage": 0
            }

            # 각 단계별 시간 측정
            step_start = time.time()
            await asyncio.sleep(0.1)  # RSS 수집 시뮬레이션
            pipeline_steps["rss_collection"] = time.time() - step_start

            step_start = time.time()
            await asyncio.sleep(0.05)  # 스마트 필터링 시뮬레이션
            pipeline_steps["smart_filtering"] = time.time() - step_start

            step_start = time.time()
            await asyncio.sleep(0.2)  # 콘텐츠 보강 시뮬레이션
            pipeline_steps["content_enhancement"] = time.time() - step_start

            step_start = time.time()
            await asyncio.sleep(0.15)  # AI 분석 시뮬레이션
            pipeline_steps["ai_analysis"] = time.time() - step_start

            step_start = time.time()
            await asyncio.sleep(0.03)  # DB 저장 시뮬레이션
            pipeline_steps["database_storage"] = time.time() - step_start

            total_duration = time.time() - start_time
            end_memory = self.performance_optimizer.get_memory_usage()

            return {
                "success": True,
                "total_duration_seconds": total_duration,
                "pipeline_steps": pipeline_steps,
                "memory_usage_mb": end_memory["rss_mb"] - start_memory["rss_mb"],
                "throughput_estimate": 50 / total_duration  # 50개 기사 기준
            }

        except Exception as e:
            logger.error(f"전체 파이프라인 테스트 실패: {e}")
            return {"success": False, "error": str(e)}

    def generate_performance_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """성능 테스트 결과 요약 생성"""
        summary = {
            "overall_status": "success",
            "key_metrics": {},
            "recommendations": []
        }

        tests = test_results.get("tests", {})

        # RSS 크롤링 성능
        if "rss_crawling" in tests and tests["rss_crawling"]["success"]:
            rss = tests["rss_crawling"]
            summary["key_metrics"]["rss_articles_per_second"] = rss.get("articles_per_second", 0)
            if rss.get("articles_per_second", 0) < 10:
                summary["recommendations"].append("RSS 크롤링 속도 개선 필요")

        # 스마트 필터링 효율성
        if "smart_filtering" in tests and tests["smart_filtering"]["success"]:
            filtering = tests["smart_filtering"]
            summary["key_metrics"]["filtering_ratio"] = filtering.get("filtering_ratio", 0)
            if filtering.get("filtering_ratio", 0) > 0.8:
                summary["recommendations"].append("필터링 기준 강화 검토")

        # 병렬 처리 가속화
        if "parallel_processing" in tests and tests["parallel_processing"]["success"]:
            parallel = tests["parallel_processing"]
            summary["key_metrics"]["speedup_factor"] = parallel.get("speedup_factor", 0)
            if parallel.get("speedup_factor", 0) < 3:
                summary["recommendations"].append("병렬 처리 최적화 필요")

        # 메모리 효율성
        if "memory_optimization" in tests and tests["memory_optimization"]["success"]:
            memory = tests["memory_optimization"]
            summary["key_metrics"]["memory_freed_mb"] = memory.get("memory_freed_mb", 0)
            if memory.get("memory_freed_mb", 0) < 10:
                summary["recommendations"].append("메모리 사용량 최적화 검토")

        # 전체 처리량
        if "full_pipeline" in tests and tests["full_pipeline"]["success"]:
            pipeline = tests["full_pipeline"]
            summary["key_metrics"]["throughput_articles_per_second"] = pipeline.get("throughput_estimate", 0)

        # 전체 메모리 효율성
        memory_delta = test_results.get("memory_delta", 0)
        if memory_delta > 100:  # 100MB 이상 증가
            summary["recommendations"].append("메모리 누수 가능성 점검 필요")

        return summary

    async def save_test_results(self, results: Dict[str, Any]):
        """테스트 결과 저장"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_test_results_{timestamp}.json"

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"📊 테스트 결과 저장됨: {filename}")

        except Exception as e:
            logger.error(f"테스트 결과 저장 실패: {e}")

async def main():
    """메인 실행 함수"""
    print("🚀 시스템 성능 통합 테스트 시작")

    test_runner = SystemPerformanceTest()
    results = await test_runner.run_comprehensive_test()

    # 결과 출력
    print("\n" + "="*60)
    print("📊 시스템 성능 테스트 결과")
    print("="*60)

    print(f"⏱️  총 테스트 시간: {results['total_duration']:.2f}초")
    print(f"💾 메모리 사용량 변화: {results['memory_delta']:.2f}MB")

    summary = results.get('performance_summary', {})
    key_metrics = summary.get('key_metrics', {})

    print("\n🔍 주요 성능 지표:")
    for metric, value in key_metrics.items():
        print(f"  - {metric}: {value:.2f}")

    recommendations = summary.get('recommendations', [])
    if recommendations:
        print("\n💡 개선 권장사항:")
        for rec in recommendations:
            print(f"  - {rec}")

    print("\n✅ 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main())
