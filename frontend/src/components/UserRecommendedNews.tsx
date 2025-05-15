'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { apiClient } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/authContext';

interface NewsItem {
  id: string;
  title: string;
  source: string;
  published_date: string;
  image_url?: string;
}

export default function UserRecommendedNews() {
  const { user, isAuthenticated } = useAuth();
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchRecommendedNews() {
      if (!isAuthenticated || !user) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        // 사용자 ID를 기반으로 협업 필터링 + 개인화된 추천
        console.log("개인화된 추천 요청 - 사용자 ID:", user.id);
        const recommendedNews = await apiClient.ai.getPersonalizedNews(user.id);
        console.log("받은 추천 데이터:", recommendedNews);
        setNews(recommendedNews);
        setError(null);
      } catch (err) {
        console.error('개인화된 뉴스를 가져오는 중 오류:', err);
        setError('뉴스를 불러오는 중 오류가 발생했습니다.');
      } finally {
        setLoading(false);
      }
    }

    fetchRecommendedNews();
  }, [user, isAuthenticated]);

  if (!isAuthenticated || !user) {
    return null;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">맞춤 추천 뉴스</h2>
      <p className="text-sm text-muted-foreground mb-4">
        회원님의 관심사와 활동 내역을 기반으로 AI가 추천한 뉴스입니다
      </p>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(4)].map((_, index) => (
            <Card key={index}>
              <div className="space-y-3">
                <Skeleton className="h-32 w-full" />
                <div className="p-4">
                  <Skeleton className="h-4 w-full mb-2" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : error ? (
        <div className="p-4 text-center text-red-500 bg-red-50 rounded-md">
          {error}
        </div>
      ) : news.length === 0 ? (
        <div className="p-4 text-center text-muted-foreground bg-muted rounded-md">
          아직 맞춤 추천할 뉴스가 없습니다. 더 많은 뉴스를 읽고 상호작용해 보세요.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {news.map((item) => (
            <Card key={item.id} className="overflow-hidden hover:shadow-md transition-shadow">
              <Link href={`/news/${item.id}`}>
                <div className="h-40 relative">
                  {item.image_url ? (
                    <Image
                      src={item.image_url}
                      alt={item.title}
                      fill
                      className="object-cover"
                    />
                  ) : (
                    <div className="h-full w-full bg-gray-100 flex items-center justify-center">
                      <span className="text-gray-400">이미지 없음</span>
                    </div>
                  )}
                </div>
                <CardContent className="p-4">
                  <h3 className="font-semibold line-clamp-2 mb-2">{item.title}</h3>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>{item.source}</span>
                    <span>{new Date(item.published_date).toLocaleDateString('ko-KR')}</span>
                  </div>
                </CardContent>
              </Link>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
