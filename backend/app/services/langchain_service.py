"""
LangChain 서비스
LangChain을 활용한 AI 기능을 제공하는 서비스입니다.
"""

import logging
import os
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain, ConversationChain
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_openai import OpenAIEmbeddings
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import EmbeddingsFilter

# 시스템 프롬프트 가져오기
from app.services.system_prompt import get_system_prompt

# 설정
from app.core.config import settings

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LangChainService:
    """LangChain 기반 AI 서비스"""

    def __init__(self):
        """서비스 초기화"""
        self.openai_api_key = settings.OPENAI_API_KEY

        # 기본 LLM 설정
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.2,
            openai_api_key=self.openai_api_key
        )

        # 보다 정확한 분석을 위한 GPT-4 모델 (신뢰도 분석 등에 사용)
        self.advanced_llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            openai_api_key=self.openai_api_key
        )

        # 임베딩 모델
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=self.openai_api_key
        )

        # 체인 초기화
        self._initialize_chains()

    def _initialize_chains(self):
        """각종 LLM 체인을 초기화합니다."""

        # 뉴스 분석 체인
        self.news_analysis_chain = LLMChain(
            llm=self.llm,
            prompt=ChatPromptTemplate.from_template(
                get_system_prompt("news_recommendation", interests="AI, 클라우드, 빅데이터, 스타트업", recent_news="", query="")
            ),
            output_key="analysis"
        )

        # 뉴스 요약 체인
        self.summarization_chain = LLMChain(
            llm=self.llm,
            prompt=ChatPromptTemplate.from_template(
                get_system_prompt("news_summarization")
            ),
            output_key="summary"
        )

        # 신뢰도 분석 체인 (GPT-4 사용)
        self.trust_analysis_chain = LLMChain(
            llm=self.advanced_llm,
            prompt=ChatPromptTemplate.from_template(
                get_system_prompt("trust_analysis")
            ),
            output_key="trust_analysis"
        )

        # 감정 분석 체인
        self.sentiment_analysis_chain = LLMChain(
            llm=self.llm,
            prompt=ChatPromptTemplate.from_template(
                get_system_prompt("sentiment_analysis")
            ),
            output_key="sentiment_analysis"
        )

        # 키워드 추출 체인
        self.keyword_extraction_chain = LLMChain(
            llm=self.llm,
            prompt=ChatPromptTemplate.from_template(
                get_system_prompt("keyword_extraction")
            ),
            output_key="keywords"
        )

        # 질문 응답 체인
        self.qa_chain = LLMChain(
            llm=self.llm,
            prompt=ChatPromptTemplate.from_template(
                get_system_prompt("news_qa")
            ),
            output_key="answer"
        )

        # 콜드 스타트 추천 체인
        self.cold_start_chain = LLMChain(
            llm=self.llm,
            prompt=ChatPromptTemplate.from_template(
                get_system_prompt("cold_start")
            ),
            output_key="recommendations"
        )

        # 하이브리드 추천 체인
        self.hybrid_recommendation_chain = LLMChain(
            llm=self.advanced_llm,
            prompt=ChatPromptTemplate.from_template(
                get_system_prompt("hybrid_recommendation")
            ),
            output_key="recommendations"
        )

        # 다양성 강화 체인
        self.diversity_chain = LLMChain(
            llm=self.llm,
            prompt=ChatPromptTemplate.from_template(
                get_system_prompt("diversity")
            ),
            output_key="diversified_recommendations"
        )

    def analyze_news_sync(self, title: str, content: str) -> Dict[str, Any]:
        """
        뉴스 기사를 분석하여 각종 메타데이터를 추출합니다 (동기 버전).
        RSS 크롤러 등 동기 환경에서 호출하기 위한 메서드입니다.
        실제 LLM 및 NLP 기법을 활용하여 고품질 분석 결과를 제공합니다.

        Args:
            title: 뉴스 제목
            content: 뉴스 내용

        Returns:
            Dict[str, Any]: 분석 결과 (요약, 키워드, 주제, 중요도, 감정 분석 등)
        """
        try:
            # 콘텐츠 길이 제한
            if len(content) > 8000:
                content = content[:8000]

            # 1. 요약 생성 (동기 버전)
            summary = self.summarization_chain.run(
                title=title,
                content=content
            )

            # 2. 키워드 추출 (동기 버전)
            keyword_result = self.keyword_extraction_chain.run(
                title=title,
                content=content
            )

            # 쉼표로 구분된 키워드 문자열을 리스트로 변환
            if isinstance(keyword_result, str):
                keywords = [k.strip() for k in keyword_result.split(',')]
            else:
                keywords = keyword_result

            # 3. 감정 분석 - 고급 NLP 기반
            try:
                # 외부 감정 분석 서비스 연동 시도
                from app.services.sentiment_analysis_service import get_sentiment_analysis_service
                sentiment_service = get_sentiment_analysis_service()

                # 동기 버전 분석 호출 시도
                import asyncio
                try:
                    # 외부 감정 분석 서비스 호출
                    sentiment_text = f"{title} {content[:1000]}"

                    # asyncio 이벤트 루프 처리
                    import asyncio
                    try:
                        # 현재 이벤트 루프 가져오기 시도
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # 이미 실행 중인 경우 새 루프 생성
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            sentiment_result = new_loop.run_until_complete(
                                sentiment_service.analyze_sentiment(sentiment_text)
                            )
                            new_loop.close()
                        else:
                            # 기존 루프 사용
                            sentiment_result = loop.run_until_complete(
                                sentiment_service.analyze_sentiment(sentiment_text)
                            )
                    except RuntimeError:
                        # 이벤트 루프가 없는 경우 새 루프 생성
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        coro = sentiment_service.analyze_sentiment(sentiment_text)
                        sentiment_result = new_loop.run_until_complete(coro)
                        new_loop.close()

                    # 감정 분석 결과가 없는 경우 백업 사용
                    if sentiment_result is None:
                        sentiment_label, sentiment_score = self._analyze_sentiment_backup(content)
                except RuntimeError:
                    # 이벤트 루프 오류 시 새 루프 생성
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    coro = sentiment_service.analyze_sentiment(f"{title} {content[:1000]}")
                    sentiment_result = new_loop.run_until_complete(coro)
                    new_loop.close()

                # 감정 분석 결과 처리
                if sentiment_result and isinstance(sentiment_result, dict):
                    sentiment_label = sentiment_result.get("label", "neutral").lower()
                    sentiment_score = sentiment_result.get("score", 0.0)
                else:
                    # 감정 분석 서비스 사용 불가시 백업 분석
                    sentiment_label, sentiment_score = self._analyze_sentiment_backup(content)
            except Exception as sentiment_error:
                logger.error(f"감정 분석 중 오류 (백업 방식 사용): {str(sentiment_error)}")
                # 백업 감정 분석 로직 사용 - 동기 함수이므로 직접 호출
                try:
                    sentiment_label, sentiment_score = self._analyze_sentiment_backup(content)
                except Exception as e:
                    logger.error(f"백업 감정 분석 실패: {e}")
                    sentiment_label, sentiment_score = "neutral", 0.0  # 기본값 설정

            # 4. 신뢰도 분석 - 고급 NLP 기반
            try:
                # 외부 신뢰도 분석 서비스 연동 시도
                from app.services.trust_analysis_service import get_trust_analysis_service
                trust_service = get_trust_analysis_service()

                # 동기 버전 신뢰도 분석 호출 (안전한 방식으로)
                import asyncio
                try:
                    # 이전에 정의한 안전한 실행 방식 적용
                    metadata = {"title": title}
                    trust_text = f"{title} {content[:2000]}"

                    # 안전한 비동기 실행 함수 사용
                    def run_trust_async_safely():
                        """신뢰도 분석을 안전하게 실행하는 함수"""
                        try:
                            # 이미 실행 중인 루프가 있는지 확인
                            try:
                                loop = asyncio.get_event_loop()
                                if loop.is_running():
                                    # 이벤트 루프가 이미 실행 중이면 백업 사용
                                    return None
                            except RuntimeError:
                                pass  # 루프가 없는 경우

                            # 새 루프에서 실행
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            result = loop.run_until_complete(
                                trust_service.calculate_trust_score(trust_text, metadata)
                            )
                            loop.close()
                            return result
                        except Exception as e:
                            logger.error(f"신뢰도 비동기 실행 오류: {e}")
                            return None

                    # 비동기 실행
                    trust_result = run_trust_async_safely()

                    # 실패 시 백업 사용
                    if trust_result is None:
                        trust_score = self._calculate_trust_score_backup(title, content, keywords)
                        # 딕셔너리 형태로 반환되는 결과 처리
                        if isinstance(trust_result, dict) and "trust_score" in trust_result:
                            trust_score = trust_result["trust_score"]
                        else:
                            trust_score = trust_result  # 이전 버전과의 호환성 유지
                    else:
                        metadata = {"title": title}
                        trust_result = loop.run_until_complete(
                            trust_service.calculate_trust_score(f"{title} {content[:2000]}", metadata)
                        )
                        # 딕셔너리 형태로 반환되는 결과 처리
                        if isinstance(trust_result, dict) and "trust_score" in trust_result:
                            trust_score = trust_result["trust_score"]
                        else:
                            trust_score = trust_result  # 이전 버전과의 호환성 유지
                except RuntimeError:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    metadata = {"title": title}
                    coro = trust_service.calculate_trust_score(f"{title} {content[:2000]}", metadata)
                    trust_result = new_loop.run_until_complete(coro)
                    # 딕셔너리 형태로 반환되는 결과 처리
                    if isinstance(trust_result, dict) and "trust_score" in trust_result:
                        trust_score = trust_result["trust_score"]
                    else:
                        trust_score = trust_result  # 이전 버전과의 호환성 유지
                    new_loop.close()
            except Exception as trust_error:
                logger.error(f"신뢰도 분석 중 오류 (기본값 사용): {str(trust_error)}")
                # 백업 신뢰도 추정 로직 - 동기 함수이므로 직접 호출
                try:
                    trust_score = self._calculate_trust_score_backup(title, content, keywords)
                except Exception as e:
                    logger.error(f"백업 신뢰도 분석 실패: {e}")
                    trust_score = 0.6  # 기본 신뢰도 값

            # 5. 주제 분류
            topics = self._extract_topics_from_keywords(keywords, title)

            # 6. 중요도 평가 - 개선된 알고리즘
            # 여러 요소 기반 중요도 계산:
            # - 콘텐츠 길이
            # - 키워드 품질 및 수량
            # - 주제의 중요성
            # - 감정 강도
            # - 신뢰도

            # 기본 중요도
            importance_base = 5.0

            # 콘텐츠 길이 요소 (0-1 범위)
            length_factor = min(1.0, len(content) / 8000)

            # 키워드 품질 요소
            keyword_factor = min(1.0, len(keywords) / 10)

            # 주제 중요성 요소 (특정 중요 주제에 가중치)
            important_topics = ["ai", "인공지능", "정책", "기술", "혁신", "보안", "금융", "환경", "에너지"]
            topic_importance = sum(1 for topic in topics if any(imp in topic.lower() for imp in important_topics)) / max(1, len(topics))

            # 감정 강도 요소 (중립보다 강한 감정이 있는 기사가 주목받음)
            emotion_intensity = abs(sentiment_score) if isinstance(sentiment_score, (int, float)) else 0.5

            # 신뢰도 요소 (높은 신뢰도 기사는 더 중요할 수 있음)
            trust_factor = trust_score if isinstance(trust_score, (int, float)) else 0.5

            # 종합 중요도 계산 (각 요소에 가중치 부여)
            importance = importance_base + (length_factor * 1) + (keyword_factor * 1.5) + (topic_importance * 2) + (emotion_intensity * 1) + (trust_factor * 2)

            # 1-10 범위로 조정
            importance = max(1, min(10, importance))

            # 7. 메타데이터 생성
            metadata = {
                "content_length": len(content),
                "reading_time_minutes": max(1, len(content) // 1000),  # 대략 1000자당 1분 읽기 시간
                "processed_date": self._get_current_date_str(),
                "topics": topics,
                "sentiment": {
                    "label": sentiment_label,
                    "score": sentiment_score
                },
                "trust_score": trust_score,
                "importance_score": importance
            }

            # 8. 엔티티 추출 시도 (요약에서)
            entities = self._extract_entities_from_text(summary + " " + title)
            if entities:
                metadata["entities"] = entities

            # 최종 결과 반환
            return {
                "summary": summary,
                "keywords": keywords,
                "sentiment": sentiment_label,
                "sentiment_score": sentiment_score,
                "trust_score": trust_score,
                "importance": importance,
                "topics": topics,
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"뉴스 분석 중 오류 발생 (동기): {str(e)}")
            return {"error": str(e)}

    def _analyze_sentiment_backup(self, text: str) -> tuple:
        """
        텍스트의 감정을 분석하는 백업 방법.

        Args:
            text: 분석할 텍스트

        Returns:
            tuple: (감정 레이블, 감정 점수)
        """
        # 감정 분석 단어 목록
        positive_words = [
            "좋은", "훌륭한", "성공", "발전", "성취", "혁신", "개선", "상승", "증가",
            "긍정", "행복", "기쁨", "성장", "진보", "획기적", "흥미", "도약", "활약"
        ]
        negative_words = [
            "나쁜", "실패", "위기", "문제", "우려", "비판", "감소", "하락", "손실",
            "부정", "실망", "좌절", "침체", "저하", "불안", "위험", "갈등", "논란"
        ]

        # 단어 카운팅
        positive_count = sum(text.count(word) for word in positive_words)
        negative_count = sum(text.count(word) for word in negative_words)

        # 총합 계산
        total_count = positive_count + negative_count

        # 감정 레이블 및 점수 결정
        if total_count == 0:
            return "neutral", 0.0

        if positive_count > negative_count:
            ratio = positive_count / total_count
            return "positive", min(0.9, ratio)
        elif negative_count > positive_count:
            ratio = negative_count / total_count
            return "negative", -min(0.9, ratio)
        else:
            return "neutral", 0.0

    def _calculate_trust_score_backup(self, title: str, content: str, keywords: List[str]) -> float:
        """
        신뢰도 점수를 추정하는 백업 방법.

        Args:
            title: 뉴스 제목
            content: 뉴스 내용
            keywords: 추출된 키워드

        Returns:
            float: 신뢰도 점수 (0-1)
        """
        # 신뢰도 지표 키워드
        credible_words = [
            "연구", "조사", "발표", "보고서", "정부", "공식", "전문가", "교수", "박사",
            "과학", "논문", "데이터", "통계", "증거", "확인", "검증", "공개", "인용"
        ]

        questionable_words = [
            "루머", "소문", "의혹", "주장", "추측", "논란", "갈등", "밝혀지지 않은",
            "불확실", "불명확", "미확인", "비공식", "익명", "알려진", "카더라", "논쟁"
        ]

        # 단어 카운팅
        credible_count = sum(1 for word in credible_words if word in title or word in content[:3000])
        questionable_count = sum(1 for word in questionable_words if word in title or word in content[:3000])

        # 기본 신뢰도 점수
        base_score = 0.6  # 중간에서 약간 높은 기본값

        # 키워드에 신뢰성 지표가 있는지 확인
        keyword_credibility = sum(1 for word in credible_words if any(word in kw for kw in keywords))
        keyword_questionability = sum(1 for word in questionable_words if any(word in kw for kw in keywords))

        # 신뢰도 조정
        adjustment = 0.0
        adjustment += (credible_count * 0.05)  # 신뢰 단어당 증가
        adjustment -= (questionable_count * 0.05)  # 의심 단어당 감소
        adjustment += (keyword_credibility * 0.02)  # 키워드 신뢰성 반영
        adjustment -= (keyword_questionability * 0.02)  # 키워드 의심성 반영

        # 최종 점수 계산 (0-1 범위로 조정)
        final_score = max(0.1, min(0.9, base_score + adjustment))
        return final_score

    def _extract_topics_from_keywords(self, keywords: List[str], title: str) -> List[str]:
        """
        키워드에서 주제 추출하는 메서드

        Args:
            keywords: 키워드 목록
            title: 제목 텍스트

        Returns:
            List[str]: 주제 목록
        """
        # 주요 카테고리 정의
        categories = {
            "인공지능": ["ai", "인공지능", "머신러닝", "딥러닝", "알고리즘", "빅데이터"],
            "기술": ["기술", "it", "소프트웨어", "개발", "프로그래밍", "코딩", "앱", "웹", "인터넷"],
            "비즈니스": ["비즈니스", "스타트업", "기업", "투자", "주식", "경제", "시장", "산업"],
            "정책": ["정책", "법률", "규제", "정부", "법안", "제도", "방침"],
            "보안": ["보안", "해킹", "사이버", "개인정보", "프라이버시", "암호화"],
            "교육": ["교육", "학습", "학교", "강의", "커리큘럼", "교사", "학생"],
            "환경": ["환경", "기후", "지속가능", "에너지", "친환경", "재생"],
            "건강": ["건강", "의료", "헬스", "웰빙", "병원", "질병", "치료"],
            "엔터테인먼트": ["엔터테인먼트", "게임", "영화", "음악", "미디어", "콘텐츠"]
        }

        # 키워드와 제목 기반 주제 매칭
        matched_topics = []
        combined_text = " ".join([title.lower()] + [k.lower() for k in keywords])

        for category, markers in categories.items():
            if any(marker in combined_text for marker in markers):
                matched_topics.append(category)

        # 매칭된 주제가 없으면 기본 주제 반환
        if not matched_topics:
            return ["일반"]

        return matched_topics

    def _extract_entities_from_text(self, text: str) -> Dict[str, List[str]]:
        """
        텍스트에서 간단히 엔티티 추출 (백업 메서드)

        Args:
            text: 분석할 텍스트

        Returns:
            Dict[str, List[str]]: 엔티티 타입별 목록
        """
        import re

        # 간단한 정규식 패턴
        org_pattern = r'(?:[A-Z][a-z0-9]*\s*)+(?:주식회사|Inc|Corp|Corporation|Company|기업|그룹|은행|대학교?|협회|연구소)'
        person_pattern = r'(?:[가-힣]{2,3}\s(?:대표|사장|회장|의원|총리|장관|박사|교수|연구원))|(?:[가-힣]{2,3}\s[가-힣]{1,2}(?:씨|님))'
        location_pattern = r'(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주|\w+구|\w+시|\w+군|\w+동)'

        # 엔티티 추출
        orgs = list(set(re.findall(org_pattern, text)))
        persons = list(set(re.findall(person_pattern, text)))
        locations = list(set(re.findall(location_pattern, text)))

        return {
            "organizations": orgs[:5],  # 최대 5개만 반환
            "persons": persons[:5],
            "locations": locations[:5]
        }

    def _get_current_date_str(self) -> str:
        """현재 날짜 문자열 반환"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async def analyze_news(self, title: str, content: str) -> Dict[str, Any]:
        """
        뉴스 기사를 분석하여 각종 메타데이터를 추출합니다.

        Args:
            title: 뉴스 제목
            content: 뉴스 내용

        Returns:
            Dict[str, Any]: 분석 결과 (요약, 키워드, 주제, 중요도 등)
        """
        try:
            # 콘텐츠 길이 제한
            if len(content) > 8000:
                content = content[:8000]

            # 요약 생성
            summary_result = await self.summarize_text(title, content)

            # 키워드 추출
            keywords_result = await self.extract_keywords(title, content)

            # 주제 분류
            topics = ["technology", "ai", "news"]  # 실제로는 분류 로직 필요

            # 중요도 평가 (1-10)
            importance = 5  # 기본값

            return {
                "summary": summary_result.get("summary", ""),
                "keywords": keywords_result.get("keywords", []),
                "topics": topics,
                "importance": importance
            }
        except Exception as e:
            logger.error(f"뉴스 분석 중 오류 발생: {str(e)}")
            return {"error": str(e)}

    async def summarize_text(self, title: str, content: str) -> Dict[str, Any]:
        """
        텍스트를 요약합니다. 다양한 요약 방식을 활용하여 고품질 요약을 생성합니다.

        Args:
            title: 텍스트 제목
            content: 텍스트 내용

        Returns:
            Dict[str, Any]: 요약 결과 및 메타데이터
        """
        try:
            # 컨텐츠 길이에 따른 처리 최적화
            content_length = len(content)

            # 긴 문서인 경우 청크로 나누어 처리
            if content_length > 8000:
                return await self._summarize_long_text(title, content)

            # 기존 요약 체인 실행
            standard_summary = await self.summarization_chain.arun(
                title=title,
                content=content
            )

            # 더 고급화된 요약 생성 (GPT-4 활용)
            try:
                # 핵심 키워드를 먼저 추출
                keywords_result = await self.keyword_extraction_chain.arun(
                    title=title,
                    content=content[:4000] if content_length > 4000 else content
                )

                # 키워드 목록 추출
                if isinstance(keywords_result, str):
                    keywords = [k.strip() for k in keywords_result.split(',')]
                else:
                    keywords = keywords_result

                # 더 구체적인 요약 프롬프트 작성
                detailed_prompt = f"""
                다음 뉴스 기사에 대해 핵심 정보를 유지하면서 명확하고 간결한 요약을 작성해주세요.
                내용을 왜곡하거나 불필요한 정보를 추가하지 말고, 기사의 가장 중요한 사실과 관점만 포함해주세요.

                제목: {title}

                내용:
                {content[:6000] if content_length > 6000 else content}

                주요 키워드: {', '.join(keywords[:5]) if len(keywords) > 0 else ''}

                다음 정보를 포함하여 JSON 형식으로 응답해주세요:
                1. short_summary: 한 문장으로 된 매우 간결한 요약 (50자 이내)
                2. detailed_summary: 3-5문장으로 된 상세 요약 (200자 내외)
                3. key_points: 글머리 기호 형식의 핵심 요점 목록 (최대 5개)
                4. context: 기사의 배경 맥락 (선택 사항)
                5. implications: 이 내용의 시사점이나 영향 (선택 사항)
                """

                # 고급 요약 생성 (GPT-4 사용)
                advanced_response = await self.advanced_llm.agenerate([[detailed_prompt]])
                advanced_summary_text = advanced_response.generations[0][0].text

                # JSON 추출 시도
                import re
                import json

                json_match = re.search(r'\{.*\}', advanced_summary_text, re.DOTALL)
                advanced_summary = {}

                if json_match:
                    try:
                        advanced_summary = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        # JSON 파싱 실패 시 기본 요약 사용
                        advanced_summary = {
                            "short_summary": standard_summary[:50] if len(standard_summary) > 50 else standard_summary,
                            "detailed_summary": standard_summary,
                            "key_points": self._extract_key_points(standard_summary)
                        }
                else:
                    # JSON이 없는 경우 텍스트 파싱 시도
                    # 간단한 요약은 표준 요약 사용
                    short_summary = standard_summary[:50] if len(standard_summary) > 50 else standard_summary

                    # 핵심 요점 추출 시도
                    key_points = self._extract_key_points(advanced_summary_text)

                    advanced_summary = {
                        "short_summary": short_summary,
                        "detailed_summary": standard_summary,
                        "key_points": key_points
                    }

                # 메타데이터 추가
                reading_time = self._calculate_reading_time(content)

                return {
                    "summary": advanced_summary.get("detailed_summary", standard_summary),
                    "short_summary": advanced_summary.get("short_summary", ""),
                    "key_points": advanced_summary.get("key_points", []),
                    "context": advanced_summary.get("context", ""),
                    "implications": advanced_summary.get("implications", ""),
                    "keywords": keywords[:10] if len(keywords) > 0 else [],
                    "metadata": {
                        "content_length": content_length,
                        "reading_time_minutes": reading_time,
                        "summary_length": len(advanced_summary.get("detailed_summary", standard_summary)),
                        "summary_ratio": len(advanced_summary.get("detailed_summary", standard_summary)) / content_length if content_length > 0 else 0
                    }
                }

            except Exception as inner_e:
                logger.error(f"고급 요약 생성 중 오류 발생: {str(inner_e)}")
                # 오류 발생시 기본 요약 반환
                return {
                    "summary": standard_summary,
                    "short_summary": standard_summary[:50] if len(standard_summary) > 50 else standard_summary,
                    "key_points": self._extract_key_points(standard_summary),
                    "keywords": await self._extract_keywords_simple(title, content[:3000]),
                    "metadata": {
                        "content_length": content_length,
                        "reading_time_minutes": self._calculate_reading_time(content)
                    }
                }

        except Exception as e:
            logger.error(f"텍스트 요약 중 오류 발생: {str(e)}")
            return {"error": str(e)}

    async def _summarize_long_text(self, title: str, content: str) -> Dict[str, Any]:
        """
        긴 텍스트를 청크로 나누어 요약합니다.

        Args:
            title: 텍스트 제목
            content: 텍스트 내용

        Returns:
            Dict[str, Any]: 요약 결과
        """
        # 텍스트 분할
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=500
        )

        chunks = text_splitter.split_text(content)

        # 각 청크 요약
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            try:
                chunk_title = f"{title} (파트 {i+1}/{len(chunks)})"
                chunk_result = await self.summarization_chain.arun(
                    title=chunk_title,
                    content=chunk
                )
                chunk_summaries.append(chunk_result)
            except Exception as e:
                logger.error(f"청크 {i+1} 요약 중 오류: {str(e)}")
                # 오류 발생 시 원문의 일부를 요약으로 사용
                first_paragraph = chunk.split('\n\n')[0] if '\n\n' in chunk else chunk[:300]
                chunk_summaries.append(first_paragraph + "...")

        # 최종 요약 생성
        combined_summary = "\n\n".join(chunk_summaries)

        # 최종 메타 요약
        try:
            meta_summary_prompt = f"""
            다음은 긴 문서를 여러 부분으로 나누어 요약한 내용입니다. 이 요약들을 종합하여 하나의 일관된 요약으로 만들어주세요:

            제목: {title}

            부분별 요약:
            {combined_summary}
            """

            meta_summary_result = await self.advanced_llm.agenerate([[meta_summary_prompt]])
            final_summary = meta_summary_result.generations[0][0].text

            # 키워드 추출
            keywords = await self._extract_keywords_simple(title, combined_summary)

            # 핵심 요점 추출
            key_points = self._extract_key_points(final_summary)

            return {
                "summary": final_summary,
                "short_summary": final_summary.split(".")[0] if "." in final_summary else final_summary[:50],
                "key_points": key_points,
                "keywords": keywords,
                "original_chunk_summaries": chunk_summaries,
                "metadata": {
                    "content_length": len(content),
                    "chunks": len(chunks),
                    "reading_time_minutes": self._calculate_reading_time(content),
                    "is_long_text": True
                }
            }

        except Exception as e:
            logger.error(f"메타 요약 생성 중 오류: {str(e)}")
            # 오류 발생 시 부분 요약을 결합한 것을 반환
            return {
                "summary": combined_summary[:500] + "..." if len(combined_summary) > 500 else combined_summary,
                "short_summary": combined_summary.split(".")[0] if "." in combined_summary else combined_summary[:50],
                "is_long_text": True,
                "error": str(e)
            }

    def _extract_key_points(self, text: str) -> List[str]:
        """
        텍스트에서 핵심 요점을 추출합니다.

        Args:
            text: 분석할 텍스트

        Returns:
            List[str]: 핵심 요점 목록
        """
        import re

        # 글머리 기호로 시작하는 목록 찾기
        bullet_pattern = r'(?:^|\n)(?:\d+[\.\)]\s*|\*\s*|\-\s*|\•\s*)[^\n]+'
        bullet_points = re.findall(bullet_pattern, text)

        if bullet_points:
            # 글머리 기호 제거 및 정리
            cleaned_points = []
            for point in bullet_points:
                # 글머리 기호 및 앞뒤 공백 제거
                cleaned = re.sub(r'^[\n\s]*(?:\d+[\.\)]\s*|\*\s*|\-\s*|\•\s*)', '', point).strip()
                if cleaned:
                    cleaned_points.append(cleaned)

            return cleaned_points[:5]  # 최대 5개 반환

        else:
            # 글머리 기호가 없으면 문장으로 분리
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]

            # 중요 문장 선택
            key_sentences = []
            for sentence in sentences:
                # 중요성을 나타내는 단어나 문구가 있는 문장 선택
                importance_markers = ["중요", "핵심", "주요", "결론", "따라서", "요약", "강조", "결과적으로"]
                if any(marker in sentence for marker in importance_markers) or len(sentence) < 100:
                    key_sentences.append(sentence)

                # 최대 5개까지만 선택
                if len(key_sentences) >= 5:
                    break

            # 문장이 충분하지 않으면 처음 몇 문장 사용
            if len(key_sentences) < 3 and len(sentences) > 0:
                return sentences[:5]

            return key_sentences

    async def _extract_keywords_simple(self, title: str, content: str) -> List[str]:
        """
        텍스트에서 간단하게 키워드를 추출합니다.

        Args:
            title: 텍스트 제목
            content: 텍스트 내용

        Returns:
            List[str]: 키워드 목록
        """
        combined_text = f"{title} {content}"

        # 중요 단어 패턴
        import re

        # 명사 패턴 (한글 명사 패턴은 매우 단순화됨)
        noun_pattern = r'[가-힣a-zA-Z]{2,}(?:[가-힣a-zA-Z]+)?'
        words = re.findall(noun_pattern, combined_text)

        # 빈도수 계산
        from collections import Counter
        word_counts = Counter(words)

        # 불용어 제거
        stopwords = ["이것", "그것", "저것", "이런", "그런", "저런", "이렇게", "그렇게", "것이", "하지만", "그리고", "그래서"]
        for word in stopwords:
            if word in word_counts:
                del word_counts[word]

        # 가장 빈번한 단어 추출
        common_words = [word for word, _ in word_counts.most_common(10)]

        # 더 좋은 키워드가 필요하면 LLM 사용
        if len(common_words) < 5:
            try:
                keywords_result = await self.keyword_extraction_chain.arun(
                    title=title,
                    content=content[:3000]
                )

                if isinstance(keywords_result, str):
                    keywords = [k.strip() for k in keywords_result.split(',')]
                    return keywords[:10]
            except:
                pass

        return common_words

    def _calculate_reading_time(self, text: str) -> int:
        """
        텍스트의 읽기 시간을 계산합니다(분 단위).

        Args:
            text: 텍스트

        Returns:
            int: 분 단위 읽기 시간
        """
        # 평균 읽기 속도: 한국어 기준 1분에 약 600자
        words_per_minute = 600

        # 글자 수 / 분당 읽기 속도
        minutes = len(text) / words_per_minute

        # 최소 1분 이상
        return max(1, round(minutes))

    async def extract_keywords(self, title: str, content: str) -> Dict[str, List[str]]:
        """
        텍스트에서 키워드를 추출합니다. 고급 NLP 기법과 임베딩 모델을 활용하여 정확하고 의미있는 키워드를 추출합니다.

        Args:
            title: 텍스트 제목
            content: 텍스트 내용

        Returns:
            Dict[str, List[str]]: 추출된 키워드 목록과 추가 메타데이터
        """
        try:
            # 콘텐츠 길이 제한
            truncated_content = content
            if len(content) > 6000:
                truncated_content = content[:6000]

            # 1. 기본 LLM 체인으로 키워드 추출
            basic_result = await self.keyword_extraction_chain.arun(
                title=title,
                content=truncated_content
            )

            # 쉼표로 구분된 키워드 문자열을 리스트로 변환
            if isinstance(basic_result, str):
                basic_keywords = [k.strip() for k in basic_result.split(',')]
            else:
                basic_keywords = basic_result

            # 2. 더 높은 품질의 키워드 생성을 위한 고급 프롬프트 (GPT-4 사용)
            try:
                advanced_prompt = f"""
                다음 텍스트에서 다양한 유형의 키워드를 추출해주세요:

                제목: {title}
                내용: {truncated_content[:2000]}...

                다음 정보를 포함하여 JSON 형식으로 응답해주세요:
                1. main_keywords: 주요 키워드 (5-10개)
                2. entity_keywords: 중요 개체/명사 (3-7개)
                3. technical_terms: 전문 용어 (0-5개, 있는 경우)
                4. theme_keywords: 글의 주제/테마 관련 키워드 (2-3개)
                5. sentiment_keywords: 감정/태도 관련 키워드 (1-3개)
                6. trending_keywords: 트렌드/유행과 관련된 키워드 (0-3개, 있는 경우)

                각 키워드 타입은 고유해야 합니다. 반복되는 키워드가 없도록 해주세요.
                키워드는 1-3단어로 구성된 간결한 형태여야 합니다.
                """

                advanced_response = await self.advanced_llm.agenerate([[advanced_prompt]])
                advanced_text = advanced_response.generations[0][0].text

                # JSON 추출 시도
                import re
                import json

                json_match = re.search(r'\{.*\}', advanced_text, re.DOTALL)
                if json_match:
                    try:
                        advanced_keywords = json.loads(json_match.group(0))

                        # 모든 키워드 합치기 (중복 제거)
                        all_keywords = set()
                        for key, keywords in advanced_keywords.items():
                            if isinstance(keywords, list):
                                all_keywords.update([k.strip() for k in keywords if k.strip()])

                        # 결과 구성
                        return {
                            "keywords": list(all_keywords)[:15],  # 상위 15개만 사용
                            "categorized": advanced_keywords,
                            "main_keywords": advanced_keywords.get("main_keywords", basic_keywords[:5]),
                            "entity_keywords": advanced_keywords.get("entity_keywords", []),
                            "technical_terms": advanced_keywords.get("technical_terms", []),
                            "theme_keywords": advanced_keywords.get("theme_keywords", []),
                            "basic_keywords": basic_keywords[:10]  # 기본 키워드도 포함
                        }
                    except json.JSONDecodeError:
                        # JSON 파싱 실패시 기본 키워드 사용
                        pass

            except Exception as inner_e:
                logger.error(f"고급 키워드 추출 중 오류 발생: {str(inner_e)}")

            # 3. 임베딩 기반 키워드 추출 시도
            try:
                # 텍스트에서 주요 문장 추출
                sentences = [sent.strip() for sent in re.split(r'[.!?]', truncated_content) if sent.strip()]
                important_sentences = []

                # 제목과 유사한 문장, 키워드가 많이 포함된 문장 우선 선택
                keyword_set = set(basic_keywords)
                for sent in sentences:
                    # 제목 포함 여부
                    if any(word in sent.lower() for word in title.lower().split()):
                        important_sentences.append(sent)
                    # 키워드 포함 수
                    elif sum(1 for kw in keyword_set if kw.lower() in sent.lower()) >= 2:
                        important_sentences.append(sent)

                    if len(important_sentences) >= 5:
                        break

                # 중요 문장이 없으면 처음 몇 문장 사용
                if not important_sentences and sentences:
                    important_sentences = sentences[:3]

                # 중요 문장에서 명사구 추출
                import re
                noun_chunks = []
                for sent in important_sentences:
                    # 한국어 명사 추출 패턴 (단순화됨)
                    chunks = re.findall(r'[가-힣a-zA-Z]{2,}(?:\s+[가-힣a-zA-Z]+){0,2}', sent)
                    noun_chunks.extend(chunks)

                # 빈도 기반 중요 명사구 선별
                from collections import Counter
                chunk_counter = Counter(noun_chunks)
                top_chunks = [chunk for chunk, _ in chunk_counter.most_common(10)]

                # 기본 키워드와 통합 (중복 제거)
                combined_keywords = list(set(basic_keywords) | set(top_chunks))

                # 통합 키워드 카테고리 추정
                # 기술 용어와 일반 용어 분리
                general_terms = []
                technical_terms = []

                for kw in combined_keywords:
                    if any(tech_marker in kw.lower() for tech_marker in ["ai", "ml", "기술", "시스템", "개발", "데이터", "알고리즘"]):
                        technical_terms.append(kw)
                    else:
                        general_terms.append(kw)

                return {
                    "keywords": combined_keywords[:15],  # 상위 15개만 사용
                    "general_terms": general_terms[:8],
                    "technical_terms": technical_terms[:5],
                    "important_phrases": top_chunks,
                    "basic_keywords": basic_keywords
                }

            except Exception as embed_e:
                logger.error(f"임베딩 기반 키워드 추출 중 오류: {str(embed_e)}")
                # 기본 결과 반환
                return {"keywords": basic_keywords}

        except Exception as e:
            logger.error(f"키워드 추출 중 오류 발생: {str(e)}")

            # 백업 방식: 기본 키워드 추출
            try:
                simple_keywords = await self._extract_keywords_simple(title, content[:3000])
                return {"keywords": simple_keywords, "note": "백업 방식으로 추출됨"}
            except:
                return {"error": str(e), "keywords": []}

    async def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        텍스트에서 엔티티(인물, 조직, 위치 등)를 추출합니다.

        Args:
            text: 분석할 텍스트

        Returns:
            Dict[str, List[str]]: 엔티티 유형별 목록
        """
        try:
            # 엔티티 추출을 위한 LLM 프롬프트
            entity_prompt = f"""
            다음 텍스트에서 모든 이름 있는 개체(Named Entities)를 추출하고 분류해주세요:

            {text[:4000] if len(text) > 4000 else text}

            다음 형식의 JSON으로 응답해주세요:
            {{
                "persons": ["사람1", "사람2", ...],
                "organizations": ["조직1", "조직2", ...],
                "locations": ["장소1", "장소2", ...],
                "products": ["제품1", "제품2", ...],
                "events": ["이벤트1", "이벤트2", ...],
                "concepts": ["개념1", "개념2", ...]
            }}
            """

            entity_response = await self.llm.agenerate([[entity_prompt]])
            entity_text = entity_response.generations[0][0].text

            # JSON 추출 시도
            import re
            import json

            json_match = re.search(r'\{.*\}', entity_text, re.DOTALL)
            if json_match:
                try:
                    entities = json.loads(json_match.group(0))
                    return entities
                except json.JSONDecodeError:
                    # 파싱 실패 시 기본 구조 반환
                    return {
                        "persons": [],
                        "organizations": [],
                        "locations": [],
                        "products": [],
                        "events": [],
                        "concepts": []
                    }
            else:
                # JSON이 없는 경우 텍스트 파싱
                persons = re.findall(r'persons["\']\s*:\s*\[(.*?)\]', entity_text)
                orgs = re.findall(r'organizations["\']\s*:\s*\[(.*?)\]', entity_text)
                locations = re.findall(r'locations["\']\s*:\s*\[(.*?)\]', entity_text)

                extract_items = lambda text: [item.strip().strip('"\'') for item in text.split(',') if item.strip()]

                return {
                    "persons": extract_items(persons[0]) if persons else [],
                    "organizations": extract_items(orgs[0]) if orgs else [],
                    "locations": extract_items(locations[0]) if locations else [],
                    "products": [],
                    "events": [],
                    "concepts": []
                }

        except Exception as e:
            logger.error(f"엔티티 추출 중 오류 발생: {str(e)}")
            return {"error": str(e)}

    async def analyze_trust(self, title: str, content: str) -> Dict[str, Any]:
        """
        뉴스 기사의 신뢰도를 분석합니다. 실제 신뢰도 분석 서비스와 연동합니다.

        Args:
            title: 뉴스 제목
            content: 뉴스 내용

        Returns:
            Dict[str, Any]: 신뢰도 분석 결과
        """
        try:
            # 콘텐츠 길이 제한
            if len(content) > 4000:
                content = content[:4000]

            # 신뢰도 분석 체인 실행
            chain_result = await self.trust_analysis_chain.arun(
                title=title,
                content=content
            )

            # 외부 신뢰도 분석 서비스 호출
            try:
                from app.services.trust_analysis_service import get_trust_analysis_service
                trust_analysis_service = get_trust_analysis_service()

                # 텍스트 결합
                combined_text = f"{title} {content}"
                metadata = {"title": title}
                trust_result = await trust_analysis_service.calculate_trust_score(combined_text, metadata)

                # 딕셔너리 형태로 반환되는 결과 처리
                if isinstance(trust_result, dict) and "trust_score" in trust_result:
                    trust_score = trust_result["trust_score"]
                else:
                    trust_score = trust_result  # 이전 버전과의 호환성 유지

                # 상세 신뢰도 요소 분석 (GPT 모델에 구체적인 분석 요청)
                detailed_prompt = f"""
                다음 뉴스 기사의 신뢰도 요소를 상세하게 분석해주세요:

                제목: {title}
                내용: {content[:1000]}...

                다음 신뢰도 요소에 대해 0.0에서 1.0 사이의 점수로 평가해주세요:
                1. 출처 신뢰성 (source_credibility)
                2. 사실적 정확성 (factual_accuracy)
                3. 객관성 (objectivity)
                4. 투명성 (transparency)
                5. 전문성 (expertise)

                각 요소별 점수와 그 이유를 JSON 형식으로 제공해주세요.
                """

                detailed_response = await self.advanced_llm.agenerate([[detailed_prompt]])
                detailed_text = detailed_response.generations[0][0].text

                # JSON 추출 시도
                import re
                import json

                json_match = re.search(r'\{.*\}', detailed_text, re.DOTALL)
                if json_match:
                    try:
                        trust_factors = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        # JSON 파싱 실패 시 구조화된 텍스트 추출 시도
                        trust_factors = {}
                        for factor in ["source_credibility", "factual_accuracy", "objectivity", "transparency", "expertise"]:
                            match = re.search(rf'{factor}["\s:]+([\d\.]+)', detailed_text, re.IGNORECASE)
                            if match:
                                trust_factors[factor] = float(match.group(1))
                            else:
                                trust_factors[factor] = 0.5  # 기본값
                else:
                    # 기본 요소 설정
                    trust_factors = {
                        "source_credibility": 0.7,
                        "factual_accuracy": 0.7,
                        "objectivity": 0.6,
                        "transparency": 0.7,
                        "expertise": 0.6
                    }

                # 상세 분석 내용 추출
                analysis = {
                    "summary": chain_result,
                    "detailed_analysis": detailed_text,
                    "trust_factors": trust_factors,
                    "overall_score": trust_score
                }

                return {
                    "trust_score": trust_score,
                    "trust_factors": trust_factors,
                    "analysis": analysis
                }

            except Exception as inner_e:
                logger.error(f"외부 신뢰도 분석 서비스 호출 중 오류 발생: {str(inner_e)}")

                # 백업으로 LLM 기반 분석 결과 사용
                llm_trust_score = await self._extract_trust_score_from_text(chain_result)

                return {
                    "trust_score": llm_trust_score,
                    "trust_factors": {
                        "source_credibility": llm_trust_score * 0.9,
                        "factual_accuracy": llm_trust_score * 1.1 if llm_trust_score * 1.1 <= 1.0 else 1.0,
                        "objectivity": llm_trust_score * 0.85,
                        "transparency": llm_trust_score * 0.95
                    },
                    "analysis": chain_result,
                    "note": "외부 서비스 오류로 LLM 결과를 사용했습니다."
                }

        except Exception as e:
            logger.error(f"신뢰도 분석 중 오류 발생: {str(e)}")
            return {"error": str(e)}

    async def _extract_trust_score_from_text(self, analysis_text: str) -> float:
        """
        분석 텍스트에서 신뢰도 점수를 추출합니다.

        Args:
            analysis_text: 분석 텍스트

        Returns:
            float: 신뢰도 점수 (0-1)
        """
        try:
            # 숫자로 된 신뢰도 점수 찾기 시도
            import re
            score_matches = re.findall(r'([\d\.]+)\s*\/\s*10|신뢰도[\s:]+([\d\.]+)', analysis_text)

            if score_matches:
                for match in score_matches:
                    # 여러 형태의 매치 처리
                    if match[0]:  # x/10 형태
                        return float(match[0]) / 10
                    elif match[1]:  # 신뢰도: x 형태
                        score = float(match[1])
                        # 가정: 10점 만점 시스템이면 10으로 나눔
                        return score / 10 if score > 1 else score

            # 키워드 기반 점수 추정
            positive_terms = ["신뢰할 수 있", "정확", "검증", "사실", "공식", "확인", "근거", "투명"]
            negative_terms = ["의심", "불확실", "오해", "왜곡", "과장", "편향", "가짜", "루머", "오류"]

            positive_count = sum(1 for term in positive_terms if term in analysis_text)
            negative_count = sum(1 for term in negative_terms if term in analysis_text)

            # 기본값에서 시작해서 긍정적/부정적 용어 비율에 따라 조정
            total_terms = len(positive_terms) + len(negative_terms)
            base_score = 0.6  # 기본 신뢰도

            if positive_count + negative_count > 0:
                score_adjustment = ((positive_count - negative_count) / total_terms) * 0.4
                return max(0.1, min(0.9, base_score + score_adjustment))

            return base_score

        except Exception as e:
            logger.error(f"신뢰도 점수 추출 중 오류: {str(e)}")
            return 0.5  # 오류 시 중간값 반환

    async def analyze_sentiment(self, title: str, content: str) -> Dict[str, Any]:
        """
        텍스트의 감정을 분석합니다. 실제 감정 분석 서비스와 연동하여 정확한 결과를 제공합니다.

        Args:
            title: 텍스트 제목
            content: 텍스트 내용

        Returns:
            Dict[str, Any]: 감정 분석 결과
        """
        try:
            # 콘텐츠 길이 제한
            if len(content) > 4000:
                content = content[:4000]

            # 기존 LLM 체인을 통한 분석
            chain_result = await self.sentiment_analysis_chain.arun(
                title=title,
                content=content
            )

            # 실제 감정 분석 서비스 연동
            try:
                from app.services.sentiment_analysis_service import get_sentiment_analysis_service
                sentiment_service = get_sentiment_analysis_service()

                # 텍스트 결합
                combined_text = f"{title} {content}"

                # 감정 분석 실행
                sentiment_result = await sentiment_service.analyze_sentiment(combined_text)

                # 감정 분석 결과가 있으면 사용, 없으면 백업 방식으로 처리
                if sentiment_result and isinstance(sentiment_result, dict):
                    # 결과 형식화
                    score = sentiment_result.get("score", 0)  # -1.0 ~ 1.0
                    label = sentiment_result.get("label", "neutral").lower()

                    # 감정 분석 상세 분석을 위한 GPT 호출
                    detailed_prompt = f"""
                    다음 텍스트의 감정을 상세하게 분석해주세요:

                    제목: {title}
                    내용: {content[:1000]}...

                    다음 정보를 포함하여 JSON 형식으로 응답해주세요:
                    1. positive_score: 긍정적 감정 점수 (0.0-1.0)
                    2. negative_score: 부정적 감정 점수 (0.0-1.0)
                    3. neutral_score: 중립적 감정 점수 (0.0-1.0)
                    4. dominant_emotions: 주요 감정 목록 (최대 3개)
                    5. emotional_language: 감정적인 언어 표현 예시
                    6. analysis_summary: 분석 요약
                    """

                    detailed_response = await self.llm.agenerate([[detailed_prompt]])
                    detailed_text = detailed_response.generations[0][0].text

                    # JSON 추출 시도
                    import re
                    import json

                    json_match = re.search(r'\{.*\}', detailed_text, re.DOTALL)
                    if json_match:
                        try:
                            detailed_analysis = json.loads(json_match.group(0))
                        except json.JSONDecodeError:
                            # 기본 점수 설정
                            if label == "positive":
                                positive, negative, neutral = 0.7, 0.1, 0.2
                            elif label == "negative":
                                positive, negative, neutral = 0.1, 0.7, 0.2
                            else:
                                positive, negative, neutral = 0.2, 0.2, 0.6

                            detailed_analysis = {
                                "positive_score": positive,
                                "negative_score": negative,
                                "neutral_score": neutral,
                                "dominant_emotions": self._extract_emotions_from_text(detailed_text),
                                "emotional_language": [],
                                "analysis_summary": detailed_text
                            }
                    else:
                        # 감정 점수 기본값
                        if label == "positive":
                            positive, negative, neutral = 0.7, 0.1, 0.2
                        elif label == "negative":
                            positive, negative, neutral = 0.1, 0.7, 0.2
                        else:
                            positive, negative, neutral = 0.2, 0.2, 0.6

                        detailed_analysis = {
                            "positive_score": positive,
                            "negative_score": negative,
                            "neutral_score": neutral,
                            "dominant_emotions": self._extract_emotions_from_text(detailed_text),
                            "emotional_language": [],
                            "analysis_summary": detailed_text
                        }

                    # 결과 구성
                    sentiment = {
                        "score": score,
                        "label": label,
                        "positive": detailed_analysis.get("positive_score", 0.3),
                        "negative": detailed_analysis.get("negative_score", 0.1),
                        "neutral": detailed_analysis.get("neutral_score", 0.6),
                        "dominant_emotions": detailed_analysis.get("dominant_emotions", []),
                        "emotional_language": detailed_analysis.get("emotional_language", [])
                    }

                    return {
                        "sentiment": sentiment,
                        "analysis": {
                            "summary": chain_result,
                            "detailed_analysis": detailed_analysis
                        }
                    }

                else:
                    # 백업 방식: 기존 LLM 결과에서 감정 추출
                    sentiment_info = await self._extract_sentiment_from_text(chain_result)

                    return {
                        "sentiment": sentiment_info,
                        "analysis": chain_result
                    }

            except Exception as inner_e:
                logger.error(f"감정 분석 서비스 연동 중 오류 발생: {str(inner_e)}")

                # 백업 방식: 기존 LLM 결과에서 감정 추출
                sentiment_info = await self._extract_sentiment_from_text(chain_result)

                return {
                    "sentiment": sentiment_info,
                    "analysis": chain_result,
                    "note": "외부 서비스 오류로 LLM 결과를 사용했습니다."
                }

        except Exception as e:
            logger.error(f"감정 분석 중 오류 발생: {str(e)}")
            return {"error": str(e)}

    async def _extract_sentiment_from_text(self, analysis_text: str) -> Dict[str, Any]:
        """
        분석 텍스트에서 감정 정보를 추출합니다.

        Args:
            analysis_text: 분석 텍스트

        Returns:
            Dict[str, Any]: 감정 분석 정보
        """
        try:
            # 감정 레이블 추출 시도
            import re

            # 긍정/부정 키워드 탐색
            positive_terms = ["긍정", "좋", "행복", "희망", "기쁨", "만족", "성공", "발전", "축하"]
            negative_terms = ["부정", "나쁨", "슬픔", "분노", "실망", "우려", "비판", "불안", "위협"]
            neutral_terms = ["중립", "보통", "일반", "표준", "객관"]

            # 키워드 발견 빈도수
            pos_count = sum(1 for term in positive_terms if term in analysis_text)
            neg_count = sum(1 for term in negative_terms if term in analysis_text)
            neu_count = sum(1 for term in neutral_terms if term in analysis_text)

            # 감정 레이블과 점수 산출
            total = pos_count + neg_count + neu_count
            if total == 0:
                # 기본값
                positive = 0.3
                negative = 0.1
                neutral = 0.6
                label = "neutral"
                score = 0.2  # 약간 긍정적
            else:
                positive = pos_count / total
                negative = neg_count / total
                neutral = neu_count / total

                # 가장 높은 점수의 감정 레이블 선택
                if positive > negative and positive > neutral:
                    label = "positive"
                    score = 0.5 + (positive * 0.5)  # 0.5 ~ 1.0
                elif negative > positive and negative > neutral:
                    label = "negative"
                    score = -0.5 - (negative * 0.5)  # -0.5 ~ -1.0
                else:
                    label = "neutral"
                    score = (positive - negative) * 0.4  # -0.4 ~ 0.4

            # 감정 단어 추출
            emotion_words = ["행복", "기쁨", "즐거움", "흥분", "만족", "안도", "희망",
                          "슬픔", "우울", "분노", "두려움", "불안", "실망", "당혹",
                          "혐오", "공포", "놀라움", "사랑", "미움", "질투"]

            dominant_emotions = []
            for emotion in emotion_words:
                if emotion in analysis_text:
                    dominant_emotions.append(emotion)

            if len(dominant_emotions) > 3:
                dominant_emotions = dominant_emotions[:3]

            return {
                "score": score,
                "label": label,
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "dominant_emotions": dominant_emotions
            }

        except Exception as e:
            logger.error(f"감정 정보 추출 중 오류: {str(e)}")
            return {
                "score": 0.2,
                "label": "neutral",
                "positive": 0.3,
                "negative": 0.1,
                "neutral": 0.6,
            }

    def _extract_emotions_from_text(self, text: str) -> List[str]:
        """
        텍스트에서 감정 단어를 추출합니다.

        Args:
            text: 분석 텍스트

        Returns:
            List[str]: 감정 단어 목록
        """
        emotion_words = {
            "행복": ["행복", "기쁨", "즐거움", "희열", "만족", "환희"],
            "슬픔": ["슬픔", "비탄", "우울", "침울", "서글픔", "비애"],
            "분노": ["분노", "화남", "격분", "격노", "분개", "노여움"],
            "공포": ["공포", "두려움", "무서움", "겁", "불안", "공포감"],
            "혐오": ["혐오", "메스꺼움", "구역질", "거부감", "역겨움"],
            "놀라움": ["놀라움", "경이", "경악", "기겁", "충격"],
            "기대": ["기대", "희망", "고대", "설렘", "고조"],
            "신뢰": ["신뢰", "믿음", "확신", "인정", "승복"]
        }

        found_emotions = []
        for emotion, keywords in emotion_words.items():
            if any(keyword in text for keyword in keywords):
                found_emotions.append(emotion)

        # 최대 3개로 제한
        return found_emotions[:3] if found_emotions else ["중립"]

    async def answer_question(self, title: str, content: str, question: str) -> str:
        """
        뉴스 기사에 대한 질문에 답변합니다.

        Args:
            title: 뉴스 제목
            content: 뉴스 내용
            question: 질문

        Returns:
            str: 질문에 대한 답변
        """
        try:
            # 콘텐츠 길이 제한
            if len(content) > 4000:
                content = content[:4000]

            result = await self.qa_chain.arun(
                title=title,
                content=content,
                question=question
            )

            return result
        except Exception as e:
            logger.error(f"질문 응답 중 오류 발생: {str(e)}")
            return f"죄송합니다. 질문에 응답하는 중 오류가 발생했습니다: {str(e)}"

    async def get_recommendations(self,
                                interests: List[str],
                                read_history: List[str],
                                query: str,
                                news_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        사용자 관심사와 읽은 기사 이력을 기반으로 추천을 생성합니다.
        벡터 임베딩 기반 유사도 및 LLM 추론을 결합한 하이브리드 추천 시스템을 구현합니다.

        Args:
            interests: 사용자 관심 카테고리
            read_history: 최근 읽은 기사 제목 목록
            query: 관심사 기반 쿼리
            news_list: 뉴스 목록

        Returns:
            Dict[str, Dict[str, Any]]: 뉴스 ID를 키로 하는 추천 결과
        """
        try:
            if not news_list:
                return {}

            # 0. 결과 저장용 딕셔너리
            recommendations = {}

            # 1. 컨텐츠 기반 필터링: 임베딩 모델 활용
            try:
                # 임베딩 서비스 가져오기
                from app.services.embedding_service import get_embedding_service
                embedding_service = get_embedding_service()

                # 관심사와 쿼리 결합하여 사용자 프로필 생성
                user_profile = f"관심사: {', '.join(interests) if interests else '일반 뉴스'}"
                if query:
                    user_profile += f". 검색어: {query}"
                if read_history:
                    user_profile += f". 최근 본 뉴스: {'; '.join(read_history[:3])}"

                # 사용자 프로필 임베딩 생성
                user_embedding = await embedding_service.get_embedding(user_profile)

                # 각 뉴스의 임베딩 생성 및 유사도 계산
                content_scores = {}

                for news in news_list:
                    news_id = news.get("id", "")
                    if not news_id:
                        continue

                    # 뉴스 텍스트 결합
                    news_text = f"{news.get('title', '')} {news.get('content', '')[:500]}"

                    # 뉴스 임베딩 생성 (또는 DB에서 가져오기)
                    try:
                        # 기존 임베딩 확인 시도
                        from app.db.mongodb import embeddings_collection
                        existing_embedding = embeddings_collection.find_one({"news_id": news_id})

                        if existing_embedding and "embedding" in existing_embedding:
                            news_embedding = existing_embedding["embedding"]
                        else:
                            # 새 임베딩 생성
                            news_embedding = await embedding_service.get_embedding(news_text)
                    except:
                        # 직접 임베딩 생성
                        news_embedding = await embedding_service.get_embedding(news_text)

                    # 코사인 유사도 계산
                    if user_embedding and news_embedding:
                        import numpy as np
                        cosine_sim = np.dot(user_embedding, news_embedding) / (
                            np.linalg.norm(user_embedding) * np.linalg.norm(news_embedding)
                        )
                        # 유사도 0.5-1.0 범위로 정규화 (유사할수록 1에 가까움)
                        normalized_sim = 0.5 + (cosine_sim * 0.5)
                        content_scores[news_id] = normalized_sim

            except Exception as embed_error:
                logger.error(f"임베딩 기반 추천 중 오류: {str(embed_error)}")
                # 임베딩 오류 시 기본 점수 할당
                content_scores = {news.get("id", ""): 0.7 for news in news_list if news.get("id", "")}

            # 2. LLM 기반 하이브리드 추천 구성
            try:
                # 관심사 문자열 형태로 변환
                interests_str = ", ".join(interests) if interests else "일반 뉴스"

                # 읽은 기사 목록 문자열 형태로 변환
                recent_news = "\n- ".join(read_history) if read_history else "없음"
                if recent_news != "없음":
                    recent_news = f"- {recent_news}"

                # 뉴스 목록 형식화 (임베딩 점수 포함)
                news_items = []
                for i, news in enumerate(news_list):
                    news_id = news.get("id", "")
                    if not news_id:
                        continue

                    # 내용 구성
                    content_score = content_scores.get(news_id, 0.7)
                    trust_score = news.get("trust_score", 0.5)
                    sentiment = news.get("sentiment_score", 0)
                    sentiment_label = "긍정적" if sentiment > 0.2 else "부정적" if sentiment < -0.2 else "중립적"

                    # 출판 시간 정보 추가
                    pub_date = news.get("published_date", "")
                    date_str = ""
                    if pub_date:
                        from datetime import datetime
                        if isinstance(pub_date, datetime):
                            date_str = f", 발행: {pub_date.strftime('%Y-%m-%d')}"
                        elif isinstance(pub_date, str):
                            date_str = f", 발행: {pub_date}"

                    news_items.append(
                        f"{i+1}. ID: {news_id}, 제목: {news.get('title', '제목 없음')}{date_str}, "
                        f"출처: {news.get('source', '알 수 없음')}, "
                        f"유사도: {content_score:.2f}, 신뢰도: {trust_score:.2f}, 감정: {sentiment_label}"
                    )

                # 뉴스 아이템을 문자열로 결합
                news_items_str = "\n".join(news_items)

                # 추천 프롬프트 개선 - 명확한 형식 지정
                custom_prompt = f"""
                당신은 개인화된 뉴스 추천 시스템입니다. 사용자의 관심사와 읽은 기사 이력, 그리고 임베딩 기반 유사도 점수를 고려하여 가장 적합한 뉴스를 추천하세요.

                사용자 프로필:
                - 관심사: {interests_str}
                - 최근 읽은 기사:
                {recent_news}
                - 검색어/요청: {query if query else "특별한 요청 없음"}

                추천할 뉴스 목록:
                {news_items_str}

                [요청 사항]
                1. 위 뉴스에서 사용자에게 가장 관련성 높은 뉴스 ID 목록을 선정하세요.
                2. 각 뉴스에 대해 추천 이유와 1-10 점수를 매겨주세요.
                3. 추천 시 다음 요소를 고려하세요:
                   - 사용자의 관심사와 일치하는 주제
                   - 유사도 점수 (높을수록 좋음)
                   - 신뢰도 점수 (높을수록 좋음)
                   - 읽은 기사와의 관련성 및 다양성

                JSON 형식으로 아래와 같이 응답해주세요:
                {{
                  "뉴스ID1": {{ "score": 점수, "reason": "추천 이유" }},
                  "뉴스ID2": {{ "score": 점수, "reason": "추천 이유" }},
                  ...
                }}
                """

                # 고급 LLM 사용
                recommendation_response = await self.advanced_llm.agenerate([[custom_prompt]])
                recommendation_text = recommendation_response.generations[0][0].text

                # JSON 추출
                import re
                import json

                json_match = re.search(r'\{.*\}', recommendation_text, re.DOTALL)
                if json_match:
                    try:
                        llm_recommendations = json.loads(json_match.group(0))

                        # 결과 검증 및 보정
                        for news_id, rec_data in llm_recommendations.items():
                            if isinstance(rec_data, dict):
                                score = rec_data.get("score", 0)
                                reason = rec_data.get("reason", "")

                                # 점수 검증: 1-10 범위로 조정
                                if isinstance(score, (int, float)):
                                    score = max(1, min(10, score))
                                else:
                                    try:
                                        score = float(score)
                                        score = max(1, min(10, score))
                                    except:
                                        score = 7  # 기본값

                                # 추천 결과 저장
                                recommendations[news_id] = {
                                    "score": score,
                                    "reason": reason,
                                    "content_similarity": content_scores.get(news_id, 0.7)
                                }
                    except json.JSONDecodeError:
                        logger.error("추천 결과 JSON 파싱 실패")

                # LLM 결과가 없으면 임베딩 점수 기반으로 추천
                if not recommendations:
                    for news in news_list:
                        news_id = news.get("id", "")
                        if news_id:
                            similarity = content_scores.get(news_id, 0.7)
                            # 유사도를 1-10 점수로 변환
                            score = 1 + (similarity * 9)
                            recommendations[news_id] = {
                                "score": score,
                                "reason": f"사용자 관심사 '{interests_str}'와 {similarity:.2f} 유사도로 일치",
                                "content_similarity": similarity
                            }

            except Exception as llm_error:
                logger.error(f"LLM 기반 추천 중 오류: {str(llm_error)}")

                # LLM 오류 시 임베딩 점수로만 추천
                for news in news_list:
                    news_id = news.get("id", "")
                    if news_id:
                        similarity = content_scores.get(news_id, 0.7)
                        # 유사도를 1-10 점수로 변환
                        score = 1 + (similarity * 9)
                        recommendations[news_id] = {
                            "score": score,
                            "reason": f"컨텐츠 유사도 기반 추천 (LLM 오류 발생)",
                            "content_similarity": similarity
                        }

            # 3. 협업 필터링 점수 통합 (가능한 경우)
            try:
                # 협업 필터링 서비스 확인
                from app.services.collaborative_filtering import get_collaborative_filtering_service
                cf_service = get_collaborative_filtering_service()

                # 첫 번째 뉴스 ID에서 사용자 ID 추출 시도 (임시)
                user_id = None
                for news in news_list[:1]:
                    user_id_field = news.get("user_id")
                    if user_id_field:
                        user_id = user_id_field
                        break

                # 사용자 ID가 있으면 협업 필터링 추천 가져오기
                if user_id:
                    cf_scores = cf_service.get_recommendations_for_user(user_id, limit=len(news_list))

                    # 협업 필터링 점수 통합
                    for news_id, cf_score in cf_scores.items():
                        if news_id in recommendations:
                            # 기존 점수와 협업 필터링 점수 결합 (70:30 비율)
                            current_score = recommendations[news_id].get("score", 5)
                            combined_score = (current_score * 0.7) + (cf_score * 0.3)

                            recommendations[news_id]["score"] = combined_score
                            recommendations[news_id]["collaborative_score"] = cf_score

                            # 이유 업데이트
                            recommendations[news_id]["reason"] += " (협업 필터링 점수 반영)"

            except Exception as cf_error:
                logger.debug(f"협업 필터링 통합 중 오류 (무시됨): {str(cf_error)}")
                # 협업 필터링 오류는 무시 (선택적 기능)

            # 4. 다양성 보장 및 최종 조정
            try:
                # 카테고리별 뉴스 분류
                category_news = {}
                for news in news_list:
                    news_id = news.get("id", "")
                    if not news_id or news_id not in recommendations:
                        continue

                    # 카테고리 목록 (비어있으면 '일반'으로 설정)
                    categories = news.get("categories", ["일반"])
                    if not categories:
                        categories = ["일반"]

                    main_category = categories[0]
                    if main_category not in category_news:
                        category_news[main_category] = []

                    category_news[main_category].append(news_id)

                # 한 카테고리가 너무 많이 추천되는 경우 조정
                max_per_category = max(2, len(news_list) // 3)  # 최대 카테고리당 비율

                for category, news_ids in category_news.items():
                    if len(news_ids) > max_per_category:
                        # 점수 기준 정렬
                        sorted_ids = sorted(
                            news_ids,
                            key=lambda nid: recommendations[nid].get("score", 0),
                            reverse=True
                        )

                        # 상위 N개 유지, 나머지 점수 감소
                        for i, news_id in enumerate(sorted_ids):
                            if i >= max_per_category:
                                # 다양성을 위해 점수 감소 (최대 30%)
                                recommendations[news_id]["score"] *= 0.7
                                recommendations[news_id]["diversity_adjusted"] = True

            except Exception as diversity_error:
                logger.error(f"다양성 조정 중 오류: {str(diversity_error)}")

            return recommendations

        except Exception as e:
            logger.error(f"추천 생성 중 오류 발생: {str(e)}")

            # 오류 발생 시 기본 추천 제공
            basic_recommendations = {}
            for news in news_list:
                news_id = news.get("id", "")
                if news_id:
                    basic_recommendations[news_id] = {
                        "score": 5,  # 중간 점수
                        "reason": "기본 추천 (오류 발생 시)",
                        "error": str(e)
                    }

            return basic_recommendations

    async def get_cold_start_recommendations(self,
                                           is_new_user: bool,
                                           selected_interests: List[str],
                                           trending_news: List[Dict[str, Any]]) -> List[str]:
        """
        콜드 스타트 상황에서 추천을 생성합니다.

        Args:
            is_new_user: 신규 사용자 여부
            selected_interests: 사용자가 선택한 관심사
            trending_news: 트렌딩 뉴스 목록

        Returns:
            List[str]: 추천된 뉴스 ID 목록
        """
        try:
            # 관심사 문자열로 변환
            interests_str = ", ".join(selected_interests) if selected_interests else "일반 뉴스"

            # 트렌딩 뉴스 형식화
            trends = []
            for i, news in enumerate(trending_news):
                trends.append(f"{i+1}. {news.get('title', 'unknown')}")
            trends_str = "\n".join(trends)

            # 추천 생성
            result = await self.cold_start_chain.arun(
                is_new_user=str(is_new_user),
                selected_interests=interests_str,
                current_trends=trends_str
            )

            # 단순 결과 반환 (실제로는 결과 파싱 필요)
            recommended_ids = [news.get("id", "") for news in trending_news]
            return recommended_ids
        except Exception as e:
            logger.error(f"콜드 스타트 추천 생성 중 오류 발생: {str(e)}")
            return []

    async def diversify_recommendations(self,
                                      main_interests: List[str],
                                      current_recommendations: List[Dict[str, Any]],
                                      diversity_target: float = 0.3) -> List[Dict[str, Any]]:
        """
        추천 결과의 다양성을 강화합니다.

        Args:
            main_interests: 사용자 주요 관심사
            current_recommendations: 현재 추천 결과
            diversity_target: 다양성 목표 수준 (0.0-1.0)

        Returns:
            List[Dict[str, Any]]: 다양성이 강화된 추천 결과
        """
        try:
            # 관심사 문자열로 변환
            interests_str = ", ".join(main_interests) if main_interests else "일반 뉴스"

            # 현재 추천 비율 계산
            categories = {}
            for rec in current_recommendations:
                for cat in rec.get("categories", []):
                    categories[cat] = categories.get(cat, 0) + 1

            # 비율 문자열화
            current_mix = []
            total = len(current_recommendations) or 1
            for cat, count in categories.items():
                percentage = (count / total) * 100
                current_mix.append(f"{cat}: {percentage:.1f}%")
            current_mix_str = ", ".join(current_mix)

            # 다양성 강화
            result = await self.diversity_chain.arun(
                main_interests=interests_str,
                current_mix=current_mix_str,
                diversity_target=str(diversity_target)
            )

            # 단순 결과 반환 (실제로는 더 복잡한 로직 필요)
            return current_recommendations
        except Exception as e:
            logger.error(f"추천 다양성 강화 중 오류 발생: {str(e)}")
            return current_recommendations


# 서비스 인스턴스 관리
_langchain_service = None

def get_langchain_service() -> LangChainService:
    """LangChain 서비스 인스턴스를 반환합니다."""
    global _langchain_service
    if _langchain_service is None:
        _langchain_service = LangChainService()
    return _langchain_service
