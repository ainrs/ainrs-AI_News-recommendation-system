'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { Card, CardContent, CardFooter } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useNews } from '@/lib/hooks/useNews';
import type { NewsForDisplay } from '@/lib/api/newsService';

interface NewsSectionProps {
  title: string;
  category?: string;
  limit?: number;
  view?: 'grid' | 'list';
  showTrending?: boolean;
}

export function NewsSection({
  title,
  category,
  limit = 10,
  view = 'grid',
  showTrending = false,
}: NewsSectionProps) {
  const {
    news,
    loading,
    error,
    fetchLatestNews,
    fetchTrendingNews
  } = useNews({
    limit,
    category,
    autoFetch: false
  });

  useEffect(() => {
    if (showTrending) {
      fetchTrendingNews();
    } else {
      fetchLatestNews();
    }
  }, [showTrending, fetchLatestNews, fetchTrendingNews]);

  // 에러 핸들링
  if (error) {
    return (
      <section className="mb-10">
        <h2 className="section-heading">{title}</h2>
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </section>
    );
  }

  return (
    <section className="mb-10">
      <h2 className="section-heading">{title}</h2>

      {/* 로딩 상태 표시 */}
      {loading ? (
        <div className={`grid grid-cols-1 ${view === 'grid' ? 'md:grid-cols-2' : ''} gap-6`}>
          {/* 고유한 ID를 생성하기 위해 타이틀(공백 제거), 타임스탬프, 인덱스를 조합 */}
          {Array.from({ length: limit }).map((_, index) => (
            <Card
              key={`skeleton-${title.replace(/\s+/g, '-')}-${Date.now()}-${index}`}
              className="news-card"
            >
              <div className="relative h-48">
                <Skeleton className="h-full w-full" />
              </div>
              <CardContent className="p-4">
                <Skeleton className="h-6 w-3/4 mb-2" />
                <Skeleton className="h-4 w-full mb-1" />
                <Skeleton className="h-4 w-full mb-1" />
                <Skeleton className="h-4 w-2/3" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        // 뉴스 데이터 표시
        <div className={`grid grid-cols-1 ${view === 'grid' ? 'md:grid-cols-2' : ''} gap-6`}>
          {news.length > 0 ? (
            news.map((item) => (
              <NewsCard key={item.id || `news-${item.title.replace(/\s+/g, '-')}-${Date.now()}`} news={item} />
            ))
          ) : (
            <div className="w-full text-center py-6">
              <p className="text-muted-foreground mb-2">표시할 뉴스가 없습니다.</p>
              <p className="text-sm text-muted-foreground">
                뉴스 데이터를 불러오는 중입니다... 잠시만 기다려주세요.
              </p>
              <button
                className="mt-4 bg-[hsl(var(--variety-blue))] text-white px-4 py-2 rounded-md text-sm"
                onClick={() => showTrending ? fetchTrendingNews() : fetchLatestNews()}
              >
                새로고침
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// 뉴스 카드 컴포넌트
interface NewsCardProps {
  news: NewsForDisplay;
}

function NewsCard({ news }: NewsCardProps) {
  return (
    <Card className={`news-card ${news.aiEnhanced ? 'border-[hsl(var(--variety-blue))] border-opacity-60' : ''}`}>
      {news.imageUrl && (
        <div className="relative h-48">
          <Image
            src={news.imageUrl || 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAZAAAADICAMAAAD2ShmzAAAAM1BMVEX////CwsL5+fnV1dXq6ur19fXg4OC8vLzT09Pt7e3Hx8fv7+/d3d3h4eHQ0NCwsLD///+ck8V3AAAACXBIWXMAAAsTAAALEwEAmpwYAAAD90lEQVR4nO3di5KjIBCFYQREvEDf/2UX0E2ceGlAiQy6/1fTtZVJ1SQndjtBr7IcZ7TqfnAZHhODu1cP/92V0tpqEz6BePgzcb/+Qb01hSK9VQeQKU6e0iJ6VXpRfFcfoAlbRZoiCCKEAEIIIIQAQggghABCCCCEAEIIBYUwU0kGsZoG8k4yiNPf1f9bvWQQ70zpSnnBILZcnhTLBbGutBDLfXbFBmF/CJQMwiXtsiDcrLJXJYNYZkpCsQghgBACCCGAEAIIIYAQQgEhk9UVMGhMMVQ3qGsZbZ+HGqY53jJp90Nouo2HUL2O/6pqpjmGQx6R9PlbY8+GUJ0+GTTHJdIhVGfOhFCdP7OT6qYTi6NvRULcR3UkBnVbXOUexFd2LkTVdjnRV3ZqIGbLXnp2Jb5T8dwcPrM5F8It/Ft48yrR3HbVHQ+hvlqfFwihL5cA4SCr1J0B8UWnPTKhvtfAu9ZQCB2sU85rCcyH0Nl65GQIXaj+T4doCtL4jAL3hWzpkahZXLsxO2tRFoIyIKV6ZDaEZmwDQlUHQVyhQkNo3g4gtPCDNkdVIJdDXJt0Y5xXcmMOyjXIpZNIGj3mZQgVPd4IQttaCqG1zfI1EFoNGc6HUNnD8URIYJ8QYzAiFMStzZGlENrYvhLSl2t20qUQYm1hq+wVh0Jo4UgIre6PQ6jocYi+XGXXJZdBaN2i4iFUdkVSPy7axrIglHdZXz/OwpW3UrMg3aYP+6HdTjdX8g/SPU6hgx32P4imbKF0z0txA+bZ0e3FNuX3LtfucWhbkofVU+DhXPe4FN4vQcfz2e4JH1DQ5zt8KftFuSDgk6Ou/AxoG/HZ7Mu1ouD5N2f/rLYxe1DGCDxj6ux7yjdC5P1S4Dlt5y2TvTIQRzV7XuDZiVcfUCJ4q8qXy2EJ3yrK5aA7e6/MhfAfQxcAoYc4UWflw0BFNKcdJPjZJQgBhBBACAGEEEAIAYQQQAgBhBBACAGEEEAIAYQQQAgBhBBACAGEEEAIAYQQQAgBhBBACAGEEEAIAYQQQAgBhBAWA8K9MlwI9ynhXqQsCOcXEWw3JQvCPRdcFMkgzEfJZZEMwv1g+EqJZBDuUcN+jgWDcL8h7rkkGYR7V3FPMO5lxEUSCXGPRuoNx0USCfd65d6zDIj+Moj+Moj+Moj+Moj+Moj++vMQ8tRCf/1lEP31l0H0FzV7YV9sMQ1Wf1Gz4QDC3XaYF1tUfGISrT91EUQI/WUQ/WUQ/WUQ/WUQ/UXNIJjfGYR5xUa0+NQZ1g8lzSCkGQT7uZ14Nd8QJt5fJIjDiqIAAAAASUVORK5CYII='}
            alt={news.title}
            fill
            className="object-cover"
          />
          {news.aiEnhanced && (
            <div className="absolute top-2 right-2 bg-[hsl(var(--variety-blue))] text-white px-2 py-1 rounded-md text-xs font-medium z-10">
              AI 강화
            </div>
          )}
        </div>
      )}
      <CardContent className="p-4">
        <div className="mb-2 flex flex-wrap">
          {news.categories && news.categories.map((category, index) => (
            <span
              key={`${news.id || 'news'}-${category}-${index}`}
              className="text-sm text-[hsl(var(--variety-blue))] mr-2"
            >
              {category}
            </span>
          ))}
          {!news.imageUrl && news.aiEnhanced && (
            <span className="text-xs font-medium bg-[hsl(var(--variety-blue))] text-white px-2 py-0.5 rounded-md">
              AI 강화
            </span>
          )}
        </div>
        <h3 className="news-title mb-2">
          <Link href={`/news/${news.id}`} className="hover:underline">
            {news.title}
          </Link>
        </h3>
        <p className="news-summary">
          {news.summary || `${news.content.substring(0, 150)}...`}
        </p>
        {news.aiEnhanced && news.trustScore > 0 && (
          <div className="mt-2 flex items-center">
            <div className="w-full bg-gray-200 rounded-full h-1.5">
              <div
                className="bg-[hsl(var(--variety-blue))] h-1.5 rounded-full"
                style={{ width: `${news.trustScore * 100}%` }}
              ></div>
            </div>
            <span className="text-xs ml-2 text-gray-600">신뢰도</span>
          </div>
        )}
      </CardContent>
      <CardFooter className="p-4 pt-0 flex justify-between items-center">
        <p className="text-xs text-muted-foreground">{news.publishedDate}</p>
        <p className="text-xs font-medium">{news.source}</p>
      </CardFooter>
    </Card>
  );
}

export default NewsSection;
