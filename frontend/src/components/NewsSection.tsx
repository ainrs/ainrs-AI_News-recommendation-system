'use client';

import { useState, useEffect } from 'react';

// 유효하지 않은 이미지를 확인하는 함수
function isInvalidImage(url: string): boolean {
  if (!url) return true;

  // 유효하지 않은 이미지 패턴 목록
  const invalidPatterns = [
    'audio_play',
    '.svg',
    'static/media',
    'icon',
    'logo',
    'button'
  ];

  // 조선일보 이미지 리사이저 URL은 유효함 (예외 처리)
  if (url.includes('chosun.com/resizer') && (url.includes('.jpg') || url.includes('.png') || url.includes('.jpeg'))) {
    console.log('조선일보 이미지 URL 예외 허용:', url);
    return false;
  }

  // 패턴 매칭
  return invalidPatterns.some(pattern => url.toLowerCase().includes(pattern));
}
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
          <AlertDescription>
            {error}
            <button
              onClick={() => showTrending ? fetchTrendingNews() : fetchLatestNews()}
              className="ml-2 text-sm underline text-blue-600 hover:text-blue-800"
            >
              다시 시도
            </button>
          </AlertDescription>
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
              <NewsCard
                key={item.id || `news-${item.title.replace(/\s+/g, '-')}-${Date.now()}`}
                news={{
                  ...item,
                  id: item.id || item._id || `news-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
                }}
              />
            ))
          ) : (
            <div className="w-full text-center py-6">
              <p className="text-muted-foreground mb-2">표시할 뉴스가 없습니다.</p>
              <p className="text-sm text-muted-foreground">
                {category ?
                  `${category} 카테고리의 뉴스를 불러오는 중입니다... 백엔드에서 HTML 파싱이 완료될 때까지 기다려주세요.` :
                  '뉴스 데이터를 불러오는 중입니다... 잠시만 기다려주세요.'}
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
      {news.imageUrl && !isInvalidImage(news.imageUrl) && (
        <div className="relative h-48">
          <Image
            src={news.imageUrl}
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

      {/* 이미지가 없을 때 대체 이미지 표시 */}
      {(!news.imageUrl || isInvalidImage(news.imageUrl)) && (
        <div className="relative h-48 bg-gray-100 flex items-center justify-center">
          <div className="text-gray-400 text-center">
            <svg className="w-12 h-12 mx-auto mb-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
            </svg>
            <p className="text-sm">이미지 없음</p>
          </div>
          {news.aiEnhanced && (
            <div className="absolute top-2 right-2 bg-[hsl(var(--variety-blue))] text-white px-2 py-1 rounded-md text-xs font-medium z-10">
              AI 강화
            </div>
          )}
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
          <Link href={news.id ? `/news/${news.id}` : '#'} className="hover:underline">
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
