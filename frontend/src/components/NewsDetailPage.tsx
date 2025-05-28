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
    'button',
    'favicon',
  ];

  // 이미지 URL에 유효한 확장자가 있는지 확인
  const validExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp'];
  const hasValidExtension = validExtensions.some((ext) =>
    url.toLowerCase().includes(ext)
  );

  // 특정 뉴스 사이트 이미지 예외 처리
  // 조선일보
  if (url.includes('chosun.com/resizer') && hasValidExtension) {
    console.log('조선일보 이미지 URL 예외 허용:', url);
    return false;
  }

  // BBC 이미지
  if (url.includes('ichef.bbci.co.uk/news')) {
    console.log('BBC 이미지 URL 허용:', url);
    return false;
  }

  // 연합뉴스
  if (url.includes('img.yna.co.kr') && hasValidExtension) {
    console.log('연합뉴스 이미지 URL 허용:', url);
    return false;
  }

  // 오픈그래프 이미지는 일반적으로 유효함
  if (
    (url.includes('/og_') || url.includes('/opengraph/')) &&
    hasValidExtension
  ) {
    console.log('오픈그래프 이미지 URL 허용:', url);
    return false;
  }

  // feedburner 및 기타 RSS 피드 서비스 이미지 처리
  if (url.includes('feedburner.com') || url.includes('feedsportal.com')) {
    // feedburner 이미지가 실제로 존재하는지 확인하는 로직이 필요할 수 있음
    return false; // 일단 허용
  }

  // 이미지 URL에 일반적인 이미지 호스팅 서비스 패턴이 있는지 확인
  const imageHostingPatterns = [
    'i.imgur.com',
    'images.unsplash.com',
    'media.cnn.com',
    'img.youtube.com',
    'i0.wp.com',
    'i1.wp.com',
    'i2.wp.com',
    'image.ytn.co.kr',
    'image.aitimes.com',
    'photo.jtbc.co.kr',
    'images.khan.co.kr',
    'news.kbs.co.kr/data',
    'imgnews.pstatic.net'
  ];

  if (imageHostingPatterns.some(pattern => url.includes(pattern))) {
    console.log('이미지 호스팅 서비스에서 이미지 허용:', url);
    return false;
  }

  // 패턴 매칭 (유효하지 않은 패턴 포함 여부 확인)
  return invalidPatterns.some((pattern) =>
    url.toLowerCase().includes(pattern)
  );
}

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [newsId, isAuthenticated, user]);

  // 사용자 상호작용 기록
  const recordInteraction = async (
    type: 'view' | 'click' | 'read' | 'like' | 'share'
  ) => {
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
        setRelatedNews(related.filter((news) => news.id !== newsId));
      }
    } catch (error) {
      console.error('관련 뉴스를 가져오는 중 오류:', error);
    }
  };

  // AI 분석 데이터 가져오기
  const fetchAiAnalysis = async () => {
    try {
      // 각 API 호출에 개별적인 try-catch를 적용하여 하나가 실패해도 다른 것들이 가능하도록 함
      let trustAnalysis = { trust_score: 0.5 };
      let sentimentAnalysis = {
        sentiment: {
          score: 0,
          label: 'neutral',
          positive: 0.33,
          negative: 0.33,
          neutral: 0.34,
        },
      };
      let keywordAnalysis = { key_phrases: [] };
      let summarization = { summary: '' };

      try {
        trustAnalysis = await apiClient.ai.analyzeTrustScore(newsId);
      } catch (err) {
        console.error('신뢰도 분석 중 오류:', err);
        // 기본값은 이미 설정됨
      }

      try {
        sentimentAnalysis = await apiClient.ai.analyzeSentiment(newsId);
      } catch (err) {
        console.error('감정 분석 중 오류:', err);
        // 기본값은 이미 설정됨
      }

      try {
        keywordAnalysis = await apiClient.ai.extractKeyPhrases(newsId);
      } catch (err) {
        console.error('키워드 추출 중 오류:', err);
        // 기본값은 이미 설정됨
      }

      try {
        summarization = await apiClient.ai.summarizeNews(newsId);
      } catch (err) {
        console.error('요약 생성 중 오류:', err);
        // 기본값은 이미 설정됨
      }

      // 안전한 접근 보장
      setAiAnalysis({
        trustScore: trustAnalysis?.trust_score || 0.5,
        sentimentScore: sentimentAnalysis?.sentiment?.score || 0,
        sentiment: {
          label: sentimentAnalysis?.sentiment?.label || 'neutral',
          positive: sentimentAnalysis?.sentiment?.positive || 0.33,
          negative: sentimentAnalysis?.sentiment?.negative || 0.33,
          neutral: sentimentAnalysis?.sentiment?.neutral || 0.34,
        },
        keyPhrases: keywordAnalysis?.key_phrases || [],
        summary: summarization?.summary || '요약을 생성할 수 없습니다.',
      });
    } catch (error) {
      console.error('AI 분석 데이터를 가져오는 중 오류:', error);
      // 기본 분석 데이터 설정
      setAiAnalysis({
        trustScore: 0.5,
        sentimentScore: 0,
        sentiment: {
          label: 'neutral',
          positive: 0.33,
          negative: 0.33,
          neutral: 0.34,
        },
        keyPhrases: [],
        summary: '요약을 생성할 수 없습니다.',
      });
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
                <Button className="mt-4" onClick={() => router.push('/')}>
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

  // 뉴스 데이터 디버깅
  console.log('뉴스 데이터:', newsItem);

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
              {newsItem.categories && newsItem.categories.map((category: string) => (
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
            {newsItem.imageUrl && !isInvalidImage(newsItem.imageUrl) && (
              <div className="mb-6 rounded-md overflow-hidden">
                <img
                  src={newsItem.imageUrl}
                  alt={newsItem.title}
                  className="object-cover w-full max-h-96 rounded-md"
                  onError={(e) => {
                    console.log('썸네일 이미지 로드 오류, 대체 이미지 사용');
                    (e.target as HTMLImageElement).src =
                      'https://via.placeholder.com/800x450?text=뉴스+이미지';
                    (e.target as HTMLImageElement).onerror = null; // 무한 루프 방지
                  }}
                />
              </div>
            )}

            {/* AI 요약 - 본문 중복 확인 및 요약과 내용의 차이 확인 */}
            {(aiAnalysis.summary || newsItem.summary) && (
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
                  {aiAnalysis.summary &&
                  aiAnalysis.summary !== newsItem.content &&
                  aiAnalysis.summary.length > 20
                    ? aiAnalysis.summary
                    : newsItem.summary &&
                      newsItem.summary !== newsItem.content &&
                      newsItem.summary.length > 20
                    ? newsItem.summary
                    : '이 뉴스의 요약을 생성할 수 없습니다.'}
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

            {/* 뉴스 컨텐츠 표시 - 한국어 기사 포맷에 맞게 조정 */}
            <div className="prose max-w-none mb-6">
              {/* 뉴스 내용 헤더 - 눈에 띄게 표시 */}
              <h3 className="text-lg font-bold text-gray-800 mb-4 border-b pb-2">
                뉴스 본문
              </h3>

              {/* 본문 내에 이미지 중복 표시 방지 - 썸네일에 이미 표시되었으므로 본문에서는 제거 */}

              {/* 본문 내용이 비어있지 않은지 확인 */}
              {newsItem.content && newsItem.content.trim() ? (
                // 본문 내용 표시
                <>
                  {/* 본문 내용이 너무 짧으면 대체 메시지 표시 */}
                  {newsItem.content.trim().length < 100 ? (
                    <div className="p-4 bg-yellow-50 rounded-md text-gray-700 mb-4">
                      <p>전체 뉴스 내용을 보려면 아래 원문 링크를 클릭하세요.</p>
                      {newsItem.content && (
                        <p className="mt-2 font-medium">{newsItem.content}</p>
                      )}
                    </div>
                  ) : (
                    // 충분히 긴 내용이 있는 경우 정상 표시
                    newsItem.content
                      .split('\n')
                      .map((paragraph: string) => paragraph.trim())
                      .filter(Boolean) // 빈 문단 제거
                      .map((paragraph: string, idx: number) => {
                        // 첫 단락은 들여쓰기 없이 볼드체로
                        if (idx === 0) {
                          return (
                            <p key={idx} className="font-medium leading-relaxed my-4">
                              {paragraph}
                            </p>
                          );
                        }

                        // 인용구 감지 (따옴표로 시작하는 경우)
                        if (
                          paragraph.startsWith('"') ||
                          paragraph.startsWith('"') ||
                          paragraph.startsWith("'") ||
                          paragraph.startsWith("'")
                        ) {
                          return (
                            <blockquote
                              key={idx}
                              className="italic border-l-4 border-gray-300 pl-4 my-4"
                            >
                              {paragraph}
                            </blockquote>
                          );
                        }

                        // 일반 단락 - 적절한 들여쓰기와 줄간격
                        return (
                          <p key={idx} className="indent-4 my-4 leading-relaxed">
                            {paragraph}
                          </p>
                        );
                      })
                  )}
                </>
              ) : (
                // 본문이 비어있는 경우 대체 메시지 표시
                <div className="p-4 bg-gray-100 rounded-md text-gray-600">
                  <p>뉴스 본문을 불러올 수 없습니다. 원문 링크를 통해 확인해주세요.</p>
                </div>
              )}
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
                sentimentScore: aiAnalysis.sentimentScore,
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
                {relatedNews.map((item) => (
                  <Card
                    key={item.id}
                    className="overflow-hidden hover:shadow-md transition-shadow"
                  >
                    <Link href={`/news/${item.id}`}>
                      <div className="h-40 relative">
                        {item.image_url && !isInvalidImage(item.image_url) ? (
                          <img
                            src={item.image_url}
                            alt={item.title}
                            className="object-cover w-full h-full"
                            onError={(e) => {
                              console.log('이미지 로드 오류, 대체 이미지 사용');
                              (e.target as HTMLImageElement).src =
                                'https://via.placeholder.com/400x300?text=News+Image';
                              // 무한 루프 방지
                              (e.target as HTMLImageElement).onerror = null;
                            }}
                          />
                        ) : (
                          <div className="h-full w-full bg-gray-100 flex items-center justify-center">
                            <span className="text-gray-400">이미지 없음</span>
                          </div>
                        )}
                      </div>
                      <CardContent className="p-4">
                        <h3 className="font-semibold line-clamp-2 mb-2">
                          {item.title}
                        </h3>
                        <div className="flex justify-between text-xs text-gray-500">
                          <span>{item.source}</span>
                          <span>
                            {new Date(item.published_date).toLocaleDateString()}
                          </span>
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
