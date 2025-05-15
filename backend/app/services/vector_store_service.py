import os
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
import numpy as np
import json

from app.core.config import settings

# 로거 설정
logger = logging.getLogger(__name__)

class VectorStoreService:
    def __init__(self, collection_name: str = "news_articles", persist_directory: str = None,
                vector_db_type: str = "auto"):
        """
        고급 벡터 저장소 서비스 초기화 - 다양한 벡터 DB 지원 및 성능 최적화

        Args:
            collection_name: 컬렉션 이름
            persist_directory: 영구 저장 디렉토리 경로
            vector_db_type: 벡터 DB 타입 ("chroma", "faiss", "hybrid", "auto" 중 하나)
                - "chroma": ChromaDB 사용 (기본값)
                - "faiss": FAISS 벡터 DB 사용 (고성능)
                - "hybrid": 두 DB를 함께 사용 (고급 상황별 라우팅)
                - "auto": 컬렉션 크기 등에 따라 자동 선택
        """
        # 기본 디렉토리 설정
        if persist_directory is None:
            persist_directory = os.path.join(settings.DATA_DIR, "vector_storage")

        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.vector_db_type = vector_db_type

        # 메인 디렉토리 생성
        os.makedirs(persist_directory, exist_ok=True)

        # Chroma DB 설정
        self.chroma_directory = os.path.join(persist_directory, "chroma_db")
        os.makedirs(self.chroma_directory, exist_ok=True)

        # FAISS 설정
        self.faiss_directory = os.path.join(persist_directory, "faiss_db")
        os.makedirs(self.faiss_directory, exist_ok=True)

        # 성능 메트릭 저장용 캐시
        self.performance_metrics = {
            "chroma": {"query_times": [], "success_rate": 1.0},
            "faiss": {"query_times": [], "success_rate": 1.0}
        }

        # 벡터 데이터 통계
        self.stats = {
            "total_vectors": 0,
            "avg_vector_dim": 0,
            "last_updated": None
        }

        # Chroma 클라이언트 초기화
        try:
            # 향상된 설정으로 Chroma 클라이언트 생성
            self.chroma_client = chromadb.PersistentClient(
                path=self.chroma_directory,
                settings=Settings(
                    anonymized_telemetry=False,  # 텔레메트리 비활성화
                    allow_reset=True,            # 리셋 허용
                    is_persistent=True           # 영구 저장
                )
            )

            # 컬렉션 생성 또는 로드
            try:
                self.chroma_collection = self.chroma_client.get_collection(name=collection_name)
                print(f"ChromaDB 컬렉션 '{collection_name}' 로드됨")
            except ValueError:
                self.chroma_collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"description": "뉴스 기사 벡터 저장소"}
                )
                print(f"새 ChromaDB 컬렉션 '{collection_name}' 생성됨")

            self.has_chroma = True

        except Exception as chroma_error:
            # Collection [news_articles] does not exists 오류는 정상적인 첫 실행 시 발생하는 오류로 INFO 레벨 로깅
            if "Collection [news_articles] does not exists" in str(chroma_error):
                logger.info(f"ChromaDB 컬렉션이 아직 존재하지 않습니다. 이는 첫 실행 시 정상적인 동작입니다.")
                logger.info(f"FAISS를 대체 벡터 저장소로 사용합니다.")
            else:
                logger.error(f"ChromaDB 초기화 중 오류: {chroma_error}")
            self.has_chroma = False
            self.chroma_collection = None

        # FAISS 벡터 저장소 초기화 시도
        self.has_faiss = False
        self.faiss_index = None
        self.faiss_id_map = {}  # ID와 인덱스 매핑

        try:
            import faiss
            import numpy as np

            # FAISS 인덱스 파일 경로
            self.faiss_index_path = os.path.join(self.faiss_directory, f"{collection_name}.index")
            self.faiss_map_path = os.path.join(self.faiss_directory, f"{collection_name}_map.json")

            # 기존 인덱스 로드 또는 새로 생성
            if os.path.exists(self.faiss_index_path):
                try:
                    self.faiss_index = faiss.read_index(self.faiss_index_path)
                    # ID 매핑 로드
                    if os.path.exists(self.faiss_map_path):
                        with open(self.faiss_map_path, 'r') as f:
                            self.faiss_id_map = json.load(f)
                    print(f"FAISS 인덱스 로드됨: {self.faiss_index.ntotal} 벡터")
                    self.has_faiss = True
                except Exception as load_error:
                    print(f"FAISS 인덱스 로드 실패: {load_error}")
                    # 로드 실패 시 새 인덱스 생성
                    self.faiss_index = faiss.IndexFlatIP(1536)  # 코사인 유사도용 내적 인덱스
                    self.has_faiss = True
            else:
                # 새 인덱스 생성 - 기본 OpenAI 임베딩 차원(1536) 사용
                self.faiss_index = faiss.IndexFlatIP(1536)  # 코사인 유사도용 내적 인덱스
                logger.info(f"✅ 새 FAISS 인덱스 생성됨")
                self.has_faiss = True

        except ImportError:
            print("FAISS 라이브러리를 찾을 수 없습니다. FAISS 벡터 저장소 비활성화됨.")
        except Exception as faiss_error:
            print(f"FAISS 초기화 중 오류: {faiss_error}")

        # 벡터 DB 선택 로직 설정
        self.active_db = self._select_active_db(vector_db_type)
        logger.info(f"✅ 활성 벡터 DB: {self.active_db}")

    def _select_active_db(self, vector_db_type: str) -> str:
        """DB 타입에 따라 활성화할 벡터 DB 결정"""
        if vector_db_type == "chroma" and self.has_chroma:
            return "chroma"
        elif vector_db_type == "faiss" and self.has_faiss:
            return "faiss"
        elif vector_db_type == "hybrid" and self.has_chroma and self.has_faiss:
            return "hybrid"
        elif vector_db_type == "auto":
            # 자동 선택 로직
            if self.has_faiss and self.stats["total_vectors"] > 10000:
                # 대용량 데이터의 경우 FAISS 선택
                return "faiss"
            elif self.has_chroma:
                # 소규모 또는 기본 선택
                return "chroma"
            elif self.has_faiss:
                return "faiss"

        # 기본값: 사용 가능한 첫 번째 DB
        if self.has_chroma:
            return "chroma"
        elif self.has_faiss:
            return "faiss"
        else:
            raise ValueError("사용 가능한 벡터 DB가 없습니다.")

    async def add_documents(self, documents: List[Dict[str, Any]], embeddings: List[List[float]], ids: List[str]) -> Dict[str, Any]:
        """
        문서와 임베딩을 벡터 저장소에 추가합니다.
        여러 벡터 DB에 동시에 추가할 수 있는 고급 기능을 제공합니다.

        Args:
            documents: 문서 메타데이터 목록 (딕셔너리 형태)
            embeddings: 문서 임베딩 목록
            ids: 문서 ID 목록

        Returns:
            Dict[str, Any]: 저장 결과 요약 (성공/실패 카운트 등)
        """
        if not documents or not embeddings or not ids:
            print("추가할 문서가 없습니다.")
            return {"success": False, "error": "추가할 문서가 없습니다.", "count": 0}

        result = {"success": False, "chroma_success": False, "faiss_success": False, "count": 0}
        doc_count = len(documents)

        # 임베딩 및 ID 길이 확인
        if len(embeddings) != doc_count or len(ids) != doc_count:
            error_msg = f"문서({doc_count}), 임베딩({len(embeddings)}), ID({len(ids)}) 개수가 일치하지 않습니다."
            print(error_msg)
            return {"success": False, "error": error_msg, "count": 0}

        # 벡터 차원 검증 및 통계 업데이트
        if embeddings and isinstance(embeddings[0], list) and len(embeddings[0]) > 0:
            vector_dim = len(embeddings[0])
            self.stats["avg_vector_dim"] = vector_dim

        # 1. ChromaDB에 추가
        if self.has_chroma and (self.active_db == "chroma" or self.active_db == "hybrid"):
            try:
                # 메타데이터를 JSON 문자열로 변환
                metadatas = []
                for doc in documents:
                    # ChromaDB는 메타데이터에 중첩된 딕셔너리를 지원하지 않으므로 평면화
                    metadata = {}
                    for key, value in doc.items():
                        if isinstance(value, (dict, list)):
                            metadata[key] = json.dumps(value)
                        elif value is None:
                            # None 값 처리
                            metadata[key] = ""
                        else:
                            metadata[key] = value
                    metadatas.append(metadata)

                # 문서 내용 추출
                document_texts = [doc.get("content", "") or "빈 내용" for doc in documents]

                # ChromaDB에 추가
                self.chroma_collection.add(
                    embeddings=embeddings,
                    documents=document_texts,
                    metadatas=metadatas,
                    ids=ids
                )
                print(f"{doc_count}개 문서가 ChromaDB에 추가됨")
                result["chroma_success"] = True

            except Exception as chroma_error:
                print(f"ChromaDB에 문서 추가 중 오류 발생: {chroma_error}")
                result["chroma_error"] = str(chroma_error)

        # 2. FAISS에 추가
        if self.has_faiss and (self.active_db == "faiss" or self.active_db == "hybrid"):
            try:
                import numpy as np
                import faiss

                # 임베딩을 numpy 배열로 변환
                embeddings_array = np.array(embeddings, dtype=np.float32)

                # 현재 인덱스 개수 - 새 벡터 위치 시작점
                current_index = self.faiss_index.ntotal

                # FAISS 인덱스에 추가
                self.faiss_index.add(embeddings_array)

                # ID 매핑 업데이트
                for i, doc_id in enumerate(ids):
                    self.faiss_id_map[doc_id] = current_index + i

                    # 메타데이터 저장 (선택적)
                    if hasattr(self, 'faiss_metadata') and self.faiss_metadata is not None:
                        # 메타데이터 딕셔너리가 있으면 업데이트
                        self.faiss_metadata[doc_id] = {
                            "content": documents[i].get("content", ""),
                            "title": documents[i].get("title", ""),
                            "source": documents[i].get("source", ""),
                            "url": documents[i].get("url", ""),
                            "published_date": str(documents[i].get("published_date", "")),
                            "index": current_index + i
                        }

                # 인덱스 저장
                faiss.write_index(self.faiss_index, self.faiss_index_path)

                # ID 매핑 저장
                with open(self.faiss_map_path, 'w') as f:
                    json.dump(self.faiss_id_map, f)

                print(f"{doc_count}개 문서가 FAISS에 추가됨")
                result["faiss_success"] = True

            except Exception as faiss_error:
                print(f"FAISS에 문서 추가 중 오류 발생: {faiss_error}")
                result["faiss_error"] = str(faiss_error)

        # 통계 업데이트
        self.stats["total_vectors"] += doc_count
        self.stats["last_updated"] = datetime.now().isoformat()

        # 최종 결과
        result["success"] = result["chroma_success"] or result["faiss_success"]
        result["count"] = doc_count
        return result

    async def search_by_vector(self, query_vector: List[float], limit: int = 10,
                             hybrid_mode: str = "merge", min_similarity: float = 0.65) -> List[Dict[str, Any]]:
        """
        쿼리 벡터와 가장 유사한 문서를 검색합니다.
        다양한 벡터 DB를 활용하여 최적의 검색 결과를 제공합니다.

        Args:
            query_vector: 쿼리 임베딩 벡터
            limit: 검색 결과 제한 수
            hybrid_mode: 하이브리드 검색 모드 ("merge", "chroma_first", "faiss_first", "best_score")
            min_similarity: 최소 유사도 점수 (0-1 범위, 이보다 낮은 유사도는 필터링)

        Returns:
            List[Dict[str, Any]]: 검색 결과 목록
        """
        # 벡터 유효성 검증
        if not query_vector or not isinstance(query_vector, list) or len(query_vector) < 10:
            print("유효하지 않은 쿼리 벡터입니다.")
            return []

        start_time = time.time()
        formatted_results = []
        chroma_results = []
        faiss_results = []

        # 활성 DB에 따른 검색 전략 선택
        if self.active_db == "chroma" and self.has_chroma:
            # ChromaDB만 사용하는 경우
            chroma_results = await self._search_with_chroma(query_vector, limit)
            formatted_results = chroma_results

        elif self.active_db == "faiss" and self.has_faiss:
            # FAISS만 사용하는 경우
            faiss_results = await self._search_with_faiss(query_vector, limit)
            formatted_results = faiss_results

        elif self.active_db == "hybrid" and self.has_chroma and self.has_faiss:
            # 하이브리드 모드: 두 엔진 모두 사용
            # 병렬 검색 수행 (asyncio)
            import asyncio
            chroma_task = asyncio.create_task(self._search_with_chroma(query_vector, limit))
            faiss_task = asyncio.create_task(self._search_with_faiss(query_vector, limit))

            # 모든 검색 결과 기다림
            await asyncio.wait([chroma_task, faiss_task])

            # 결과 가져오기
            chroma_results = await chroma_task
            faiss_results = await faiss_task

            # 하이브리드 모드에 따른 결과 병합
            if hybrid_mode == "merge":
                # 두 결과를 합치고 중복 제거 (ID 기준)
                all_results = chroma_results + faiss_results
                seen_ids = set()
                unique_results = []

                for result in all_results:
                    if result["id"] not in seen_ids:
                        seen_ids.add(result["id"])
                        unique_results.append(result)

                # 유사도 기준 재정렬
                formatted_results = sorted(unique_results, key=lambda x: x.get("similarity", 0), reverse=True)[:limit]

            elif hybrid_mode == "chroma_first":
                # ChromaDB 결과를 우선하고, 부족한 경우 FAISS로 보완
                formatted_results = chroma_results

                if len(formatted_results) < limit:
                    existing_ids = {r["id"] for r in formatted_results}
                    for faiss_result in faiss_results:
                        if faiss_result["id"] not in existing_ids and len(formatted_results) < limit:
                            formatted_results.append(faiss_result)

            elif hybrid_mode == "faiss_first":
                # FAISS 결과를 우선하고, 부족한 경우 ChromaDB로 보완
                formatted_results = faiss_results

                if len(formatted_results) < limit:
                    existing_ids = {r["id"] for r in formatted_results}
                    for chroma_result in chroma_results:
                        if chroma_result["id"] not in existing_ids and len(formatted_results) < limit:
                            formatted_results.append(chroma_result)

            elif hybrid_mode == "best_score":
                # 모든 결과를 모으고 최고 점수 기준으로 선택
                all_results = {}

                # 모든 결과 수집
                for result in chroma_results + faiss_results:
                    doc_id = result["id"]
                    similarity = result.get("similarity", 0)

                    # 이미 존재하는 ID면 더 높은 유사도 점수로 업데이트
                    if doc_id in all_results:
                        if similarity > all_results[doc_id].get("similarity", 0):
                            all_results[doc_id] = result
                    else:
                        all_results[doc_id] = result

                # 유사도 기준 상위 N개 선택
                formatted_results = sorted(all_results.values(), key=lambda x: x.get("similarity", 0), reverse=True)[:limit]

        else:
            # 사용 가능한 벡터 DB가 없는 경우
            print("사용 가능한 벡터 DB가 없습니다.")
            return []

        # 최소 유사도 필터링
        if min_similarity > 0:
            formatted_results = [result for result in formatted_results
                                if result.get("similarity", 0) >= min_similarity]

        # 성능 측정 및 디버깅
        search_time = time.time() - start_time
        print(f"벡터 검색 완료: {len(formatted_results)}개 결과, {search_time:.3f}초 소요")

        # 메트릭 업데이트
        if chroma_results:
            self.performance_metrics["chroma"]["query_times"].append(search_time)
            # 최대 100개 기록만 유지
            if len(self.performance_metrics["chroma"]["query_times"]) > 100:
                self.performance_metrics["chroma"]["query_times"].pop(0)

        if faiss_results:
            self.performance_metrics["faiss"]["query_times"].append(search_time)
            if len(self.performance_metrics["faiss"]["query_times"]) > 100:
                self.performance_metrics["faiss"]["query_times"].pop(0)

        return formatted_results

    async def _search_with_chroma(self, query_vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """
        ChromaDB를 사용한 벡터 검색을 수행합니다.

        Args:
            query_vector: 쿼리 임베딩 벡터
            limit: 검색 결과 제한 수

        Returns:
            List[Dict[str, Any]]: 검색 결과
        """
        formatted_results = []

        try:
            # ChromaDB 검색 실행
            results = self.chroma_collection.query(
                query_embeddings=[query_vector],
                n_results=limit
            )

            # 결과 형식 변환
            for i in range(len(results["ids"][0])):
                try:
                    doc_id = results["ids"][0][i]
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    document = results["documents"][0][i] if results["documents"] else ""
                    distance = results["distances"][0][i] if "distances" in results and results["distances"] else 0.0

                    # 일부 메타데이터는 문자열로 변환된 JSON일 수 있음 - 복원 시도
                    restored_metadata = {}
                    for key, value in metadata.items():
                        if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                            try:
                                restored_metadata[key] = json.loads(value)
                            except json.JSONDecodeError:
                                restored_metadata[key] = value
                        else:
                            restored_metadata[key] = value

                    # 코사인 유사도로 변환 (ChromaDB의 거리는 L2 거리이므로 변환 필요)
                    similarity = 1.0 - (distance / 2.0) if distance <= 2.0 else 0.0

                    formatted_results.append({
                        "id": doc_id,
                        "metadata": restored_metadata,
                        "content": document,
                        "distance": distance,
                        "similarity": similarity,
                        "source": "chroma",
                        "rank": i + 1
                    })
                except Exception as e:
                    print(f"ChromaDB 결과 {i} 처리 중 오류 발생: {e}")
                    continue

            # 성공률 업데이트
            self.performance_metrics["chroma"]["success_rate"] = 1.0

        except Exception as e:
            print(f"ChromaDB 검색 중 오류 발생: {e}")
            # 실패 시 성공률 감소
            self.performance_metrics["chroma"]["success_rate"] *= 0.9
            return []

        return formatted_results

    async def _search_with_faiss(self, query_vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """
        FAISS를 사용한 벡터 검색을 수행합니다.

        Args:
            query_vector: 쿼리 임베딩 벡터
            limit: 검색 결과 제한 수

        Returns:
            List[Dict[str, Any]]: 검색 결과
        """
        if not self.has_faiss or not self.faiss_index:
            return []

        formatted_results = []

        try:
            import numpy as np
            import faiss

            # 쿼리 벡터를 numpy 배열로 변환
            query_np = np.array([query_vector], dtype=np.float32)

            # FAISS 검색 수행
            # 결과: distances(내적 유사도), indices(인덱스)
            distances, indices = self.faiss_index.search(query_np, limit)

            # ID 맵으로 원본 문서 ID 찾기
            id_map_rev = {v: k for k, v in self.faiss_id_map.items()}

            # 결과 형식화
            for i in range(len(indices[0])):
                idx = indices[0][i]

                # 유효한 인덱스 확인
                if idx == -1 or idx >= self.faiss_index.ntotal:
                    continue

                # 내적 점수를 코사인 유사도로 변환 (-1 ~ 1 범위)
                similarity = float(distances[0][i])
                # 내적이 음수면 유사도가 낮은 것
                if similarity < 0:
                    similarity = 0
                # 정규화: 0-1 범위로 조정 (대부분 유사도가 0.5-1 사이에 분포)
                similarity = min(1.0, max(0.0, similarity))

                # 원본 문서 ID 찾기
                doc_id = id_map_rev.get(idx, f"unknown_{idx}")

                # 결과 추가
                result = {
                    "id": doc_id,
                    "similarity": similarity,
                    "source": "faiss",
                    "rank": i + 1,
                }

                # FAISS 메타데이터가 있으면 추가
                if hasattr(self, 'faiss_metadata') and self.faiss_metadata is not None and doc_id in self.faiss_metadata:
                    result["metadata"] = self.faiss_metadata[doc_id]
                    result["content"] = self.faiss_metadata[doc_id].get("content", "")

                formatted_results.append(result)

            # 성공률 업데이트
            self.performance_metrics["faiss"]["success_rate"] = 1.0

        except Exception as e:
            print(f"FAISS 검색 중 오류 발생: {e}")
            # 실패 시 성공률 감소
            self.performance_metrics["faiss"]["success_rate"] *= 0.9
            return []

        return formatted_results

    async def search_by_text(self, query_text: str, embedding_service, limit: int = 10,
                          task_type: str = "search", search_mode: str = "semantic",
                          hybrid_mode: str = "merge", min_similarity: float = 0.65) -> List[Dict[str, Any]]:
        """
        텍스트 쿼리로 유사한 문서를 검색합니다.
        고급 검색 기능을 제공합니다.

        Args:
            query_text: 쿼리 텍스트
            embedding_service: 임베딩 서비스 인스턴스
            limit: 검색 결과 제한 수
            task_type: 임베딩 생성 목적 ("search", "news", "recommendation" 등)
            search_mode: 검색 모드 ("semantic", "keyword", "hybrid" 중 하나)
            hybrid_mode: 하이브리드 검색 모드 ("merge", "chroma_first", "faiss_first", "best_score")
            min_similarity: 최소 유사도 점수 (0-1 범위)

        Returns:
            List[Dict[str, Any]]: 검색 결과 목록
        """
        if not query_text or not query_text.strip():
            print("검색어가 비어 있습니다.")
            return []

        # 텍스트 전처리
        clean_query = query_text.strip()

        # 키워드 기반 검색인 경우 키워드 추출
        keywords = []
        if search_mode in ["keyword", "hybrid"]:
            # 간단한 키워드 추출 (공백 기준)
            keywords = [k.strip() for k in clean_query.split() if len(k.strip()) > 1]

        # 검색 모드 기반으로 결과 구하기
        results = []

        if search_mode in ["semantic", "hybrid"]:
            # 1. 시맨틱 검색 (임베딩 기반)
            # 쿼리 텍스트 임베딩 생성 (검색에 최적화된 임베딩 모델 사용)
            query_embedding = await embedding_service.get_embedding(clean_query, task_type=task_type)

            # 임베딩으로 벡터 검색
            semantic_results = await self.search_by_vector(
                query_vector=query_embedding,
                limit=limit,
                hybrid_mode=hybrid_mode,
                min_similarity=min_similarity
            )

            if search_mode == "semantic":
                return semantic_results  # 시맨틱 검색만 사용하는 경우

            results.extend(semantic_results)

        if search_mode in ["keyword", "hybrid"] and keywords:
            # 2. 키워드 기반 검색 (메타데이터에서 키워드 매칭)
            # 각 벡터 DB 엔진에 맞게 키워드 검색 수행
            keyword_results = await self._search_by_keywords(keywords, limit)

            if search_mode == "keyword":
                return keyword_results  # 키워드 검색만 사용하는 경우

            if keyword_results:
                # 기존 결과와 병합
                all_results = results + keyword_results
                # 중복 제거 및 재정렬
                seen_ids = set()
                unique_results = []

                for result in all_results:
                    doc_id = result["id"]
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        unique_results.append(result)

                # 유사도 기준 정렬
                results = sorted(unique_results, key=lambda x: x.get("similarity", 0), reverse=True)

                # 결과 수 제한
                if len(results) > limit:
                    results = results[:limit]

        # 검색 히스토리나 통계 업데이트 (선택적)
        await self._update_search_stats(query_text, len(results))

        return results

    async def _search_by_keywords(self, keywords: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        키워드 기반 검색을 수행합니다.

        Args:
            keywords: 검색 키워드 목록
            limit: 검색 결과 제한 수

        Returns:
            List[Dict[str, Any]]: 검색 결과 목록
        """
        if not keywords:
            return []

        results = []

        # 1. ChromaDB를 통한 키워드 검색
        if self.has_chroma:
            try:
                # ChromaDB의 where 필터 사용
                # 메타데이터에서 키워드 검색
                for keyword in keywords:
                    # 제목에서 검색
                    title_filter = {"title": {"$contains": keyword}}
                    title_results = self.chroma_collection.get(
                        where=title_filter,
                        limit=limit
                    )

                    # 컨텐츠에서 검색 (where 필터가 있는 경우)
                    content_filter = {"content": {"$contains": keyword}}
                    content_results = self.chroma_collection.get(
                        where=content_filter,
                        limit=limit
                    )

                    # 검색 결과 처리
                    for i in range(len(title_results.get("ids", []))):
                        doc_id = title_results["ids"][i]
                        metadata = title_results["metadatas"][i] if "metadatas" in title_results else {}
                        document = title_results["documents"][i] if "documents" in title_results else ""

                        # 중요 메타데이터 추출
                        title = metadata.get("title", "")
                        source = metadata.get("source", "")

                        # 키워드 일치 점수 계산 (단순 버전)
                        keyword_score = 0.0
                        if title and keyword.lower() in title.lower():
                            # 제목에 키워드가 있으면 높은 점수
                            keyword_score = 0.9
                        elif document and keyword.lower() in document.lower():
                            # 내용에 키워드가 있으면 중간 점수
                            keyword_score = 0.7

                        results.append({
                            "id": doc_id,
                            "metadata": metadata,
                            "content": document,
                            "similarity": keyword_score,
                            "source": "keyword_chroma",
                            "match_type": "title",
                            "keyword": keyword
                        })

                    # 내용 검색 결과도 추가
                    for i in range(len(content_results.get("ids", []))):
                        doc_id = content_results["ids"][i]
                        # 이미 추가된 ID는 제외
                        if any(r["id"] == doc_id for r in results):
                            continue

                        metadata = content_results["metadatas"][i] if "metadatas" in content_results else {}
                        document = content_results["documents"][i] if "documents" in content_results else ""

                        results.append({
                            "id": doc_id,
                            "metadata": metadata,
                            "content": document,
                            "similarity": 0.6,  # 내용 검색은 낮은 기본 점수
                            "source": "keyword_chroma",
                            "match_type": "content",
                            "keyword": keyword
                        })

            except Exception as e:
                print(f"ChromaDB 키워드 검색 중 오류 발생: {e}")

        # 결과 정렬 및 상위 N개 선택
        results = sorted(results, key=lambda x: x.get("similarity", 0), reverse=True)
        return results[:limit]

    async def _update_search_stats(self, query_text: str, result_count: int):
        """
        검색 통계를 업데이트합니다. (캐싱 및 분석 목적)

        Args:
            query_text: 검색어
            result_count: 검색 결과 수
        """
        # 간단한 로깅만 수행 (실제로는 DB에 저장 가능)
        print(f"검색 통계 업데이트: '{query_text}' - {result_count}개 결과")

        # 검색 히스토리 저장 (선택적)
        try:
            from app.db.mongodb import get_mongodb_database
            db = await get_mongodb_database()
            search_history = db["search_history"]

            await search_history.insert_one({
                "query": query_text,
                "result_count": result_count,
                "timestamp": datetime.now(),
                "vector_db": self.active_db
            })

        except Exception as e:
            print(f"검색 통계 저장 중 오류: {e}")
            # 통계 저장은 중요하지 않으므로 실패해도 무시

    async def delete_document(self, doc_id: str) -> bool:
        """
        문서 ID로 문서를 삭제합니다.

        Args:
            doc_id: 삭제할 문서 ID

        Returns:
            성공 여부
        """
        try:
            self.collection.delete(ids=[doc_id])
            print(f"문서 삭제됨: {doc_id}")
            return True
        except Exception as e:
            print(f"문서 삭제 중 오류 발생: {e}")
            return False

    async def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        문서 ID로 문서를 가져옵니다.

        Args:
            doc_id: 문서 ID

        Returns:
            문서 데이터 또는 None
        """
        try:
            result = self.collection.get(ids=[doc_id])

            if not result["ids"]:
                return None

            metadata = result["metadatas"][0] if result["metadatas"] else {}
            document = result["documents"][0] if result["documents"] else ""

            # 일부 메타데이터는 문자열로 변환된 JSON일 수 있음 - 복원 시도
            restored_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                    try:
                        restored_metadata[key] = json.loads(value)
                    except json.JSONDecodeError:
                        restored_metadata[key] = value
                else:
                    restored_metadata[key] = value

            return {
                "id": doc_id,
                "metadata": restored_metadata,
                "content": document
            }

        except Exception as e:
            print(f"문서 조회 중 오류 발생: {e}")
            return None

# 서비스 인스턴스를 가져오는 헬퍼 함수
_vector_store_service = None

def get_vector_store_service() -> VectorStoreService:
    """
    VectorStoreService 인스턴스를 가져옵니다. (싱글톤 패턴)
    """
    global _vector_store_service
    if _vector_store_service is None:
        _vector_store_service = VectorStoreService()
    return _vector_store_service
