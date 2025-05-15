/**
 * API 타입 정의
 */

// 뉴스 기본 인터페이스
export interface News {
  _id: string;
  title: string;
  content: string;
  url: string;
  source: string;
  published_date: string;
  author?: string;
  image_url?: string;
  summary?: string;
  categories: string[];
  keywords: string[];
  created_at: string;
  updated_at: string;
  trust_score?: number;
  sentiment_score?: number;
  ai_enhanced?: boolean;  // AI로 향상되었는지 여부
  metadata?: Record<string, unknown>;
}

// 뉴스 요약 인터페이스
export interface NewsSummary {
  id: string;
  title: string;
  source: string;
  published_date: string;
  summary?: string;
  image_url?: string;
  trust_score?: number;
  sentiment_score?: number;
  similarity_score?: number;
  categories: string[];
}

// 뉴스 검색 쿼리 인터페이스
export interface NewsSearchQuery {
  query: string;
  categories?: string[];
  sources?: string[];
  start_date?: string;
  end_date?: string;
  min_trust_score?: number;
  sentiment?: 'positive' | 'negative' | 'neutral';
  limit?: number;
  skip?: number;
}

// 사용자 인터페이스
export interface User {
  _id: string;
  username: string;
  email: string;
  created_at: string;
  preferences?: {
    categories?: string[];
    sources?: string[];
  };
  metadata?: Record<string, unknown>;
}

// 상호작용 타입
export type InteractionType = 'view' | 'click' | 'read' | 'like' | 'share';

// 상호작용 인터페이스
export interface Interaction {
  user_id: string;
  news_id: string;
  interaction_type: InteractionType;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

// 상세 상호작용 인터페이스
export interface DetailedInteraction extends Interaction {
  dwell_time_seconds?: number;
  scroll_depth_percent?: number;
}

// API 응답 에러 인터페이스
export interface ApiError {
  detail: string;
  status_code: number;
}

// 분석 결과 인터페이스
export interface AnalysisResult {
  news_id: string;
  analyzed_at: string;
}

// 신뢰도 분석 결과 인터페이스
export interface TrustAnalysisResult extends AnalysisResult {
  trust_score: number;
  trust_factors: Record<string, number>;
}

// 감정 분석 결과 인터페이스
export interface SentimentAnalysisResult extends AnalysisResult {
  sentiment: {
    score: number;
    label: 'positive' | 'negative' | 'neutral';
    confidence: number;
  };
}

// 추천 결과 인터페이스
export interface RecommendationResult {
  news_id: string;
  score: number;
  reason?: string;
}

// RAG 검색 결과 인터페이스
export interface RagSearchResult {
  news: NewsSummary;
  relevance_score: number;
  context_snippet?: string;
}

// 헬스 체크 응답 인터페이스
export interface HealthCheckResponse {
  status: 'ok' | 'degraded';
  components: {
    api: 'ok' | 'error';
    database: 'ok' | 'error';
    database_error?: string;
    openai_api: 'ok' | 'not_configured' | 'error';
  };
  timestamp: string;
}
