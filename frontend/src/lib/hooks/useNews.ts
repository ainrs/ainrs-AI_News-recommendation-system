'use client';

import { useState, useEffect, useCallback } from 'react';
import { type News, NewsSummary } from '../api/types';
import newsService, { type NewsForDisplay } from '../api/newsService';
import apiClient from '../api/client';

interface UseNewsOptions {
  limit?: number;
  category?: string;
  autoFetch?: boolean;
}

/**
 * 뉴스 데이터를 가져오는 훅
 */
export function useNews(options: UseNewsOptions = {}) {
  const { limit = 20, category, autoFetch = true } = options;

  const [news, setNews] = useState<NewsForDisplay[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // 최신 뉴스 가져오기
  const fetchLatestNews = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      let newsData: News[] = [];

      if (category) {
        console.log(`${category} 카테고리 뉴스를 가져오는 중...`);
        newsData = await newsService.getNewsByCategory(category, limit);
      } else {
        console.log('최신 뉴스를 가져오는 중...');
        newsData = await newsService.getLatestNews(limit);
      }

      console.log('뉴스 데이터 로드 성공:', newsData.length);
      const formattedNews = newsData.map(newsService.formatNewsForDisplay);
      setNews(formattedNews);
    } catch (err) {
      console.error('뉴스 데이터 로드 실패:', err);
      const errMsg = category
        ? `${category} 카테고리 뉴스를 가져오는 중 오류가 발생했습니다. 백엔드 서버 연결을 확인해주세요.`
        : '뉴스를 가져오는 중 오류가 발생했습니다. 백엔드 서버 연결을 확인해주세요.';
      setError(errMsg);
      // 오류 발생 시 빈 배열 설정
      setNews([]);
    } finally {
      setLoading(false);
    }
  }, [category, limit]);

  // 트렌딩 뉴스 가져오기
  const fetchTrendingNews = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      console.log('트렌딩 뉴스를 가져오는 중...');
      const trendingNews = await newsService.getTrendingNews(limit);
      console.log('트렌딩 뉴스 로드 성공:', trendingNews.length);

      // NewsSummary를 NewsForDisplay로 변환 (타입 호환을 위한 간단한 변환)
      const formattedNews = trendingNews.map(item => ({
        id: item.id,
        title: item.title,
        content: '', // NewsSummary에는 전체 content가 없음
        summary: item.summary || '',
        source: item.source,
        publishedDate: new Date(item.published_date).toLocaleDateString('ko-KR', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
        }),
        author: '',
        imageUrl: item.image_url || '',
        categories: item.categories,
        url: '', // NewsSummary에는 URL이 없을 수 있음
        trustScore: item.trust_score || 0,
        sentimentScore: item.sentiment_score || 0,
      }));

      setNews(formattedNews);
    } catch (err) {
      console.error('트렌딩 뉴스 로드 실패:', err);
      setError('트렌딩 뉴스를 가져오는 중 오류가 발생했습니다. 백엔드 서버 연결을 확인해주세요.');
      // 오류 발생 시 빈 배열 설정
      setNews([]);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  // 키워드로 뉴스 검색
  const searchNews = useCallback(async (keyword: string) => {
    if (!keyword.trim()) return;

    setLoading(true);
    setError(null);

    try {
      console.log(`"${keyword}" 키워드로 뉴스 검색 중...`);
      const searchResults = await newsService.searchNews(keyword, limit);
      console.log('검색 결과 로드 성공:', searchResults.length);

      const formattedNews = searchResults.map(newsService.formatNewsForDisplay);
      setNews(formattedNews);
    } catch (err) {
      console.error('뉴스 검색 실패:', err);
      setError('뉴스 검색 중 오류가 발생했습니다');
      // 오류 발생 시 빈 배열 설정
      setNews([]);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  // ID로 특정 뉴스 가져오기
  const fetchNewsById = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);

    try {
      console.log(`ID ${id}로 뉴스 조회 중...`);
      const newsItem = await newsService.getNewsById(id);

      if (newsItem) {
        console.log('뉴스 조회 성공:', newsItem.title);
        const formattedNews = newsService.formatNewsForDisplay(newsItem);
        setNews([formattedNews]);
      } else {
        console.error(`ID ${id}에 해당하는 뉴스가 없습니다`);
        setError('뉴스를 찾을 수 없습니다');
        setNews([]);
      }
    } catch (err) {
      console.error(`ID ${id} 뉴스 조회 실패:`, err);
      setError('뉴스를 가져오는 중 오류가 발생했습니다');
      setNews([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // 사용자 맞춤 추천 뉴스 가져오기
  const fetchRecommendedNews = useCallback(async (userId: string) => {
    setLoading(true);
    setError(null);

    try {
      console.log(`사용자 ${userId}의 추천 뉴스를 가져오는 중...`);
      const recommendations = await newsService.getRecommendedNews(userId, limit);
      console.log('추천 뉴스 로드 성공:', recommendations.length);

      // NewsSummary를 NewsForDisplay로 변환
      const formattedNews = recommendations.map(item => ({
        id: item.id,
        title: item.title,
        content: '', // 추천에는 전체 content가 없음
        summary: item.summary || '',
        source: item.source,
        publishedDate: new Date(item.published_date).toLocaleDateString('ko-KR', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
        }),
        author: '',
        imageUrl: item.image_url || '',
        categories: item.categories,
        url: '',
        trustScore: item.trust_score || 0,
        sentimentScore: item.sentiment_score || 0,
      }));

      setNews(formattedNews);
    } catch (err) {
      console.error('추천 뉴스 로드 실패:', err);
      setError('추천 뉴스를 가져오는 중 오류가 발생했습니다');
      // 오류 발생 시 빈 배열 설정
      setNews([]);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  // 뉴스 상호작용 기록
  const recordNewsInteraction = useCallback(async (
    userId: string,
    newsId: string,
    interactionType: 'view' | 'click' | 'read' | 'like' | 'share'
  ) => {
    try {
      console.log(`사용자 ${userId}의 뉴스 ${newsId} ${interactionType} 상호작용 기록 중...`);
      const result = await newsService.recordInteraction(userId, newsId, interactionType);
      console.log('상호작용 기록 완료');
      return result;
    } catch (err) {
      console.error('뉴스 상호작용 기록 실패:', err);
      return false;
    }
  }, []);

  // 컴포넌트 마운트 시 자동 데이터 가져오기
  useEffect(() => {
    if (autoFetch) {
      fetchLatestNews();
    }
  }, [autoFetch, fetchLatestNews]);

  return {
    news,
    loading,
    error,
    fetchLatestNews,
    fetchTrendingNews,
    searchNews,
    fetchNewsById,
    fetchRecommendedNews,
    recordNewsInteraction,
  };
}

export default useNews;
