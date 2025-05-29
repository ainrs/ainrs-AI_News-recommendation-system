'use client';

import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { newsService } from '@/lib/api/newsService';
import type { News } from '@/lib/api/types';
import Link from 'next/link';
import Image from 'next/image';

// 백엔드 스마트 필터링 시스템의 카테고리 구조
const CATEGORIES = [
  { key: '인공지능', label: '인공지능', target: 8, color: 'bg-blue-500' },
  { key: 'IT기업', label: 'IT기업', target: 6, color: 'bg-green-500' },
  { key: '빅데이터', label: '빅데이터', target: 6, color: 'bg-purple-500' },
  { key: '스타트업', label: '스타트업', target: 5, color: 'bg-orange-500' },
  { key: '클라우드', label: '클라우드', target: 5, color: 'bg-cyan-500' },
  { key: '로봇', label: '로봇', target: 4, color: 'bg-red-500' },
  { key: '블록체인', label: '블록체인', target: 4, color: 'bg-yellow-500' },
  { key: '메타버스', label: '메타버스', target: 4, color: 'bg-pink-500' },
  { key: 'AI서비스', label: 'AI서비스', target: 4, color: 'bg-indigo-500' },
  { key: '칼럼', label: '칼럼', target: 4, color: 'bg-gray-500' }
];

interface CategoryNewsData {
  [category: string]: {
    news: News[];
    loading: boolean;
    error: string | null;
  };
}

export function CategoryNewsSection() {
  const [activeCategory, setActiveCategory] = useState(CATEGORIES[0].key);
  const [categoryData, setCategoryData] = useState<CategoryNewsData>({});

  // 카테고리별 뉴스 로딩
  const loadCategoryNews = async (category: string) => {
    const categoryInfo = CATEGORIES.find(c => c.key === category);
    const limit = categoryInfo?.target || 10;

    setCategoryData(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        loading: true,
        error: null
      }
    }));

    try {
      const news = await newsService.getNewsByCategory(category, limit);
      setCategoryData(prev => ({
        ...prev,
        [category]: {
          news,
          loading: false,
          error: null
        }
      }));
    } catch (error) {
      setCategoryData(prev => ({
        ...prev,
        [category]: {
          news: [],
          loading: false,
          error: '뉴스를 불러오는데 실패했습니다.'
        }
      }));
    }
  };

  // 초기 로딩 및 카테고리 변경 시 로딩
  useEffect(() => {
    if (!categoryData[activeCategory]?.news?.length) {
      loadCategoryNews(activeCategory);
    }
  }, [activeCategory]);

  // 카테고리 변경 핸들러
  const handleCategoryChange = (category: string) => {
    setActiveCategory(category);
  };

  // 이미지 URL 검증
  const getValidImageUrl = (imageUrl?: string): string => {
    if (!imageUrl ||
        imageUrl.includes('audio_play') ||
        imageUrl.includes('.svg') ||
        imageUrl.includes('static/media') ||
        imageUrl.includes('icon') ||
        imageUrl.includes('logo') ||
        imageUrl.includes('button')) {
      return '/placeholder-image.png';
    }
    return imageUrl;
  };

  // 뉴스 카드 컴포넌트
  const NewsCard = ({ news }: { news: News }) => (
    <Link href={`/news/${news._id || news.id}`}>
      <Card className="hover:shadow-lg transition-shadow duration-200 cursor-pointer h-full">
        <div className="aspect-video relative overflow-hidden rounded-t-lg">
          <Image
            src={getValidImageUrl(news.image_url)}
            alt={news.title}
            fill
            className="object-cover"
            onError={(e) => {
              const target = e.target as HTMLImageElement;
              target.src = '/placeholder-image.png';
            }}
          />
        </div>
        <CardContent className="p-4">
          <h3 className="font-semibold text-sm line-clamp-2 mb-2">
            {news.title}
          </h3>
          {news.summary && (
            <p className="text-gray-600 text-xs line-clamp-3 mb-2">
              {news.summary}
            </p>
          )}
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{news.source}</span>
            <span>{new Date(news.published_date).toLocaleDateString()}</span>
          </div>
          {news.categories && news.categories.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {news.categories.slice(0, 2).map((category, idx) => (
                <Badge key={idx} variant="secondary" className="text-xs">
                  {category}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );

  // 로딩 스켈레톤
  const LoadingSkeleton = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: 6 }).map((_, idx) => (
        <Card key={idx}>
          <Skeleton className="aspect-video" />
          <CardContent className="p-4">
            <Skeleton className="h-4 mb-2" />
            <Skeleton className="h-4 mb-2" />
            <Skeleton className="h-3 w-2/3" />
          </CardContent>
        </Card>
      ))}
    </div>
  );

  const currentCategoryData = categoryData[activeCategory];

  return (
    <section className="mb-10">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">카테고리별 뉴스</h2>
        <div className="text-sm text-gray-500">
          스마트 필터링으로 선별된 최고 품질의 뉴스
        </div>
      </div>

      <Tabs value={activeCategory} onValueChange={handleCategoryChange} className="w-full">
        <TabsList className="grid w-full grid-cols-5 lg:grid-cols-10 mb-6">
          {CATEGORIES.map((category) => (
            <TabsTrigger
              key={category.key}
              value={category.key}
              className="text-xs px-2 py-1"
            >
              <div className="flex items-center space-x-1">
                <div className={`w-2 h-2 rounded-full ${category.color}`} />
                <span>{category.label}</span>
              </div>
            </TabsTrigger>
          ))}
        </TabsList>

        {CATEGORIES.map((category) => (
          <TabsContent key={category.key} value={category.key} className="mt-6">
            <div className="mb-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${category.color}`} />
                  <span>{category.label} 뉴스</span>
                </h3>
                <Badge variant="outline">
                  목표: {category.target}개 |
                  {currentCategoryData?.news?.length || 0}개 수집됨
                </Badge>
              </div>
            </div>

            {currentCategoryData?.loading && <LoadingSkeleton />}

            {currentCategoryData?.error && (
              <div className="text-center py-8">
                <p className="text-red-500 mb-4">{currentCategoryData.error}</p>
                <button
                  onClick={() => loadCategoryNews(category.key)}
                  className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  다시 시도
                </button>
              </div>
            )}

            {currentCategoryData?.news && currentCategoryData.news.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {currentCategoryData.news.map((news) => (
                  <NewsCard key={news._id || news.id} news={news} />
                ))}
              </div>
            )}

            {currentCategoryData && !currentCategoryData.loading &&
             currentCategoryData.news.length === 0 && !currentCategoryData.error && (
              <div className="text-center py-8 text-gray-500">
                <p>아직 {category.label} 카테고리의 뉴스가 없습니다.</p>
                <p className="text-sm mt-2">새로운 뉴스를 수집 중입니다...</p>
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>
    </section>
  );
}
