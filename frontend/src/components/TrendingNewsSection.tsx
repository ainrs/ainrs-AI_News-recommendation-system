'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import apiClient from '@/lib/api/client';

export default function TrendingNewsSection() {
  const [trendingNews, setTrendingNews] = useState<Array<{
    id: string;
    title: string;
    views: number;
    source: string;
  }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 실제 API에서 트렌딩 데이터를 가져옵니다.
  useEffect(() => {
    async function fetchTrendingNews() {
      setLoading(true);
      try {
        // 백엔드 API 호출
        const data = await apiClient.news.getTrending(5);

        // 응답 데이터를 컴포넌트에 맞게 변환
        const formattedData = data.map(item => ({
          id: item.id,
          title: item.title,
          views: Math.floor((item.trust_score || 0) * 1000), // 신뢰도 점수를 조회수로 변환
          source: item.source
        }));

        setTrendingNews(formattedData);
        setError(null);
      } catch (err) {
        console.error('트렌딩 뉴스를 가져오는 중 오류:', err);
        setError('트렌딩 뉴스를 가져오는 중 오류가 발생했습니다');
        setTrendingNews([]);
      } finally {
        setLoading(false);
      }
    }

    fetchTrendingNews();
  }, []);

  if (error) {
    return (
      <section className="mb-8 bg-white p-4 rounded-lg border">
        <h2 className="section-heading">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[hsl(var(--variety-blue))]">
            <path d="M12 2L9 9H2L7 14L5 21L12 17L19 21L17 14L22 9H15L12 2Z" />
          </svg>
          인기 뉴스
        </h2>
        <Alert variant="destructive" className="mt-2">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </section>
    );
  }

  return (
    <section className="mb-8 bg-white p-4 rounded-lg border">
      <h2 className="section-heading">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[hsl(var(--variety-blue))]">
          <path d="M12 2L9 9H2L7 14L5 21L12 17L19 21L17 14L22 9H15L12 2Z" />
        </svg>
        인기 뉴스
      </h2>
      <div className="space-y-4">
        {loading ? (
          // 로딩 상태
          Array.from({ length: 5 }).map((_, i) => (
            <div
              key={`trending-skeleton-${i}`}
              className="flex gap-4 items-center"
            >
              <div className="min-w-8 flex items-center justify-center bg-[hsl(var(--variety-blue))] text-white rounded-full h-8 w-8 font-bold">
                {i + 1}
              </div>
              <div className="flex-1">
                <Skeleton className="h-4 w-full mb-2" />
                <Skeleton className="h-3 w-2/3" />
              </div>
            </div>
          ))
        ) : trendingNews.length > 0 ? (
          // 트렌딩 뉴스
          trendingNews.map((item, index) => (
            <div key={item.id} className="flex gap-4 items-center">
              <div className="min-w-8 flex items-center justify-center bg-[hsl(var(--variety-blue))] text-white rounded-full h-8 w-8 font-bold">
                {index + 1}
              </div>
              <div>
                <h3 className="font-medium line-clamp-2">
                  <Link href={`/news/${item.id}`} className="hover:underline">
                    {item.title}
                  </Link>
                </h3>
                <p className="text-xs text-muted-foreground">
                  {item.source} · 조회수 {item.views.toLocaleString()}
                </p>
              </div>
            </div>
          ))
        ) : (
          <p className="text-center text-gray-500 py-4">표시할 인기 뉴스가 없습니다.</p>
        )}
      </div>
    </section>
  );
}
