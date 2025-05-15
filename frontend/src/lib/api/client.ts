/**
 * API 클라이언트
 * 백엔드 API와 통신하기 위한 유틸리티 함수들을 제공합니다.
 */

import { type News, type NewsSummary, NewsSearchQuery, type HealthCheckResponse } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

/**
 * API 요청을 처리하는 기본 함수
 */
async function fetchApi<T = unknown>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  // 기본 헤더 설정
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const config = {
    ...options,
    headers,
  };

  try {
    console.log(`📡 API 요청: ${options.method || 'GET'} ${url}`);
    const response = await fetch(url, config);

    // 에러 처리
    if (!response.ok) {
      const errorText = await response.text();
      let errorDetail = '';

      try {
        const errorJson = JSON.parse(errorText);
        errorDetail = errorJson.detail || errorJson.message || '';
      } catch {
        errorDetail = errorText || `HTTP 상태 코드: ${response.status}`;
      }

      const errorMessage = `API 요청 오류: ${response.status} ${response.statusText}${errorDetail ? ` - ${errorDetail}` : ''}`;
      console.error(`❌ ${errorMessage}`);
      throw new Error(errorMessage);
    }

    // 응답이 비어있는 경우 처리
    if (response.status === 204) {
      return {} as T;
    }

    // 응답이 JSON이 아닐 경우를 대비해 체크
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const data = await response.json();
      console.log(`✅ API 응답 성공: ${options.method || 'GET'} ${url}`);
      return data as T;
    } else {
      const text = await response.text();
      console.log(`✅ API 응답 성공 (텍스트): ${options.method || 'GET'} ${url}`);
      // 텍스트 응답을 객체로 변환하여 반환
      return { text, status: response.status } as unknown as T;
    }
  } catch (error) {
    // 네트워크 오류 또는 기타 예외 처리
    if (error instanceof Error) {
      console.error(`❌ API 요청 실패: ${options.method || 'GET'} ${url} - ${error.message}`);
      throw new Error(`API 요청 실패: ${error.message}`);
    } else {
      console.error(`❌ API 요청 실패: ${options.method || 'GET'} ${url} - 알 수 없는 오류`);
      throw new Error('API 요청 중 알 수 없는 오류가 발생했습니다');
    }
  }
}

/**
 * API 클라이언트
 */
