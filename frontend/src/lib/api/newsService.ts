import { apiClient } from './client';
import { type News, type NewsSummary, NewsSearchQuery } from './types';

/**
 * 뉴스 서비스
 * 뉴스 데이터를 가져오고 처리하는 기능을 제공합니다.
 */
export const newsService = {
  /**
   * 최신 뉴스 목록을 가져옵니다.
   */
  getLatestNews: async (limit = 20): Promise<News[]> => {
    try {
      return await apiClient.news.getAll({ limit });
    } catch (error) {
      console.error('최신 뉴스를 가져오는 중 오류 발생:', error);
      return [];
    }
  },

  /**
   * 카테고리별 뉴스를 가져옵니다.
   */
  getNewsByCategory: async (category: string, limit = 10): Promise<News[]> => {
    try {
      return await apiClient.news.getAll({ category, limit });
    } catch (error) {
      console.error(`${category} 카테고리 뉴스를 가져오는 중 오류 발생:`, error);
      return [];
    }
  },

  /**
   * 트렌딩 뉴스를 가져옵니다.
   */
  getTrendingNews: async (limit = 10): Promise<NewsSummary[]> => {
    try {
      return await apiClient.news.getTrending(limit);
    } catch (error) {
      console.error('트렌딩 뉴스를 가져오는 중 오류 발생:', error);
      return [];
    }
  },

  /**
   * 콜드 스타트 추천 뉴스를 가져옵니다.
   * 사용자 정보가 없거나 새로운 사용자를 위한 추천입니다.
   */
  getColdStartRecommendations: async (limit = 5): Promise<NewsSummary[]> => {
    try {
      // 콜드 스타트 추천 API 호출
      return await apiClient.news.getColdStartRecommendations(limit);
    } catch (error) {
      console.error('콜드 스타트 추천을 가져오는 중 오류 발생:', error);
      // 실패 시 트렌딩 뉴스로 대체
      return await newsService.getTrendingNews(limit);
    }
  },

  /**
   * 특정 뉴스를 ID로 가져옵니다.
   */
  getNewsById: async (id: string): Promise<News | null> => {
    try {
      return await apiClient.news.getById(id);
    } catch (error) {
      console.error(`뉴스 ID ${id}를 가져오는 중 오류 발생:`, error);
      return null;
    }
  },

  /**
   * 키워드로 뉴스를 검색합니다.
   */
  searchNews: async (keyword: string, limit = 20): Promise<News[]> => {
    try {
      return await apiClient.news.searchByKeyword(keyword, limit);
    } catch (error) {
      console.error(`'${keyword}' 키워드로 뉴스를 검색하는 중 오류 발생:`, error);
      return [];
    }
  },

  /**
   * 사용자 맞춤 추천 뉴스를 가져옵니다.
   */
  getRecommendedNews: async (userId: string, limit = 10): Promise<NewsSummary[]> => {
    try {
      return await apiClient.users.getRecommendations(userId, limit);
    } catch (error) {
      console.error(`사용자 ${userId}의 추천 뉴스를 가져오는 중 오류 발생:`, error);
      return [];
    }
  },

  /**
   * 뉴스와의 상호작용을 기록합니다.
   */
  recordInteraction: async (
    userId: string,
    newsId: string,
    interactionType: 'view' | 'click' | 'read' | 'like' | 'share'
  ): Promise<boolean> => {
    try {
      await apiClient.users.recordInteraction(userId, newsId, interactionType);
      return true;
    } catch (error) {
      console.error('뉴스 상호작용을 기록하는 중 오류 발생:', error);
      return false;
    }
  },

  /**
   * 뉴스 데이터를 프론트엔드 표시용으로 변환합니다.
   */
  formatNewsForDisplay: (news: News): NewsForDisplay => {
    // 디버깅용: 뉴스 원본 데이터 구조 확인
    console.log('뉴스 원본 데이터:', {
      id: news._id || news.id,
      hasContent: !!news.content,
      contentLength: news.content?.length,
      hasSummary: !!news.summary,
      summaryLength: news.summary?.length,
      hasImageUrl: !!news.image_url,
      imageUrl: news.image_url
    });

    return {
      id: news._id || news.id || `news-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      title: news.title,
      content: news.content || '',
      summary: news.summary || '',
      source: news.source,
      publishedDate: new Date(news.published_date).toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      }),
      author: news.author || '',
      imageUrl: news.image_url || '',
      categories: news.categories || [],
      url: news.url || '',
      trustScore: news.trust_score || 0,
      sentimentScore: news.sentiment_score || 0,
      aiEnhanced: news.ai_enhanced || false, // AI 향상 여부
      // 원본 데이터 유지
      _originalData: news
    };
  },
};

// 프론트엔드 표시용 뉴스 타입
export interface NewsForDisplay {
  id: string;
  title: string;
  content: string;
  summary: string;
  source: string;
  publishedDate: string;
  author: string;
  imageUrl: string;
  categories: string[];
  url: string;
  trustScore: number;
  sentimentScore: number;
  aiEnhanced: boolean; // AI 강화 여부
  _originalData?: any; // 원본 데이터 보존 (디버깅용)
}

export default newsService;
