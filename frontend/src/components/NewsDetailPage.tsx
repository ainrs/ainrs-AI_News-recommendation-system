'use client';

import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useNews } from '@/lib/hooks/useNews';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ChevronLeft } from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/authContext';
import Header from '@/components/Header';
import MainNavigation from '@/components/MainNavigation';
import Footer from '@/components/Footer';
import NewsInteractionButtons from '@/components/NewsInteractionButtons';
import NewsComments from '@/components/NewsComments';
import NewsAIAnalysis from '@/components/NewsAIAnalysis';
import NewsQuestionAnswering from '@/components/NewsQuestionAnswering';

export default function NewsDetailPage({ newsId }: { newsId: string }) {
  const router = useRouter();
  const { user, isAuthenticated } = useAuth();
  const { news, loading, error, fetchNewsById } = useNews();
  const [showComments, setShowComments] = useState(false);
  const commentsSectionRef = useRef<HTMLDivElement>(null);

  // 관련 기사 추천
  const [relatedNews, setRelatedNews] = useState<any[]>([]);
  const [aiAnalysis, setAiAnalysis] = useState<{
    trustScore?: number;
    sentimentScore?: number;
    keyPhrases?: string[];
    summary?: string;
    sentiment?: {
      label: string;
      positive: number;
      negative: number;
      neutral: number;
    };
  }>({});

  // 뉴스 데이터 가져오기
  useEffect(() => {
    if (newsId) {
      fetchNewsById(newsId);

      // 로그인한 경우 조회 상호작용 기록
      if (isAuthenticated && user) {
        recordInteraction('view');
      }

      // 관련 뉴스 가져오기
      fetchRelatedNews();

      // AI 분석 데이터 가져오기
      fetchAiAnalysis();
    }
  }, [newsId, isAuthenticated, user]);

  // 사용자 상호작용 기록
  const recordInteraction = async (type: 'view' | 'click' | 'read' | 'like' | 'share') => {
    if (!isAuthenticated || !user) return;

    try {
      await apiClient.users.recordInteraction(user.id, newsId, type);
    } catch (error) {
      console.error('상호작용 기록 중 오류:', error);
    }
  };

  // 관련 뉴스 가져오기
  const fetchRelatedNews = async () => {
    try {
      // 현재 뉴스 데이터가 있으면 그 콘텐츠로 검색
      const currentNews = await apiClient.news.getById(newsId);
      if (currentNews) {
        const query = `${currentNews.title} ${currentNews.summary || ''}`;
        const related = await apiClient.ai.searchNewsByVector(query, 4);
        // 현재 뉴스는 필터링
        setRelatedNews(related.filter(news => news.id !== newsId));
      }
    } catch (error) {
      console.error('관련 뉴스를 가져오는 중 오류:', error);
    }
  };

  // AI 분석 데이터 가져오기
  const fetchAiAnalysis = async () => {
    try {
      // 병렬 요청으로 신뢰도 및 감정 분석 데이터 가져오기
      const [trustAnalysis, sentimentAnalysis, keywordAnalysis] = await Promise.all([
        apiClient.ai.analyzeTrustScore(newsId),
        apiClient.ai.analyzeSentiment(newsId),
        apiClient.ai.extractKeyPhrases(newsId)
      ]);

      // 텍스트 요약 가져오기
      const summarization = await apiClient.ai.summarizeNews(newsId);

      setAiAnalysis({
        trustScore: trustAnalysis.trust_score,
        sentimentScore: sentimentAnalysis.sentiment.score,
        sentiment: {
          label: sentimentAnalysis.sentiment.label,
          positive: sentimentAnalysis.sentiment.positive,
          negative: sentimentAnalysis.sentiment.negative,
          neutral: sentimentAnalysis.sentiment.neutral
        },
        keyPhrases: keywordAnalysis.key_phrases,
        summary: summarization.summary
      });
    } catch (error) {
      console.error('AI 분석 데이터를 가져오는 중 오류:', error);
    }
  };

  // 댓글 섹션으로 스크롤
  const scrollToComments = () => {
    setShowComments(true);

    setTimeout(() => {
      if (commentsSectionRef.current) {
        commentsSectionRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    }, 100);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col">
        <Header />
        <MainNavigation />
        <main className="flex-grow bg-background">
          <div className="variety-container py-8">
            <Button
              variant="ghost"
              className="mb-4"
              onClick={() => router.back()}
            >
              <ChevronLeft className="mr-2 h-4 w-4" />
              뒤로 가기
            </Button>

            {/* 로딩 스켈레톤 */}
            <div className="space-y-4">
              <Skeleton className="h-8 w-3/4" />
              <Skeleton className="h-4 w-1/4 mb-6" />
              <Skeleton className="h-96 w-full rounded-md" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  if (error || news.length === 0) {
    return (
      <div className="min-h-screen flex flex-col">
        <Header />
        <MainNavigation />
        <main className="flex-grow bg-background">
          <div className="variety-container py-8">
            <Button
              variant="ghost"
              className="mb-4"
              onClick={() => router.back()}
            >
              <ChevronLeft className="mr-2 h-4 w-4" />
              뒤로 가기
            </Button>

            <Card>
              <CardContent className="py-10 text-center">
                <h2 className="text-xl font-bold mb-2">뉴스를 찾을 수 없습니다</h2>
                <p className="text-muted-foreground">
                  요청하신 뉴스를 찾을 수 없거나 접근할 수 없습니다.
                </p>
                <Button
                  className="mt-4"
                  onClick={() => router.push('/')}
                >
                  홈으로 돌아가기
                </Button>
              </CardContent>
            </Card>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  const newsItem = news[0];

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <MainNavigation />
      <main className="flex-grow bg-background">
        <div className="variety-container py-8">
          <Button
            variant="ghost"
            className="mb-4"
            onClick={() => router.back()}
          >
            <ChevronLeft className="mr-2 h-4 w-4" />
            뒤로 가기
          </Button>

          <article className="bg-white border rounded-lg p-6 mb-6">
            {/* 뉴스 카테고리 */}
            <div className="flex flex-wrap gap-2 mb-4">
              {newsItem.categories.map(category => (
                <Link
                  key={category}
                  href={`/?category=${encodeURIComponent(category)}`}
                  className="text-sm text-[hsl(var(--variety-blue))] hover:underline"
                >
                  #{category}
                </Link>
              ))}
            </div>

            {/* 뉴스 제목 */}
            <div className="flex items-center mb-3">
              <h1 className="text-3xl font-bold">{newsItem.title}</h1>
              {newsItem.aiEnhanced && (
                <span className="ml-3 bg-[hsl(var(--variety-blue))] text-white text-xs font-semibold px-2 py-1 rounded">
                  AI 강화
                </span>
              )}
            </div>

            {/* 뉴스 메타 정보 */}
            <div className="flex justify-between items-center mb-6 text-sm text-gray-500">
              <div>
                <span className="font-medium text-gray-700">{newsItem.source}</span>
                {newsItem.author && <span> · {newsItem.author}</span>}
                <span> · {newsItem.publishedDate}</span>
              </div>
            </div>

            {/* 뉴스 썸네일 */}
            {newsItem.imageUrl && (
              <div className="relative h-96 mb-6 rounded-md overflow-hidden">
                <Image
                  src={newsItem.imageUrl}
                  alt={newsItem.title}
                  fill
                  className="object-cover"
                />
              </div>
            )}

            {/* AI 요약 */}
            {(aiAnalysis.summary || newsItem.aiEnhanced) && (
              <div className="bg-blue-50 p-4 rounded-md mb-6">
                <h3 className="font-semibold text-blue-800 mb-2 flex items-center">
                  <span className="mr-2">AI 요약</span>
                  {newsItem.aiEnhanced && (
                    <span className="text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">
                      실시간 분석
                    </span>
                  )}
                </h3>
                <p className="text-blue-800">
                  {aiAnalysis.summary || newsItem.summary}
                </p>
              </div>
            )}

            {/* AI 뉴스 분석 */}
            <NewsAIAnalysis
              newsId={newsId}
              trustScore={aiAnalysis.trustScore}
              sentimentScore={aiAnalysis.sentimentScore}
              sentiment={aiAnalysis.sentiment}
              keyPhrases={aiAnalysis.keyPhrases}
              loading={loading}
            />

            {/* 뉴스 본문 */}
            <div className="mb-2">
              {newsItem.aiEnhanced && newsItem.trustScore > 0 && (
                <div className="flex items-center mb-2">
                  <div className="mr-2 text-sm font-medium">신뢰도:</div>
                  <div className="flex-grow h-2.5 bg-gray-200 rounded-full">
                    <div
                      className={`h-2.5 rounded-full ${
                        newsItem.trustScore >= 0.7
                          ? 'bg-green-500'
                          : newsItem.trustScore >= 0.4
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${newsItem.trustScore * 100}%` }}
                    ></div>
                  </div>
                  <div className="ml-2 text-sm text-gray-500">
                    {Math.round(newsItem.trustScore * 100)}%
                  </div>
                </div>
              )}
            </div>
            <div className="prose max-w-none mb-6">
              {newsItem.content.split('\n').map((paragraph, idx) => (
                <p key={idx}>{paragraph}</p>
              ))}
            </div>

            {/* 뉴스 원문 링크 */}
            {newsItem.url && (
              <div className="my-6">
                <Link
                  href={newsItem.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[hsl(var(--variety-blue))] hover:underline flex items-center"
                >
                  원문 보기
                  <span className="inline-block ml-1">↗</span>
                </Link>
              </div>
            )}

            {/* 상호작용 버튼 */}
            <NewsInteractionButtons
              newsId={newsId}
              initialStats={{
                likes: 0,
                comments: 0,
                shares: 0,
                trustScore: aiAnalysis.trustScore,
                sentimentScore: aiAnalysis.sentimentScore
              }}
              onCommentClick={scrollToComments}
            />
          </article>

          {/* AI에게 질문하기 */}
          <NewsQuestionAnswering newsId={newsId} />

          {/* 관련 뉴스 */}
          {relatedNews.length > 0 && (
            <div className="mb-8">
              <h2 className="text-xl font-bold mb-4">관련 뉴스</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {relatedNews.map(item => (
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
                          <span>{new Date(item.published_date).toLocaleDateString()}</span>
                        </div>
                      </CardContent>
                    </Link>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* 댓글 섹션 */}
          <div ref={commentsSectionRef}>
            <NewsComments newsId={newsId} />
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