export const apiClient = {
  /**
   * 인증 API
   */
  auth: {
    /**
     * 로그인
     */
    login: async (username: string, password: string): Promise<{
      access_token: string;
      token_type: string;
      user_id: string;
      username: string;
    }> => {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      try {
        const response = await fetchApi<{
          access_token: string;
          token_type: string;
          user_id: string;
          username: string;
        }>('/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: formData.toString(),
        });
        return response;
      } catch (error) {
        console.error('로그인 중 오류:', error);
        throw error;
      }
    },

    /**
     * 회원가입
     */
    register: async (username: string, email: string, password: string): Promise<{
      status: string;
      message: string;
      user_id: string;
      verification_required?: boolean;
    }> => {
      try {
        return await fetchApi<{
          status: string;
          message: string;
          user_id: string;
          verification_required?: boolean;
        }>('/api/auth/register', {
          method: 'POST',
          body: JSON.stringify({
            username,
            email,
            password,
          }),
        });
      } catch (error) {
        console.error('회원가입 중 오류:', error);
        throw error;
      }
    },

    /**
     * 이메일 인증 코드 요청
     */
    requestVerificationCode: async (email: string): Promise<{
      status: string;
      message: string;
      expires_in_minutes: number;
    }> => {
      try {
        return await fetchApi<{
          status: string;
          message: string;
          expires_in_minutes: number;
        }>('/api/email/send-verification-code', {
          method: 'POST',
          body: JSON.stringify({ email }),
        });
      } catch (error) {
        console.error('인증 코드 요청 중 오류:', error);
        throw error;
      }
    },

    /**
     * 이메일 인증 코드 확인
     */
    verifyCode: async (email: string, code: string): Promise<{
      status: string;
      message: string;
      verified: boolean;
    }> => {
      try {
        return await fetchApi<{
          status: string;
          message: string;
          verified: boolean;
        }>('/api/email/verify-code', {
          method: 'POST',
          body: JSON.stringify({ email, code }),
        });
      } catch (error) {
        console.error('인증 코드 확인 중 오류:', error);
        throw error;
      }
    },
  },

  /**
   * 뉴스 API
   */
  news: {
    /**
     * 뉴스 목록 가져오기
     */
    getAll: async (params: {
      limit?: number;
      skip?: number;
      source?: string;
      category?: string;
    } = {}): Promise<News[]> => {
      const queryParams = new URLSearchParams();

      if (params.limit) queryParams.append('limit', params.limit.toString());
      if (params.skip) queryParams.append('skip', params.skip.toString());
      if (params.source) queryParams.append('source', params.source);
      if (params.category) queryParams.append('category', params.category);

      const query = queryParams.toString();
      try {
        return await fetchApi<News[]>(`/news?${query}`);
      } catch (error) {
        console.error('뉴스 목록을 가져오는 중 오류:', error);
        return [];
      }
    },

    /**
     * 특정 ID의 뉴스 가져오기
     */
    getById: async (id: string): Promise<News> => {
      try {
        return await fetchApi<News>(`/news/${id}`);
      } catch (error) {
        console.error(`ID ${id}의 뉴스를 가져오는 중 오류:`, error);
        throw error;
      }
    },

    /**
     * 뉴스 검색
     */
    search: async (query: string): Promise<News[]> => {
      try {
        return await fetchApi<News[]>('/news/search', {
          method: 'POST',
          body: JSON.stringify({ query }),
        });
      } catch (error) {
        console.error('뉴스 검색 중 오류:', error);
        return [];
      }
    },

    /**
     * 트렌딩 뉴스 가져오기
     */
    getTrending: async (limit = 10): Promise<NewsSummary[]> => {
      try {
        return await fetchApi<NewsSummary[]>(`/news/trending?limit=${limit}`);
      } catch (error) {
        console.error('트렌딩 뉴스를 가져오는 중 오류:', error);
        return [];
      }
    },

    /**
     * 키워드 기반 뉴스 검색
     */
    searchByKeyword: async (keyword: string, limit = 20): Promise<News[]> => {
      try {
        return await fetchApi<News[]>('/news/search', {
          method: 'POST',
          body: JSON.stringify({ query: keyword, limit }),
        });
      } catch (error) {
        console.error(`키워드 '${keyword}'로 뉴스를 검색하는 중 오류:`, error);
        return [];
      }
    },

    /**
     * 뉴스 댓글 가져오기
     */
    getComments: async (newsId: string): Promise<Comment[]> => {
      try {
        return await fetchApi<Comment[]>(`/news/${newsId}/comments`);
      } catch (error) {
        console.error(`뉴스 ${newsId}의 댓글을 가져오는 중 오류:`, error);
        return [];
      }
    },

    /**
     * 뉴스 댓글 작성
     */
    addComment: async (newsId: string, userId: string, content: string): Promise<Comment> => {
      try {
        return await fetchApi<Comment>(`/news/${newsId}/comments`, {
          method: 'POST',
          body: JSON.stringify({
            user_id: userId,
            content,
          }),
        });
      } catch (error) {
        console.error(`뉴스 ${newsId}에 댓글을 작성하는 중 오류:`, error);
        throw error;
      }
    },

    /**
     * 뉴스 통계 가져오기
     */
    getStats: async (newsId: string): Promise<NewsStats> => {
      try {
        return await fetchApi<NewsStats>(`/news/${newsId}/stats`);
      } catch (error) {
        console.error(`뉴스 ${newsId}의 통계를 가져오는 중 오류:`, error);
        return { views: 0, likes: 0, comments: 0, shares: 0 };
      }
    },

    /**
     * 뉴스 북마크 설정/해제
     */
    toggleBookmark: async (newsId: string, userId: string, bookmarked: boolean): Promise<{ success: boolean }> => {
      try {
        return await fetchApi<{ success: boolean }>(`/news/${newsId}/bookmark`, {
          method: 'POST',
          body: JSON.stringify({
            user_id: userId,
            bookmarked,
          }),
        });
      } catch (error) {
        console.error(`뉴스 ${newsId}의 북마크 상태를 변경하는 중 오류:`, error);
        return { success: false };
      }
    },
  },

  /**
   * 사용자 API
   */
  users: {
    /**
     * 사용자 추천 뉴스 가져오기
     */
    getRecommendations: async (userId: string, limit = 10): Promise<NewsSummary[]> => {
      try {
        return await fetchApi<NewsSummary[]>(`/recommendations/${userId}?limit=${limit}`);
      } catch (error) {
        console.error(`사용자 ${userId}의 추천 뉴스를 가져오는 중 오류:`, error);
        return [];
      }
    },

    /**
     * 사용자 상호작용 기록
     */
    recordInteraction: async (
      userId: string,
      newsId: string,
      interactionType: 'view' | 'click' | 'read' | 'like' | 'share'
    ): Promise<{ message: string }> => {
      try {
        return await fetchApi<{ message: string }>('/interaction', {
          method: 'POST',
          body: JSON.stringify({
            user_id: userId,
            news_id: newsId,
            interaction_type: interactionType,
          }),
        });
      } catch (error) {
        console.error(`사용자 상호작용 기록 중 오류:`, error);
        return { message: '상호작용 기록 실패' };
      }
    },

    /**
     * 사용자 상호작용 이력 가져오기
     */
    getUserInteractions: async (userId: string, newsId?: string): Promise<UserInteractions> => {
      const endpoint = newsId
        ? `/user-interactions?userId=${userId}&newsId=${newsId}`
        : `/user-interactions?userId=${userId}`;
      try {
        return await fetchApi<UserInteractions>(endpoint);
      } catch (error) {
        console.error(`사용자 상호작용 이력 조회 중 오류:`, error);
        return { userId, interactions: [] };
      }
    },
  },

  /**
   * AI 및 모델 API
   */
  ai: {
    /**
     * 텍스트 임베딩 생성
     */
    getTextEmbedding: async (text: string): Promise<number[]> => {
      try {
        const res = await fetchApi<{ embedding: number[] }>('/text/embeddings', {
          method: 'POST',
          body: JSON.stringify({ text }),
        });
        return res.embedding;
      } catch (error) {
        console.error('텍스트 임베딩 생성 중 오류:', error);
        return [];
      }
    },

    /**
     * 뉴스 벡터 검색
     */
    searchNewsByVector: async (query: string, limit = 10): Promise<NewsSummary[]> => {
      try {
        return await fetchApi<NewsSummary[]>('/rag/search', {
          method: 'POST',
          body: JSON.stringify({ query, limit }),
        });
      } catch (error) {
        console.error('뉴스 벡터 검색 중 오류:', error);
        return [];
      }
    },

    /**
     * 뉴스에 대해 질문하기
     */
    askQuestionAboutNews: async (newsId: string, question: string): Promise<{ answer: string }> => {
      try {
        return await fetchApi<{ answer: string }>(`/news/${newsId}/ask`, {
          method: 'POST',
          body: JSON.stringify({ question }),
        });
      } catch (error) {
        console.error(`뉴스 ${newsId}에 대한 질문 처리 중 오류:`, error);
        return { answer: '답변을 가져오지 못했습니다.' };
      }
    },

    /**
     * 뉴스 신뢰도 분석
     */
    analyzeTrustScore: async (newsId: string): Promise<{
      news_id: string;
      trust_score: number;
      trust_factors: Record<string, number>;
    }> => {
      try {
        return await fetchApi<{
          news_id: string;
          trust_score: number;
          trust_factors: Record<string, number>;
        }>(`/news/${newsId}/trust-analysis`, {
          method: 'POST',
        });
      } catch (error) {
        console.error(`뉴스 ${newsId}의 신뢰도 분석 중 오류:`, error);
        return {
          news_id: newsId,
          trust_score: 0,
          trust_factors: {},
        };
      }
    },

    /**
     * 뉴스 감정 분석
     */
    analyzeSentiment: async (newsId: string): Promise<{
      news_id: string;
      sentiment: {
        score: number;
        label: string;
        positive: number;
        negative: number;
        neutral: number;
      }
    }> => {
      try {
        return await fetchApi<{
          news_id: string;
          sentiment: {
            score: number;
            label: string;
            positive: number;
            negative: number;
            neutral: number;
          }
        }>(`/news/${newsId}/sentiment-analysis`, {
          method: 'POST',
        });
      } catch (error) {
        console.error(`뉴스 ${newsId}의 감정 분석 중 오류:`, error);
        return {
          news_id: newsId,
          sentiment: {
            score: 0,
            label: 'neutral',
            positive: 0,
            negative: 0,
            neutral: 0,
          },
        };
      }
    },

    /**
     * 뉴스에서 키워드 추출
     */
    extractKeyPhrases: async (newsId: string, limit = 10): Promise<{
      news_id: string;
      key_phrases: string[];
    }> => {
      try {
        return await fetchApi<{
          news_id: string;
          key_phrases: string[];
        }>(`/news/${newsId}/key-phrases?limit=${limit}`, {
          method: 'POST',
        });
      } catch (error) {
        console.error(`뉴스 ${newsId}의 키워드 추출 중 오류:`, error);
        return {
          news_id: newsId,
          key_phrases: [],
        };
      }
    },

    /**
     * 뉴스 내용 요약
     */
    summarizeNews: async (newsId: string, max_length = 200): Promise<{
      news_id: string;
      summary: string;
    }> => {
      try {
        return await fetchApi<{
          news_id: string;
          summary: string;
        }>(`/news/${newsId}/summarize?max_length=${max_length}`, {
          method: 'POST',
        });
      } catch (error) {
        console.error(`뉴스 ${newsId}의 요약 중 오류:`, error);
        return {
          news_id: newsId,
          summary: '',
        };
      }
    },

    /**
     * 협업 필터링 기반 추천
     */
    getCollaborativeFilteringRecommendations: async (userId: string, limit = 10): Promise<NewsSummary[]> => {
      try {
        return await fetchApi<NewsSummary[]>(`/collaborative-filtering/recommendations/${userId}?limit=${limit}`);
      } catch (error) {
        console.error(`협업 필터링 추천 중 오류:`, error);
        return [];
      }
    },

    /**
     * 유사한 사용자 찾기
     */
    getSimilarUsers: async (userId: string, limit = 5): Promise<{
      user_id: string;
      similar_users: Array<{ user_id: string; similarity: number }>
    }> => {
      try {
        return await fetchApi<{
          user_id: string;
          similar_users: Array<{ user_id: string; similarity: number }>
        }>(`/collaborative-filtering/similar-users/${userId}?limit=${limit}`);
      } catch (error) {
        console.error(`유사한 사용자 찾기 중 오류:`, error);
        return {
          user_id: userId,
          similar_users: [],
        };
      }
    },

    /**
     * 개인화된 뉴스 추천받기
     */
    getPersonalizedNews: async (userId: string, limit = 8): Promise<NewsSummary[]> => {
      try {
        return await fetchApi<NewsSummary[]>(`/recommendation/personalized/${userId}?limit=${limit}`);
      } catch (error) {
        console.error(`개인화된 뉴스 추천 중 오류:`, error);
        return [];
      }
    },

    /**
     * 관심사 기반 뉴스 추천받기
     */
    getInterestBasedNews: async (categories: string[], limit = 8): Promise<NewsSummary[]> => {
      try {
        return await fetchApi<NewsSummary[]>('/recommendation/interests', {
          method: 'POST',
          body: JSON.stringify({ categories, limit }),
        });
      } catch (error) {
        console.error('관심사 기반 뉴스 추천 중 오류:', error);
        return [];
      }
    },

    /**
     * 사용자 상호작용 통계
     */
    getUserStats: async (userId: string, days = 30): Promise<{
      views: number;
      likes: number;
      comments: number;
      shares: number;
      category_distribution: Record<string, number>;
      source_distribution: Record<string, number>;
    }> => {
      try {
        return await fetchApi<{
          views: number;
          likes: number;
          comments: number;
          shares: number;
          category_distribution: Record<string, number>;
          source_distribution: Record<string, number>;
        }>(`/users/stats/${userId}?days=${days}`);
      } catch (error) {
        console.error(`사용자 ${userId}의 상호작용 통계 조회 중 오류:`, error);
        return {
          views: 0,
          likes: 0,
          comments: 0,
          shares: 0,
          category_distribution: {},
          source_distribution: {},
        };
      }
    },

    /**
     * RSS 피드 데이터 가져오기
     */
    getRSSFeeds: async (category?: string): Promise<News[]> => {
      // 백엔드 API 경로는 /api/v1/rss/feeds 입니다
      const endpoint = category ? `/api/v1/rss/feeds?category=${category}` : '/api/v1/rss/feeds';
      try {
        return await fetchApi<News[]>(endpoint);
      } catch (error) {
        console.error('RSS 피드 데이터를 가져오는 중 오류:', error);
        return [];
      }
    },

    /**
     * RSS 크롤링 작업 시작
     */
    startRSSCrawling: async (): Promise<{ message: string }> => {
      try {
        return await fetchApi<{ message: string }>('/crawl', {
          method: 'POST',
        });
      } catch (error) {
        console.error('RSS 크롤링 작업 시작 중 오류:', error);
        return { message: '크롤링 시작 실패' };
      }
    },

    /**
     * 모델 상태 확인
     */
    getModelsStatus: async (): Promise<Record<string, { status: string; type: string }>> => {
      try {
        return await fetchApi<Record<string, { status: string; type: string }>>('/models/status');
      } catch (error) {
        console.error('모델 상태 확인 중 오류:', error);
        return {};
      }
    },

    /**
     * 진단 실행
     */
    runDiagnostics: async (): Promise<{
      mongodb: { status: string; error?: string };
      openai_api: { status: string; error?: string };
      embedding_service: { status: string; error?: string };
      vector_store: { status: string; error?: string };
      overall_status: string;
    }> => {
      try {
        return await fetchApi<{
          mongodb: { status: string; error?: string };
          openai_api: { status: string; error?: string };
          embedding_service: { status: string; error?: string };
          vector_store: { status: string; error?: string };
          overall_status: string;
        }>('/diagnostics');
      } catch (error) {
        console.error('진단 실행 중 오류:', error);
        return {
          mongodb: { status: 'unknown' },
          openai_api: { status: 'unknown' },
          embedding_service: { status: 'unknown' },
          vector_store: { status: 'unknown' },
          overall_status: 'unknown',
        };
      }
    },
  },

  /**
   * 헬스 체크 API
   */
  health: async (): Promise<HealthCheckResponse> => {
    try {
      return await fetchApi<HealthCheckResponse>('/health');
    } catch (error) {
      console.error('헬스 체크 중 오류:', error);
      return { status: 'unhealthy' } as HealthCheckResponse;
    }
  },
};

export interface Comment {
  id: string;
  userId: string;
  userName: string;
  content: string;
  createdAt: string;
  likes: number;
  replies?: Comment[];
}

export interface NewsStats {
  views: number;
  likes: number;
  comments: number;
  shares: number;
}

export interface UserInteraction {
  userId: string;
  newsId: string;
  type: 'view' | 'click' | 'read' | 'like' | 'share' | 'bookmark';
  timestamp: string;
}

export interface UserInteractions {
  userId: string;
  interactions: UserInteraction[];
}

export default apiClient;
