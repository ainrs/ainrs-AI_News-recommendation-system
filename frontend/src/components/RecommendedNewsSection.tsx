'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Card, CardContent } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import {
  BadgeInfo,
  ThumbsUp,
  Award,
  Sparkles
} from 'lucide-react';
import apiClient from '@/lib/api/client';
import type { NewsForDisplay } from '@/lib/api/newsService';

interface RecommendedNewsProps {
  title?: string;
  userId: string;
  limit?: number;
  fallbackData?: any[]; // 콜드 스타트 추천 데이터
  isColdStartLoading?: boolean; // 콜드 스타트 로딩 상태
}

export default function RecommendedNewsSection({
  title = '맞춤 추천',
  userId,
  limit = 5,
  fallbackData = [],
  isColdStartLoading = false
}: RecommendedNewsProps) {
  const [news, setNews] = useState<NewsForDisplay[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [recommendationType, setRecommendationType] = useState<'collaborative' | 'personalized' | 'latest' | 'coldstart'>('latest'); // 기본값을 'latest'로 변경
  const [usedFallback, setUsedFallback] = useState<boolean>(false); // 폴백 데이터를 사용했는지 여부

  useEffect(() => {
    // 사용자 ID가 있거나 콜드 스타트 추천이 선택된 경우 추천을 가져옴
    if (userId || recommendationType === 'coldstart') {
      fetchRecommendations();
    }
  }, [userId, limit, recommendationType]);

  // 폴백 데이터가 변경되면 오류 상태에서 자동으로 폴백 데이터를 사용
  useEffect(() => {
    if (fallbackData && fallbackData.length > 0 && (error || news.length === 0) && !usedFallback) {
      console.log('콜드 스타트 폴백 데이터 사용:', fallbackData.length);
      const formattedFallback = formatNewsData(fallbackData);
      setNews(formattedFallback);
      setUsedFallback(true);
      setError(null);
      setLoading(false);
    }
  }, [fallbackData, error, usedFallback]);

  // 결과를 NewsForDisplay 형식으로 변환하는 함수
  const formatNewsData = (data: any[]): NewsForDisplay[] => {
    return data.map((item: any) => ({
      id: item.id || item._id,
      title: item.title,
      content: item.content || '',
      summary: item.summary || '',
      source: item.source,
      publishedDate: new Date(item.published_date).toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      }),
      author: item.author || '',
      imageUrl: item.image_url || '',
      categories: item.categories || [],
      url: item.url || '',
      trustScore: item.trust_score || 0,
      sentimentScore: item.sentiment_score || 0,
      recommendationScore: item.recommendation_score,
      recommendationReason: item.recommendation_reason || "추천 시스템에서 선택한 콘텐츠",
    }));
  };

  const fetchRecommendations = async () => {
    if (!userId && recommendationType !== 'coldstart') return;

    setLoading(true);
    try {
      let recommendedNews;

      switch (recommendationType) {
        case 'collaborative':
          // 협업 필터링 기반 추천
          recommendedNews = await apiClient.ai.getCollaborativeFilteringRecommendations(userId, limit);
          break;
        case 'personalized':
          // 개인화 추천
          recommendedNews = await apiClient.users.getRecommendations(userId, limit);
          break;
        case 'coldstart':
          // 콜드 스타트 추천
          recommendedNews = await apiClient.news.getColdStartRecommendations(limit);
          break;
        case 'latest':
        default:
          // 최신 뉴스 (기본값)
          recommendedNews = await apiClient.news.getAll({ limit });
          break;
      }

      // 결과가 없으면 폴백 데이터 사용
      if (!recommendedNews || recommendedNews.length === 0) {
        if (fallbackData && fallbackData.length > 0 && !usedFallback) {
          console.log('API 응답이 비어있어 콜드 스타트 폴백 데이터 사용');
          recommendedNews = fallbackData;
          setUsedFallback(true);
        }
      }

      // 결과를 NewsForDisplay 형식으로 변환
      const formattedNews = formatNewsData(recommendedNews);

      setNews(formattedNews);
      setError(null);
    } catch (err) {
      console.error('추천 뉴스를 가져오는 중 오류:', err);
      setError('추천 뉴스를 가져오는 중 오류가 발생했습니다.');
      setNews([]);
    } finally {
      setLoading(false);
    }
  };

  // 추천 유형 변경 핸들러
  const handleChangeRecommendationType = (type: 'collaborative' | 'personalized' | 'latest') => {
    setRecommendationType(type);
  };

  // 로딩 상태
  if (loading) {
    return (
      <div className="space-y-4 mb-8">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">{title}</h2>
          <div className="flex gap-2">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-8 w-24" />
          </div>
        </div>
        {[1, 2, 3].map((id) => (
          <Card key={`recommended-skeleton-${id}`} className="p-4">
            <div className="flex gap-4">
              <Skeleton className="h-16 w-16 rounded-md" />
              <div className="flex-1">
                <Skeleton className="h-4 w-3/4 mb-2" />
                <Skeleton className="h-3 w-1/2 mb-1" />
                <Skeleton className="h-3 w-1/4" />
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  // 에러 상태
  if (error) {
    return (
      <div className="mb-8">
        <h2 className="text-xl font-bold mb-4">{title}</h2>
        <Card className="p-4 bg-red-50">
          <p className="text-red-700">{error}</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="mb-8">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold flex items-center">
          <Sparkles className="mr-2 h-5 w-5 text-[hsl(var(--variety-blue))]" />
          {title}
        </h2>
        <div className="flex gap-2 text-sm">
          <button
            onClick={() => handleChangeRecommendationType('collaborative')}
            className={`px-3 py-1 rounded ${
              recommendationType === 'collaborative'
                ? 'bg-[hsl(var(--variety-blue))] text-white'
                : 'bg-gray-100'
            }`}
          >
            협업 필터링
          </button>
          <button
            onClick={() => handleChangeRecommendationType('personalized')}
            className={`px-3 py-1 rounded ${
              recommendationType === 'personalized'
                ? 'bg-[hsl(var(--variety-blue))] text-white'
                : 'bg-gray-100'
            }`}
          >
            맞춤 추천
          </button>
          <button
            onClick={() => handleChangeRecommendationType('coldstart')}
            className={`px-3 py-1 rounded ${
              recommendationType === 'coldstart'
                ? 'bg-[hsl(var(--variety-blue))] text-white'
                : 'bg-gray-100'
            }`}
          >
            빠른추천
          </button>
          <button
            onClick={() => handleChangeRecommendationType('latest')}
            className={`px-3 py-1 rounded ${
              recommendationType === 'latest'
                ? 'bg-[hsl(var(--variety-blue))] text-white'
                : 'bg-gray-100'
            }`}
          >
            최신 뉴스
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {news.length > 0 ? (
          news.map((item) => (
            <Card key={item.id} className="p-3 hover:shadow-md transition-shadow">
              <Link href={`/news/${item.id}`} className="block">
                <div className="flex gap-3">
                  {item.imageUrl ? (
                    <div className="w-16 h-16 relative rounded-md overflow-hidden flex-shrink-0">
                      <Image
                        src={item.imageUrl}
                        alt={item.title}
                        fill
                        className="object-cover"
                      />
                    </div>
                  ) : (
                    <div className="w-16 h-16 bg-gray-100 rounded-md flex items-center justify-center flex-shrink-0">
                      <BadgeInfo className="h-6 w-6 text-gray-400" />
                    </div>
                  )}
                  <div className="flex-1">
                    <h3 className="font-medium text-sm line-clamp-2 mb-1">
                      {item.title}
                    </h3>
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>{item.source}</span>
                      <span>{item.publishedDate}</span>
                    </div>
                    {item.recommendationScore && (
                      <div className="mt-1 text-xs flex items-center">
                        <span className="flex items-center text-amber-600 mr-2">
                          <Award className="h-3 w-3 mr-1" />
                          추천점수: {item.recommendationScore?.toFixed(1)}
                        </span>
                        {item.trustScore > 0 && (
                          <span className="flex items-center text-blue-600">
                            <ThumbsUp className="h-3 w-3 mr-1" />
                            신뢰도: {(item.trustScore * 10).toFixed(1)}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                {item.recommendationReason && (
                  <div className="mt-2 text-xs text-gray-600 bg-gray-50 p-2 rounded">
                    <span className="font-medium">추천 이유: </span>
                    {item.recommendationReason}
                  </div>
                )}
              </Link>
            </Card>
          ))
        ) : (
          <Card className="p-4 text-center text-gray-500">
            <p>추천할 뉴스가 없습니다.</p>
            <p className="text-sm mt-1">
              더 많은 뉴스를 읽고 상호작용하면 맞춤 추천을 받을 수 있습니다.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}
