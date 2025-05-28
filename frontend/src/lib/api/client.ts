/**
 * API 클라이언트
 * 백엔드 API와 통신하기 위한 유틸리티 함수들을 제공합니다.
 */

import { type News, type NewsSummary, NewsSearchQuery, type HealthCheckResponse } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
const API_TIMEOUT = 30000; // 30초 타임아웃 (AI 분석 작업을 위해 시간 연장)

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

    // 타임아웃이 있는 fetch 구현
    const fetchWithTimeout = async (resource: string, options: RequestInit, timeout: number) => {
      const controller = new AbortController();
      const id = setTimeout(() => controller.abort(), timeout);

      try {
        const response = await fetch(resource, {
          ...options,
          signal: controller.signal
        });
        clearTimeout(id);
        return response;
      } catch (error) {
        clearTimeout(id);
        throw error;
      }
    };

    const response = await fetchWithTimeout(url, config, API_TIMEOUT);

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
      if (error.name === 'AbortError') {
        console.error(`❌ API 요청 실패(타임아웃): ${options.method || 'GET'} ${url} - 요청이 시간 초과로 중단되었습니다.`);
        throw new Error('API 요청 실패: 요청이 시간 초과로 중단되었습니다.');
      }
      console.error(`❌ API 요청 실패: ${options.method || 'GET'} ${url} - ${error.message}`);
      throw new Error(`API 요청 실패: ${error.message}`);
    } else {
      console.error(`❌ API 요청 실패: ${options.method || 'GET'} ${url} - 알 수 없는 오류`);
      throw new Error('API 요청 중 알 수 없는 오류가 발생했습니다');
    }
  }
}

/**
 * 자동 재시도 기능이 있는 API 요청 함수
 * 백엔드 서버가 시작 중이거나 일시적으로 연결할 수 없는 경우에 유용
 */
async function fetchApiWithRetry<T = unknown>(
  endpoint: string,
  options: RequestInit = {},
  maxRetries = 2,
  retryDelay = 1000
): Promise<T> {
  let lastError: Error | null = null;

  // 재시도 횟수만큼 반복
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      // 첫 시도가 아니면 잠시 대기 (재시도마다 대기 시간 증가)
      if (attempt > 0) {
        const currentDelay = retryDelay * attempt; // 점점 더 오래 기다림
        console.log(`🔄 API 요청 재시도 ${attempt}/${maxRetries}: ${endpoint}, ${currentDelay}ms 대기 후 시도`);
        await new Promise(resolve => setTimeout(resolve, currentDelay));
      }

      // API 호출 시도
      return await fetchApi<T>(endpoint, options);
    } catch (error) {
      // 오류 저장
      lastError = error instanceof Error ? error : new Error('알 수 없는 오류');

      // 타임아웃이 빨리 발생하도록 하고, 빠르게 실패를 반환합니다
      if (attempt >= maxRetries) {
        // 최대 재시도 횟수 도달 시
        console.error(`⚠️ API 요청 최대 재시도 횟수(${maxRetries}) 도달: ${endpoint}`);
        break;
      }
    }
  }

  // 모든 시도 실패 시
  throw lastError;
}

/**
 * 백엔드 서버 연결 상태 확인
 * 연결 가능 여부와 기본 상태를 반환합니다.
 */
