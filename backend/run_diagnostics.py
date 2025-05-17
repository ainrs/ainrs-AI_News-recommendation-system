#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import logging
from datetime import datetime
import traceback
from urllib.parse import urlparse

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()

# MongoDB 연결 진단
async def check_mongodb_connection():
    logger.info("MongoDB 연결 확인 중...")

    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_db_name = os.getenv("MONGODB_DB_NAME", "news_recommendation")

    # URI 파싱하여 민감 정보 제거
    parsed_uri = urlparse(mongodb_uri)
    safe_uri = f"{parsed_uri.scheme}://{parsed_uri.netloc}"

    result = {
        "status": "unknown",
        "uri": safe_uri,
        "db_name": mongodb_db_name,
        "error": None,
        "collections": [],
        "counts": {}
    }

    try:
        # pymongo 가져오기
        import pymongo
        from pymongo import MongoClient
        logger.info(f"pymongo 버전: {pymongo.__version__}")

        # 연결 시도
        logger.info(f"MongoDB 연결 시도: {safe_uri}")
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)

        # 연결 테스트
        client.admin.command('ping')
        result["status"] = "connected"
        logger.info("MongoDB ping 성공!")

        # DB 정보 수집
        db = client[mongodb_db_name]
        result["collections"] = db.list_collection_names()
        logger.info(f"컬렉션 목록: {result['collections']}")

        # 각 컬렉션의 문서 수 확인
        for collection in result["collections"]:
            count = db[collection].count_documents({})
            result["counts"][collection] = count
            logger.info(f"컬렉션 '{collection}': {count}개 문서")

        # 추가 분석: 뉴스 컬렉션이 있는지 확인
        if "news" in result["collections"]:
            news_count = result["counts"].get("news", 0)
            if news_count == 0:
                logger.warning("news 컬렉션에 문서가 없습니다. 뉴스 데이터가 없습니다.")
                result["warnings"] = ["news 컬렉션에 데이터가 없습니다."]
        else:
            logger.warning("news 컬렉션이 존재하지 않습니다.")
            result["warnings"] = ["news 컬렉션이 존재하지 않습니다."]

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        logger.error(f"MongoDB 연결 실패: {str(e)}")

    return result

# OpenAI API 연결 진단
async def check_openai_connection():
    logger.info("OpenAI API 연결 확인 중...")

    api_key = os.getenv("OPENAI_API_KEY", "")
    # API 키 앞 부분만 표시 (보안)
    safe_key = api_key[:8] + "..." if api_key else ""

    result = {
        "status": "unknown",
        "api_key_set": bool(api_key),
        "api_key_prefix": safe_key,
        "error": None
    }

    if not api_key:
        result["status"] = "error"
        result["error"] = "API 키가 설정되지 않았습니다."
        logger.error("OpenAI API 키가 설정되지 않았습니다.")
        return result

    try:
        # OpenAI 가져오기
        from openai import OpenAI

        # 클라이언트 초기화
        client = OpenAI(api_key=api_key)

        # 간단한 API 호출로 연결 테스트
        logger.info("OpenAI 임베딩 테스트 시도 중...")
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input="테스트"
        )

        result["status"] = "connected"
        result["model"] = "text-embedding-3-small"
        result["dimensions"] = len(response.data[0].embedding)
        logger.info(f"OpenAI 임베딩 테스트 성공! 차원: {result['dimensions']}")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        logger.error(f"OpenAI API 연결 실패: {str(e)}")

    return result

# 벡터 저장소 확인
async def check_vector_stores():
    logger.info("벡터 저장소 확인 중...")

    data_dir = os.getenv("DATA_DIR", "./data")

    result = {
        "status": "unknown",
        "data_dir": data_dir,
        "error": None,
        "stores": {}
    }

    try:
        # 데이터 디렉토리 확인
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            logger.info(f"데이터 디렉토리 생성됨: {data_dir}")

        # Chroma 디렉토리 확인
        chroma_path = os.path.join(data_dir, "chroma")
        result["stores"]["chroma"] = {
            "path": chroma_path,
            "exists": os.path.exists(chroma_path)
        }

        # FAISS 디렉토리 확인
        faiss_path = os.path.join(data_dir, "faiss")
        result["stores"]["faiss"] = {
            "path": faiss_path,
            "exists": os.path.exists(faiss_path)
        }

        # 상태 결정
        if result["stores"]["chroma"]["exists"] or result["stores"]["faiss"]["exists"]:
            result["status"] = "exists"
            if result["stores"]["chroma"]["exists"] and result["stores"]["faiss"]["exists"]:
                result["status"] = "complete"
        else:
            result["status"] = "not_initialized"
            logger.warning("벡터 저장소가 초기화되지 않았습니다.")

        logger.info(f"벡터 저장소 상태: {result['status']}")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        logger.error(f"벡터 저장소 확인 실패: {str(e)}")

    return result

# 전체 진단 실행
async def run_diagnostics():
    logger.info("시스템 진단 시작...")

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "python_version": sys.version,
            "platform": sys.platform
        },
        "mongodb": await check_mongodb_connection(),
        "openai": await check_openai_connection(),
        "vector_stores": await check_vector_stores()
    }

    # 전체 상태 판단
    mongodb_ok = results["mongodb"]["status"] == "connected"
    openai_ok = results["openai"]["status"] == "connected"

    if mongodb_ok and openai_ok:
        results["overall_status"] = "operational"
    elif not mongodb_ok:
        results["overall_status"] = "critical"
    else:
        results["overall_status"] = "degraded"

    # 추천 사항 추가
    recommendations = []

    if not mongodb_ok:
        recommendations.append("MongoDB 연결 문제를 해결하세요. .env 파일의 MONGODB_URI를 확인하고 MongoDB 서버가 실행 중인지 확인하세요.")

    if not openai_ok:
        recommendations.append("OpenAI API 연결 문제를 해결하세요. .env 파일의 OPENAI_API_KEY가 올바르게 설정되었는지 확인하세요.")

    if results["vector_stores"]["status"] == "not_initialized":
        recommendations.append("벡터 저장소가 초기화되지 않았습니다. 앱을 실행하면 자동으로 초기화됩니다.")

    results["recommendations"] = recommendations

    return results

# 메인 함수
async def main():
    try:
        results = await run_diagnostics()

        # 결과 출력
        print("\n========== 진단 결과 ==========")
        print(f"전체 상태: {results['overall_status'].upper()}")
        print(f"MongoDB: {results['mongodb']['status']}")
        print(f"OpenAI API: {results['openai']['status']}")
        print(f"벡터 저장소: {results['vector_stores']['status']}")

        if results["recommendations"]:
            print("\n권장 조치:")
            for i, rec in enumerate(results["recommendations"], 1):
                print(f"{i}. {rec}")

        # JSON 파일로 저장
        with open("diagnostics_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n상세 결과가 diagnostics_results.json 파일에 저장되었습니다.")

    except Exception as e:
        logger.error(f"진단 중 오류 발생: {str(e)}")
        print(f"진단 실패: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
