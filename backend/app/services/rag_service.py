import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from bson.objectid import ObjectId  # MongoDB ObjectId 추가

# LangChain (정확한 최신 import 위치)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma, FAISS
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import EmbeddingsFilter
from langchain_core.documents import Document
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

# MongoDB
from app.db.mongodb import (
    news_collection,
    user_interactions_collection
)

# Config
from app.core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGService:
    """Service for implementing Retrieval Augmented Generation with LangChain"""

    def __init__(self):
        # Initialize OpenAI embeddings
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.OPENAI_API_KEY
        )

        # Initialize LLM
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.2,
            openai_api_key=settings.OPENAI_API_KEY
        )

        # Create Chroma directory if it doesn't exist
        self.chroma_dir = os.path.join(settings.DATA_DIR, "chroma")
        os.makedirs(self.chroma_dir, exist_ok=True)

        # Create FAISS directory if it doesn't exist
        self.faiss_dir = os.path.join(settings.DATA_DIR, "faiss")
        os.makedirs(self.faiss_dir, exist_ok=True)

        # Initialize vector stores
        self._init_vectorstores()

        # Create a retriever with contextual compression
        self.retriever = self._create_retriever()

        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

        # Setup the conversational chain
        self.conversational_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.retriever,
            memory=self.memory,
            return_source_documents=True
        )

    def _init_vectorstores(self):
        """Initialize vector stores (both Chroma and FAISS)"""
        try:
            # 기존 Chroma DB 폴더 검사
            if os.path.exists(self.chroma_dir):
                import shutil
                # 손상된 DB일 수 있으므로 DB 파일 검사
                try:
                    # DB 파일 검사 및 필요 시 삭제
                    sqlite_file = os.path.join(self.chroma_dir, "chroma.sqlite3")
                    if os.path.exists(sqlite_file):
                        try:
                            # sqlite3 파일 유효성 검사
                            import sqlite3
                            conn = sqlite3.connect(sqlite_file)
                            cursor = conn.cursor()
                            cursor.execute("PRAGMA integrity_check")
                            conn.close()
                            logger.info("Chroma DB integrity check passed")
                        except Exception as db_err:
                            # 손상된 파일 삭제
                            logger.error(f"Chroma DB integrity check failed: {db_err}")
                            os.remove(sqlite_file)
                            logger.info(f"Removed corrupted Chroma DB file")
                except Exception as rm_err:
                    logger.warning(f"Failed to check/remove Chroma DB file: {rm_err}")

            # Chroma DB 생성 시도
            self.chroma_vectorstore = Chroma(
                collection_name="news_embeddings",
                embedding_function=self.embeddings,
                persist_directory=self.chroma_dir
            )
            logger.info(f"Loaded existing Chroma vectorstore from {self.chroma_dir}")
        except Exception as e:
            # If loading fails, create a new one
            logger.warning(f"Could not load Chroma DB: {e}. Creating a new one.")
            # 인메모리 인스턴스로 먼저 만들고
            try:
                self.chroma_vectorstore = Chroma(
                    collection_name="news_embeddings",
                    embedding_function=self.embeddings
                )
                # 그 다음 디스크에 저장
                self.chroma_vectorstore = Chroma(
                    collection_name="news_embeddings",
                    embedding_function=self.embeddings,
                    persist_directory=self.chroma_dir
                )
                # Save empty vectorstore
                self.chroma_vectorstore.persist()
                logger.info("Successfully created new Chroma DB")
            except Exception as create_err:
                # 최후의 수단: 인메모리만 사용
                logger.error(f"Failed to create persistent Chroma DB: {create_err}")
                self.chroma_vectorstore = Chroma(
                    collection_name="news_embeddings",
                    embedding_function=self.embeddings
                )
                logger.warning("Using in-memory Chroma vectorstore as fallback")

        # For FAISS, check if index file exists
        faiss_index_path = os.path.join(self.faiss_dir, "index.faiss")
        faiss_docstore_path = os.path.join(self.faiss_dir, "docstore.json")

        if os.path.exists(faiss_index_path) and os.path.exists(faiss_docstore_path):
            # Load existing FAISS index
            self.faiss_vectorstore = FAISS.load_local(
                self.faiss_dir,
                self.embeddings,
                "index"
            )
            logger.info(f"Loaded existing FAISS vectorstore from {self.faiss_dir}")
        else:
            # Create new empty FAISS index
            self.faiss_vectorstore = FAISS.from_texts(
                ["Placeholder text for initialization"],
                self.embeddings
            )
            # Save empty FAISS index
            self.faiss_vectorstore.save_local(self.faiss_dir, "index")
            logger.info("Created new FAISS vectorstore")

        # Default to using Chroma
        self.vectorstore = self.chroma_vectorstore

    def _create_retriever(self):
        """Create a retriever with contextual compression"""
        embeddings_filter = EmbeddingsFilter(
            embeddings=self.embeddings,
            similarity_threshold=0.75
        )

        retriever = ContextualCompressionRetriever(
            base_compressor=embeddings_filter,
            base_retriever=self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 10}
            )
        )

        return retriever

    def switch_vectorstore(self, store_type: str = "chroma"):
        """Switch between vector stores

        Args:
            store_type: Type of vector store to use ('chroma' or 'faiss')
        """
        if store_type.lower() == "chroma":
            self.vectorstore = self.chroma_vectorstore
            logger.info("Switched to Chroma vectorstore")
        elif store_type.lower() == "faiss":
            self.vectorstore = self.faiss_vectorstore
            logger.info("Switched to FAISS vectorstore")
        else:
            logger.warning(f"Unknown vectorstore type: {store_type}. Using Chroma.")
            self.vectorstore = self.chroma_vectorstore

        # Update retriever
        self.retriever = self._create_retriever()

        # Update conversational chain
        self.conversational_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.retriever,
            memory=self.memory,
            return_source_documents=True
        )

    def index_news_articles(self, days: int = 7, batch_size: int = 50, store_type: str = "both") -> int:
        """Index recent news articles in the vector store"""
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get recent news articles
        recent_news = list(news_collection.find({
            "created_at": {"$gte": start_date}
        }))

        if not recent_news:
            return 0

        logger.info(f"Indexing {len(recent_news)} news articles")

        # Process in batches
        indexed_count = 0
        for i in range(0, len(recent_news), batch_size):
            batch = recent_news[i:i+batch_size]

            # Create documents
            documents = []
            for news in batch:
                # Combine title and content
                full_text = f"Title: {news['title']}\n\nContent: {news['content']}"

                # Add metadata
                metadata = {
                    "news_id": news["_id"],
                    "title": news["title"],
                    "source": news["source"],
                    "url": news["url"],
                    "published_date": news["published_date"].isoformat(),
                    "categories": news.get("categories", []),
                    "trust_score": news.get("trust_score"),
                    "sentiment_score": news.get("sentiment_score")
                }

                documents.append(Document(
                    page_content=full_text,
                    metadata=metadata
                ))

            # Add to appropriate vectorstore(s)
            if store_type.lower() in ["chroma", "both"]:
                self.chroma_vectorstore.add_documents(documents)
                self.chroma_vectorstore.persist()

            if store_type.lower() in ["faiss", "both"]:
                self.faiss_vectorstore.add_documents(documents)
                self.faiss_vectorstore.save_local(self.faiss_dir, "index")

            indexed_count += len(documents)
            logger.info(f"Indexed {indexed_count} documents so far")

        # If we just indexed to both, default to using Chroma
        if store_type.lower() == "both":
            self.vectorstore = self.chroma_vectorstore
            self.retriever = self._create_retriever()
            self.conversational_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.retriever,
                memory=self.memory,
                return_source_documents=True
            )

        return indexed_count

    def search_news_with_query(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for news articles similar to the query using RAG"""
        # Get relevant documents
        docs = self.retriever.get_relevant_documents(query)
        docs = docs[:limit]  # Limit results

        # Extract news IDs and metadata
        results = []
        for doc in docs:
            metadata = doc.metadata

            # Get full news article from database for complete information
            try:
                news_id_obj = ObjectId(metadata["news_id"])
                news = news_collection.find_one({"_id": news_id_obj})
            except:
                # 실패하면 문자열 ID로 시도
                news = news_collection.find_one({"_id": metadata["news_id"]})
            if news:
                result = {
                    "id": news["_id"],
                    "title": news["title"],
                    "source": news["source"],
                    "published_date": news["published_date"],
                    "summary": news.get("summary"),
                    "url": news["url"],
                    "trust_score": news.get("trust_score"),
                    "sentiment_score": news.get("sentiment_score"),
                    "categories": news.get("categories", []),
                    "similarity_score": 1.0  # Default similarity score
                }
                results.append(result)

        return results

    def generate_news_summary(self, news_id: str) -> Optional[str]:
        """Generate a summary for a news article using LLM"""
        # Get news article
        news = news_collection.find_one({"_id": news_id})
        if not news:
            return None

        try:
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert news editor who creates concise, informative summaries.
                 Summarize the following news article in 2-3 sentences. Focus on the key facts and insights.
                 Do not include your personal opinions. Keep the summary factual and objective."""),
                ("user", "Title: {title}\n\nContent: {content}")
            ])

            # Create chain
            summary_chain = LLMChain(llm=self.llm, prompt=prompt)

            # Generate summary
            summary = summary_chain.run(title=news["title"], content=news["content"])

            # Update article in database
            news_collection.update_one(
                {"_id": news_id},
                {"$set": {
                    "summary": summary.strip(),
                    "updated_at": datetime.utcnow()
                }}
            )

            return summary.strip()

        except Exception as e:
            logger.error(f"Error generating summary for news {news_id}: {e}")
            return None

    def chat_with_news(self, user_id: str, query: str) -> Dict[str, Any]:
        """Chat with news articles using RAG"""
        try:
            # Use the conversational chain
            result = self.conversational_chain({"question": query})

            # Extract response and source documents
            answer = result.get("answer", "I couldn't find an answer to your question.")
            source_docs = result.get("source_documents", [])

            # Extract source metadata
            sources = []
            for doc in source_docs:
                metadata = doc.metadata
                sources.append({
                    "news_id": metadata.get("news_id"),
                    "title": metadata.get("title"),
                    "source": metadata.get("source"),
                    "url": metadata.get("url"),
                    "published_date": metadata.get("published_date")
                })

            # Record user interaction
            for source in sources:
                self._record_chat_interaction(user_id, source.get("news_id"), query)

            return {
                "answer": answer,
                "sources": sources
            }

        except Exception as e:
            logger.error(f"Error in chat with news: {e}")
            return {
                "answer": "I'm sorry, I encountered an error while processing your question.",
                "sources": []
            }

    def _record_chat_interaction(self, user_id: str, news_id: str, query: str) -> None:
        """Record a chat interaction for analytics"""
        if not news_id:
            return

        interaction = {
            "user_id": user_id,
            "news_id": news_id,
            "interaction_type": "chat",
            "timestamp": datetime.utcnow(),
            "metadata": {
                "query": query
            }
        }

        try:
            user_interactions_collection.insert_one(interaction)
        except Exception as e:
            logger.error(f"Error recording chat interaction: {e}")

    def generate_topic_analysis(self, query: str) -> Dict[str, Any]:
        """Generate an analysis of a news topic using RAG"""
        try:
            # Get relevant documents
            docs = self.retriever.get_relevant_documents(query)

            if not docs:
                return {
                    "topic": query,
                    "summary": "Not enough information available on this topic.",
                    "key_points": [],
                    "sources": []
                }

            # Extract content from documents
            content = "\n\n".join([doc.page_content for doc in docs[:5]])

            # Create prompt for topic analysis
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert news analyst who creates insightful topic analyses.
                 Based on the provided news articles, generate:
                 1. A comprehensive summary of the topic (2-3 paragraphs)
                 2. 3-5 key points about the topic
                 3. Any controversies or different perspectives on the topic

                 Format your response as a JSON object with keys:
                 "summary", "key_points", and "controversies".
                 Each key_point should be a string. Controversies should be an array of perspectives.
                 """),
                ("user", "Topic: {topic}\n\nNews articles:\n{content}")
            ])

            # Create chain
            analysis_chain = LLMChain(llm=self.llm, prompt=prompt)

            # Generate analysis
            analysis_text = analysis_chain.run(topic=query, content=content)

            # Parse JSON response
            try:
                import json
                analysis = json.loads(analysis_text)
            except:
                # Fallback if JSON parsing fails
                analysis = {
                    "summary": analysis_text,
                    "key_points": [],
                    "controversies": []
                }

            # Extract source metadata
            sources = []
            for doc in docs[:5]:
                metadata = doc.metadata
                sources.append({
                    "news_id": metadata.get("news_id"),
                    "title": metadata.get("title"),
                    "source": metadata.get("source"),
                    "url": metadata.get("url"),
                    "published_date": metadata.get("published_date")
                })

            return {
                "topic": query,
                "summary": analysis.get("summary", ""),
                "key_points": analysis.get("key_points", []),
                "controversies": analysis.get("controversies", []),
                "sources": sources
            }

        except Exception as e:
            logger.error(f"Error generating topic analysis: {e}")
            return {
                "topic": query,
                "summary": "An error occurred while analyzing this topic.",
                "key_points": [],
                "controversies": [],
                "sources": []
            }


# Helper function to get service instance
def get_rag_service() -> RAGService:
    """Get RAG service instance"""
    return RAGService()
