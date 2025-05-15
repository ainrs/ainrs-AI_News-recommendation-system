'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { BadgeInfo, Zap, FolderSearch } from 'lucide-react';
import apiClient from '@/lib/api/client';
import type { NewsSummary } from '@/lib/api/types';

interface RelatedNewsProps {
  newsId: string;
  title?: string;
  limit?: number;
}

export default function RelatedNewsSection({
  newsId,
  title = '관련 뉴스',
  limit = 4
}: RelatedNewsProps) {
  const [relatedNews, setRelatedNews] = useState<NewsSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (newsId) {
      fetchRelatedNews();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [newsId, limit]);

  const fetchRelatedNews = async () => {
    setLoading(true);
    try {
      // 뉴스 데이터를 가져와서 제목과 내용 추출
      const currentNews = await apiClient.news.getById(newsId);

      if (!currentNews) {
        throw new Error('뉴스를 찾을 수 없습니다.');
      }

      // 뉴스 제목과 내용을 query로 사용하여 벡터 검색
      const query = `${currentNews.title} ${currentNews.summary || ''}`;
      const related = await apiClient.ai.searchNewsByVector(query, limit + 1);

      // 현재 뉴스 필터링
      const filtered = related.filter(news => news.id !== newsId).slice(0, limit);

      setRelatedNews(filtered);
    } catch (err) {
      console.error('관련 뉴스를 가져오는 중 오류:', err);
      setError('관련 뉴스를 가져오는 중 오류가 발생했습니다.');
      setRelatedNews([]);
    } finally {
      setLoading(false);
    }
  };

  // 로딩 상태
  if (loading) {
    return (
      <div className="mb-8">
        <h2 className="text-lg font-bold mb-3">{title}</h2>
        <div className="grid grid-cols-2 gap-3">
          {[1, 2, 3, 4].map((id) => (
            <Card key={`related-skeleton-${id}`} className="p-3">
              <Skeleton className="h-24 w-full rounded-sm mb-2" />
              <Skeleton className="h-4 w-3/4 mb-1" />
              <Skeleton className="h-3 w-1/2" />
            </Card>
          ))}
        </div>
      </div>
    );
  }

  // 에러 상태
  if (error) {
    return (
      <div className="mb-8">
        <h2 className="text-lg font-bold mb-3">{title}</h2>
        <Card className="p-4 bg-red-50">
          <p className="text-red-700">{error}</p>
        </Card>
      </div>
    );
  }

  // 관련 뉴스가 없는 경우
  if (relatedNews.length === 0) {
    return (
      <div className="mb-8">
        <h2 className="text-lg font-bold mb-3 flex items-center">
          <FolderSearch className="mr-2 h-5 w-5 text-[hsl(var(--variety-blue))]" />
          {title}
        </h2>
        <Card className="p-4 text-center text-gray-500">
          <p>관련 뉴스가 없습니다.</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="mb-8">
      <h2 className="text-lg font-bold mb-3 flex items-center">
        <Zap className="mr-2 h-5 w-5 text-[hsl(var(--variety-blue))]" />
        {title}
      </h2>
      <div className="grid grid-cols-2 gap-3">
        {relatedNews.map((item) => (
          <Card key={item.id} className="overflow-hidden hover:shadow-md transition-shadow">
            <Link href={`/news/${item.id}`} className="block">
              <div className="h-24 relative">
                {item.image_url ? (
                  <Image
                    src={item.image_url}
                    alt={item.title}
                    fill
                    className="object-cover"
                  />
                ) : (
                  <div className="h-full w-full bg-gray-100 flex items-center justify-center">
                    <BadgeInfo className="h-8 w-8 text-gray-300" />
                  </div>
                )}
              </div>
              <div className="p-3">
                <h3 className="font-medium text-sm line-clamp-2 mb-1">
                  {item.title}
                </h3>
                <div className="flex justify-between text-xs text-gray-500">
                  <span>{item.source}</span>
                  <span>{new Date(item.published_date).toLocaleDateString('ko-KR')}</span>
                </div>
                {item.similarity_score && (
                  <div className="mt-1 text-xs text-blue-600">
                    유사도: {(item.similarity_score * 100).toFixed(0)}%
                  </div>
                )}
              </div>
            </Link>
          </Card>
        ))}
      </div>
    </div>
  );
}