export const checkBackendConnection = async (): Promise<{
  connected: boolean;
  status?: string;
  message?: string;
}> => {
  try {
    // 타임아웃이 짧은 빠른 헬스체크
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const response = await fetch(`${API_BASE_URL}/api/v1/health`, {
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (response.ok) {
      const data = await response.json();
      return {
        connected: true,
        status: data.status,
        message: '백엔드 서버에 연결되었습니다.'
      };
    } else {
      return {
        connected: false,
        status: 'error',
        message: `백엔드 서버 응답 오류: ${response.status} ${response.statusText}`
      };
    }
  } catch (error) {
    // 연결 실패
    return {
      connected: false,
      status: 'disconnected',
      message: '백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.'
    };
  }
};

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
        }>('/api/v1/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: formData.toString(),
        });
        return response;
      } catch (error) {
        if (error instanceof Error) {
          throw new Error(`로그인 중 오류: ${error.message}`);
        }
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
        }>('/api/v1/api/auth/register', {
          method: 'POST',
          body: JSON.stringify({
            username,
            email,
            password,
          }),
        });
      } catch (error) {
        if (error instanceof Error) {
          throw new Error(`회원가입 중 오류: ${error.message}`);
        }
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
        }>('/api/v1/api/email/send-verification-code', {
          method: 'POST',
          body: JSON.stringify({ email }),
        });
      } catch (error) {
        if (error instanceof Error) {
          throw new Error(`인증 코드 요청 중 오류: ${error.message}`);
        }
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
        }>('/api/v1/api/email/verify-code', {
          method: 'POST',
          body: JSON.stringify({ email, code }),
        });
      } catch (error) {
        if (error instanceof Error) {
          throw new Error(`인증 코드 확인 중 오류: ${error.message}`);
        }
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
        // 재시도 로직 사용 (최대 3번, 2초 간격)
        return await fetchApiWithRetry<News[]>(`/api/v1/news?${query}`, {}, 3, 2000);
      } catch (error) {
        if (error instanceof Error) {
          throw new Error(`뉴스 목록을 가져오는 중 오류: ${error.message}`);
        }
        throw error;
      }
    },

    /**
     * 특정 ID의 뉴스 가져오기
     */
    getById: async (id: string): Promise<News> => {
      try {
        return await fetchApi<News>(`/api/v1/news/${id}`);
      } catch (error) {
        if (error instanceof Error) {
          throw new Error(`ID ${id}의 뉴스를 가져오는 중 오류: ${error.message}`);
        }
        throw error;
      }
    },

    /**
     * 뉴스 검색
     */
    search: async (query: string): Promise<News[]> => {
      try {
        return await fetchApi<News[]>('/api/v1/news/search', {
          method: 'POST',
          body: JSON.stringify({ query }),
        });
      } catch (error) {
        if (error instanceof Error) {
          throw new Error(`뉴스 검색 중 오류: ${error.message}`);
        }
        throw error;
      }
    },

    /**
     * 트렌딩 뉴스 가져오기 (자동 재시도 포함)
     */
    getTrending: async (limit = 10): Promise<NewsSummary[]> => {
      try {
        // 재시도 로직 사용 (최대 3번, 2초 간격)
        return await fetchApiWithRetry<NewsSummary[]>(`/api/v1/recommendation/trending?limit=${limit}`, {}, 3, 2000);
      } catch (error) {
        if (error instanceof Error) {
          throw new Error(`트렌딩 뉴스를 가져오는 중 오류: ${error.message}`);
        }
        throw error;
      }
    },

    /**
     * 콜드 스타트 추천 뉴스 가져오기 (자동 재시도 포함)
     * 사용자 데이터나 상호작용이 없을 때도 다양한 뉴스를 추천
     */
    getColdStartRecommendations: async (limit = 5): Promise<NewsSummary[]> => {
      try {
        // 재시도 로직 사용 (최대 3번, 2초 간격)
        return await fetchApiWithRetry<NewsSummary[]>(`/api/v1/news/cold-start?limit=${limit}`, {}, 3, 2000);
      } catch (error) {
        // 오류 시 트렌딩 뉴스로 폴백
        return await apiClient.news.getTrending(limit);
      }
    },

    /**
     * 키워드 기반 뉴스 검색
     */
    searchByKeyword: async (keyword: string, limit = 20): Promise<News[]> => {
      try {
        return await fetchApi<News[]>('/api/v1/news/search', {
          method: 'POST',
          body: JSON.stringify({ query: keyword, limit }),
        });
      } catch (error) {
        if (error instanceof Error) {
          throw new Error(`키워드 '${keyword}'로 뉴스를 검색하는 중 오류: ${error.message}`);
        }
        throw error;
      }
    },

    /**
     * 뉴스 댓글 가져오기
     */
    getComments: async (newsId: string): Promise<Comment[]> => {
      try {
        return await fetchApi<Comment[]>(`/api/v1/news/${newsId}/comments`);
      } catch (error) {
        if (error instanceof Error) {
          throw new Error(`뉴스 ${newsId}의 댓글을 가져오는 중 오류: ${error.message}`);
        }
        throw error;
      }
    },

    /**
     * 뉴스 댓글 작성
     */
    addComment: async (newsId: string, userId: string, content: string): Promise<Comment> => {
      try {
        return await fetchApi<Comment>(`/api/v1/news/${newsId}/comments`, {
          method: 'POST',
          body: JSON.stringify({
            user_id: userId,
            content,
          }),
        });
      } catch (error) {
        if (error instanceof Error) {
          throw new Error(`뉴스 ${newsId}에 댓글을 작성하는 중 오류: ${error.message}`);
        }
        throw error;
      }
    },

    /**
     * 뉴스 통계 가져오기
     */
    getStats: async (newsId: string): Promise<NewsStats> => {
      try {
        return await fetchApi<NewsStats>(`/api/v1/news/${newsId}/stats`);
      } catch (error) {
        return { views: 0, likes: 0, comments: 0, shares: 0 };
      }
    },

    /**
     * 뉴스 북마크 설정/해제
     */
    toggleBookmark: async (newsId: string, userId: string, bookmarked: boolean): Promise<{ success: boolean }> => {
      try {
        return await fetchApi<{ success: boolean }>(`/api/v1/news/${newsId}/bookmark`, {
          method: 'POST',
          body: JSON.stringify({
            user_id: userId,
            bookmarked,
          }),
        });
      } catch (error) {
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
        return await fetchApi<NewsSummary[]>(`/api/v1/recommendations/${userId}?limit=${limit}`);
      } catch (error) {
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
        return await fetchApi<{ message: string }>('/api/v1/interaction', {
          method: 'POST',
          body: JSON.stringify({
            user_id: userId,
            news_id: newsId,
            interaction_type: interactionType,
          }),
        });
      } catch (error) {
        return { message: '상호작용 기록 실패' };
      }
    },

    /**
     * 사용자 상호작용 이력 가져오기
     */
    getUserInteractions: async (userId: string, newsId?: string): Promise<UserInteractions> => {
      const endpoint = newsId
        ? `/api/v1/user-interactions?userId=${userId}&newsId=${newsId}`
        : `/api/v1/user-interactions?userId=${userId}`;
      try {
        return await fetchApi<UserInteractions>(endpoint);
      } catch (error) {
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
        const res = await fetchApi<{ embedding: number[] }>('/api/v1/text/embeddings', {
          method: 'POST',
          body: JSON.stringify({ text }),
        });
        return res.embedding;
      } catch (error) {
        return [];
      }
    },

    /**
     * 뉴스 벡터 검색
     */
    searchNewsByVector: async (query: string, limit = 10): Promise<NewsSummary[]> => {
      try {
        return await fetchApi<NewsSummary[]>(`/api/v1/rag/search?query=${encodeURIComponent(query)}&limit=${limit}`);
      } catch (error) {
        return [];
      }
    },

    /**
     * 뉴스에 대해 질문하기
     */
    askQuestionAboutNews: async (newsId: string, question: string): Promise<{ answer: string }> => {
      try {
        return await fetchApi<{ answer: string }>(`/api/v1/news/${newsId}/ask`, {
          method: 'POST',
          body: JSON.stringify({ question }),
        });
      } catch (error) {
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
        // ObjectId 형식 문제를 피하기 위해 백엔드에서 문자열 ID도 받을 수 있도록 수정됐다고 가정합니다
        // 오류 방지를 위해 news 뿐만 아니라 AI 분석 경로도 확인
        // news ID 검증을 추가하여 올바른 형식만 요청
        if (!newsId || typeof newsId !== 'string' || newsId.length < 5) {
          throw new Error("유효하지 않은 뉴스 ID");
        }

        return await fetchApi<{
          news_id: string;
          trust_score: number;
          trust_factors: Record<string, number>;
        }>(`/api/v1/news/${newsId}/trust-analysis`, {
          method: 'POST',
        });
      } catch (error) {
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
        }>(`/api/v1/news/${newsId}/sentiment-analysis`, {
          method: 'POST',
        });
      } catch (error) {
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
        }>(`/api/v1/news/${newsId}/key-phrases?limit=${limit}`, {
          method: 'POST',
        });
      } catch (error) {
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
        }>(`/api/v1/news/${newsId}/summarize?max_length=${max_length}`, {
          method: 'POST',
        });
      } catch (error) {
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
        return await fetchApi<NewsSummary[]>(`/api/v1/collaborative-filtering/recommendations/${userId}?limit=${limit}`);
      } catch (error) {
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
        }>(`/api/v1/collaborative-filtering/similar-users/${userId}?limit=${limit}`);
      } catch (error) {
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
        return await fetchApi<NewsSummary[]>(`/api/v1/recommendation/personalized/${userId}?limit=${limit}`);
      } catch (error) {
        return [];
      }
    },

    /**
     * 관심사 기반 뉴스 추천받기
     */
    getInterestBasedNews: async (categories: string[], limit = 8): Promise<NewsSummary[]> => {
      try {
        return await fetchApi<NewsSummary[]>('/api/v1/recommendation/interests', {
          method: 'POST',
          body: JSON.stringify({ categories, limit }),
        });
      } catch (error) {
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
        }>(`/api/v1/users/stats/${userId}?days=${days}`);
      } catch (error) {
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
        return [];
      }
    },

    /**
     * RSS 크롤링 작업 시작
     */
    startRSSCrawling: async (): Promise<{ message: string }> => {
      try {
        return await fetchApi<{ message: string }>('/api/v1/crawl', {
          method: 'POST',
        });
      } catch (error) {
        return { message: '크롤링 시작 실패' };
      }
    },

    /**
     * 모델 상태 확인
     */
    getModelsStatus: async (): Promise<Record<string, { status: string; type: string }>> => {
      try {
        return await fetchApi<Record<string, { status: string; type: string }>>('/api/v1/models/status');
      } catch (error) {
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
        }>('/api/v1/diagnostics');
      } catch (error) {
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
      return await fetchApi<HealthCheckResponse>('/api/v1/health');
    } catch (error) {
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
