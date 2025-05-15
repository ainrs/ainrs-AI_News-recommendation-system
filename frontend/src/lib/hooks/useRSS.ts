'use client';

import { useState, useEffect, useCallback } from 'react';
import type { News } from '../api/types';
import rssService from '../api/rssService';
import type { NewsForDisplay } from '../api/newsService';

interface UseRSSOptions {
  category?: string;
  limit?: number;
  autoFetch?: boolean;
}

/**
 * RSS 데이터를 가져오는 훅
 */
export function useRSS(options: UseRSSOptions = {}) {
  const { category, limit = 20, autoFetch = true } = options;

  const [news, setNews] = useState<NewsForDisplay[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // RSS 뉴스 가져오기
  const fetchRSSNews = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // RSS 데이터 가져오기
      const rssNews = await rssService.fetchRSSNews(category);

      // 결과를 제한
      const limitedNews = rssNews.slice(0, limit);

      // NewsForDisplay 형식으로 변환
      const formattedNews = limitedNews.map(item => ({
        id: item._id,
        title: item.title,
        content: item.content,
        summary: item.summary || '',
        source: item.source,
        publishedDate: new Date(item.published_date).toLocaleDateString('ko-KR', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
        }),
        author: item.author || '',
        imageUrl: item.image_url || '',
        categories: item.categories,
        url: item.url,
        trustScore: 0,
        sentimentScore: 0,
      }));

      setNews(formattedNews);
    } catch (err) {
      setError('RSS 뉴스를 가져오는 중 오류가 발생했습니다.');
      console.error('RSS 데이터를 가져오는 중 오류:', err);
    } finally {
      setLoading(false);
    }
  }, [category, limit]);

  useEffect(() => {
    if (autoFetch) {
      fetchRSSNews();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoFetch, fetchRSSNews]);

  return {
    news,
    loading,
    error,
    fetchRSSNews,
  };
}

export default useRSS;
