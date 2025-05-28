#!/usr/bin/env python3
"""
이 스크립트는 MongoDB 데이터베이스에서 null id 값을 가진 문서를 찾아
URL 기반의 해시값으로 ID를 설정합니다.
"""

import hashlib
import logging
from datetime import datetime
from app.db.mongodb import news_collection
from pymongo.errors import DuplicateKeyError, BulkWriteError

# 로깅 설정
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_null_ids():
    """null ID 값을 가진 문서를 찾아 고유한 ID를 설정합니다."""
    # null ID를 가진 문서 찾기
    null_id_docs = list(news_collection.find({"id": None}))
    logger.info(f"null id 값을 가진 문서 {len(null_id_docs)}개를 찾았습니다.")

    # null _id를 가진 문서 찾기
    null_id_docs.extend(list(news_collection.find({"_id": None})))
    logger.info(f"null _id 값을 가진 문서를 추가해 총 {len(null_id_docs)}개 문서를 처리합니다.")

    # 중복 제거
    unique_docs = {doc.get('url', f"unknown-{i}"): doc
                 for i, doc in enumerate(null_id_docs)}
    logger.info(f"중복 제거 후 {len(unique_docs)}개 고유 문서를 처리합니다.")

    fixed_count = 0
    error_count = 0

    for url, doc in unique_docs.items():
        try:
            if not url or url == "unknown":
                # URL이 없는 경우 타임스탬프 기반의 고유 ID 생성
                new_id = f"generated-{datetime.utcnow().timestamp()}-{fixed_count}"
            else:
                # URL 기반 해시 생성
                new_id = hashlib.md5(url.encode('utf-8')).hexdigest()

            # 원본 _id 저장 (있는 경우)
            original_id = doc.get('_id', None)

            # 새 ID로 업데이트
            update_result = news_collection.update_one(
                {"_id": original_id} if original_id else {"url": url},
                {"$set": {"_id": new_id, "id": new_id}}
            )

            if update_result.modified_count > 0:
                fixed_count += 1
                logger.info(f"문서 ID 수정 완료: {url[:30]}... -> {new_id}")
            else:
                # 이미 존재하는 경우 새 랜덤 ID 생성
                new_random_id = f"{new_id}-{datetime.utcnow().timestamp()}"
                update_result = news_collection.update_one(
                    {"_id": original_id} if original_id else {"url": url},
                    {"$set": {"_id": new_random_id, "id": new_random_id}}
                )

                if update_result.modified_count > 0:
                    fixed_count += 1
                    logger.info(f"문서 ID 수정 완료 (랜덤): {url[:30]}... -> {new_random_id}")
                else:
                    logger.warning(f"문서 ID 수정 실패: {url[:30]}...")
                    error_count += 1

        except (DuplicateKeyError, BulkWriteError) as e:
            logger.error(f"중복 키 오류 발생: {str(e)}")
            # 랜덤 접미사를 추가한 새 ID 생성
            try:
                new_random_id = f"{hashlib.md5(url.encode('utf-8')).hexdigest()}-{datetime.utcnow().timestamp()}"
                update_result = news_collection.update_one(
                    {"_id": doc.get('_id', None)} if doc.get('_id') else {"url": url},
                    {"$set": {"_id": new_random_id, "id": new_random_id}}
                )

                if update_result.modified_count > 0:
                    fixed_count += 1
                    logger.info(f"중복 해결 후 문서 ID 수정 완료: {url[:30]}... -> {new_random_id}")
                else:
                    error_count += 1
                    logger.error(f"중복 해결 시도 후에도 문서 ID 수정 실패: {url[:30]}...")
            except Exception as inner_error:
                error_count += 1
                logger.error(f"중복 해결 시도 중 오류 발생: {str(inner_error)}")

        except Exception as e:
            error_count += 1
            logger.error(f"문서 ID 수정 중 오류 발생: {str(e)}")

    logger.info(f"===== 작업 완료 =====")
    logger.info(f"총 처리 문서: {len(unique_docs)}개")
    logger.info(f"성공: {fixed_count}개")
    logger.info(f"실패: {error_count}개")

if __name__ == "__main__":
    logger.info("null ID 수정 스크립트를 시작합니다...")
    fix_null_ids()
    logger.info("스크립트 실행 완료")
