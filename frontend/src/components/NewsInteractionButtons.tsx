'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth/authContext';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ThumbsUp, Bookmark, Share, MessageSquare, ThumbsDown, AlertTriangle } from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { type NewsForDisplay } from '@/lib/api/newsService';

interface NewsInteractionButtonsProps {
  newsId: string;
  initialStats?: {
    likes: number;
    comments: number;
    shares: number;
    trustScore?: number;
    sentimentScore?: number;
  };
  onCommentClick?: () => void;
}

export default function NewsInteractionButtons({
  newsId,
  initialStats = { likes: 0, comments: 0, shares: 0 },
  onCommentClick
}: NewsInteractionButtonsProps) {
  const { user, isAuthenticated } = useAuth();

  // 상호작용 상태
  const [liked, setLiked] = useState(false);
  const [bookmarked, setBookmarked] = useState(false);
  const [stats, setStats] = useState(initialStats);
  const [interactionLoading, setInteractionLoading] = useState(false);

  // 상호작용 신뢰도 분석
  const [trustAnalysis, setTrustAnalysis] = useState<{
    score: number;
    factors: Record<string, number>;
  } | null>(null);

  // 감정 분석
  const [sentimentAnalysis, setSentimentAnalysis] = useState<{
    score: number;
    label: string;
    positive: number;
    negative: number;
    neutral: number;
  } | null>(null);

  // 사용자 상호작용 상태 불러오기
  useEffect(() => {
    if (isAuthenticated && user && newsId) {
      loadUserInteractions();
      loadNewsAnalysis();
    }
  }, [isAuthenticated, user, newsId]);

  // 사용자 상호작용 불러오기
  const loadUserInteractions = async () => {
    if (!user) return;

    try {
      // 사용자 상호작용 이력 가져오기
      const interactions = await apiClient.users.getUserInteractions(user.id, newsId);

      // 좋아요, 북마크 상태 설정
      const userLiked = interactions.interactions.some(i => i.type === 'like');
      const userBookmarked = interactions.interactions.some(i => i.type === 'bookmark');

      setLiked(userLiked);
      setBookmarked(userBookmarked);

      // 뉴스 통계 가져오기
      const newsStats = await apiClient.news.getStats(newsId);
      setStats({
        ...initialStats,
        likes: newsStats.likes,
        comments: newsStats.comments,
        shares: newsStats.shares
      });

    } catch (error) {
      console.error('사용자 상호작용을 불러오는 중 오류:', error);
    }
  };

  // 뉴스 분석 정보 불러오기
  const loadNewsAnalysis = async () => {
    if (!newsId) return;

    try {
      // 병렬로 신뢰도 분석과 감정 분석 요청
      const [trustResponse, sentimentResponse] = await Promise.all([
        apiClient.ai.analyzeTrustScore(newsId),
        apiClient.ai.analyzeSentiment(newsId)
      ]);

      // 신뢰도 분석 설정
      setTrustAnalysis({
        score: trustResponse.trust_score,
        factors: trustResponse.trust_factors
      });

      // 감정 분석 설정
      setSentimentAnalysis({
        score: sentimentResponse.sentiment.score,
        label: sentimentResponse.sentiment.label,
        positive: sentimentResponse.sentiment.positive,
        negative: sentimentResponse.sentiment.negative,
        neutral: sentimentResponse.sentiment.neutral
      });

    } catch (error) {
      console.error('뉴스 분석을 불러오는 중 오류:', error);
    }
  };

  // 좋아요 토글
  const handleLikeToggle = async () => {
    if (!isAuthenticated || !user) {
      // 로그인이 필요함을 알림
      alert('좋아요를 누르려면 로그인이 필요합니다.');
      return;
    }

    setInteractionLoading(true);

    try {
      // 토글 동작을 먼저 UI에 반영
      const newLikedState = !liked;
      setLiked(newLikedState);

      // 좋아요 수 업데이트
      setStats(prev => ({
        ...prev,
        likes: newLikedState ? prev.likes + 1 : Math.max(0, prev.likes - 1)
      }));

      // 상호작용 기록
      await apiClient.users.recordInteraction(
        user.id,
        newsId,
        newLikedState ? 'like' : 'view' // 좋아요 취소 시 'view'로 기록
      );

    } catch (error) {
      console.error('좋아요 토글 중 오류:', error);
      // 오류 발생 시 이전 상태로 되돌림
      setLiked(!liked);
      loadUserInteractions();
    } finally {
      setInteractionLoading(false);
    }
  };

  // 북마크 토글
  const handleBookmarkToggle = async () => {
    if (!isAuthenticated || !user) {
      alert('북마크를 추가하려면 로그인이 필요합니다.');
      return;
    }

    setInteractionLoading(true);

    try {
      // 토글 동작을 먼저 UI에 반영
      const newBookmarkedState = !bookmarked;
      setBookmarked(newBookmarkedState);

      // 북마크 상태 업데이트
      await apiClient.news.toggleBookmark(
        newsId,
        user.id,
        newBookmarkedState
      );

    } catch (error) {
      console.error('북마크 토글 중 오류:', error);
      // 오류 발생 시 이전 상태로 되돌림
      setBookmarked(!bookmarked);
    } finally {
      setInteractionLoading(false);
    }
  };

  // 공유하기
  const handleShare = async () => {
    try {
      // 현재 URL 공유
      const shareData = {
        title: '버라이어티.AI 뉴스',
        text: '이 뉴스를 확인해 보세요',
        url: window.location.href
      };

      if (navigator.share) {
        await navigator.share(shareData);

        // 사용자가 로그인한 경우 공유 상호작용 기록
        if (isAuthenticated && user) {
          await apiClient.users.recordInteraction(
            user.id,
            newsId,
            'share'
          );

          // 공유 횟수 업데이트
          setStats(prev => ({ ...prev, shares: prev.shares + 1 }));
        }
      } else {
        // 공유 API가 없는 경우 URL 복사로 대체
        navigator.clipboard.writeText(window.location.href);
        alert('링크가 클립보드에 복사되었습니다.');
      }
    } catch (error) {
      console.error('공유하기 중 오류:', error);
    }
  };

  // 댓글 버튼 클릭
  const handleCommentClick = () => {
    if (onCommentClick) {
      onCommentClick();
    }
  };

  // 신뢰도 점수에 따른 색상 및 라벨
  const getTrustColor = (score: number) => {
    if (score >= 0.7) return 'bg-green-100 text-green-800';
    if (score >= 0.4) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const getTrustLabel = (score: number) => {
    if (score >= 0.7) return '높음';
    if (score >= 0.4) return '중간';
    return '낮음';
  };

  // 감정 분석 라벨 및 색상
  const getSentimentColor = (label: string) => {
    switch (label) {
      case 'positive': return 'bg-green-100 text-green-800';
      case 'negative': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getSentimentLabel = (label: string) => {
    switch (label) {
      case 'positive': return '긍정적';
      case 'negative': return '부정적';
      default: return '중립적';
    }
  };

  return (
    <div className="space-y-4">
      {/* 상호작용 버튼 */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          className={`flex items-center gap-2 ${liked ? 'bg-blue-50 text-blue-600' : ''}`}
          onClick={handleLikeToggle}
          disabled={interactionLoading}
        >
          <ThumbsUp className={`h-4 w-4 ${liked ? 'fill-blue-600 text-blue-600' : ''}`} />
          <span>{stats.likes > 0 ? stats.likes : '좋아요'}</span>
        </Button>

        <Button
          variant="outline"
          className={`flex items-center gap-2 ${bookmarked ? 'bg-yellow-50 text-yellow-600' : ''}`}
          onClick={handleBookmarkToggle}
          disabled={interactionLoading}
        >
          <Bookmark className={`h-4 w-4 ${bookmarked ? 'fill-yellow-600 text-yellow-600' : ''}`} />
          <span>북마크</span>
        </Button>

        <Button
          variant="outline"
          className="flex items-center gap-2"
          onClick={handleCommentClick}
        >
          <MessageSquare className="h-4 w-4" />
          <span>{stats.comments > 0 ? stats.comments : '댓글'}</span>
        </Button>

        <Button
          variant="outline"
          className="flex items-center gap-2"
          onClick={handleShare}
        >
          <Share className="h-4 w-4" />
          <span>{stats.shares > 0 ? stats.shares : '공유'}</span>
        </Button>
      </div>

      {/* 뉴스 분석 결과 */}
      <div className="flex flex-wrap gap-2 mt-4">
        {trustAnalysis && (
          <div className="inline-flex items-center">
            <Badge variant="outline" className={`${getTrustColor(trustAnalysis.score)}`}>
              <AlertTriangle className="h-3 w-3 mr-1" />
              신뢰도: {getTrustLabel(trustAnalysis.score)} ({(trustAnalysis.score * 10).toFixed(1)}점)
            </Badge>
          </div>
        )}

        {sentimentAnalysis && (
          <div className="inline-flex items-center">
            <Badge variant="outline" className={`${getSentimentColor(sentimentAnalysis.label)}`}>
              {sentimentAnalysis.label === 'positive' ? (
                <ThumbsUp className="h-3 w-3 mr-1" />
              ) : sentimentAnalysis.label === 'negative' ? (
                <ThumbsDown className="h-3 w-3 mr-1" />
              ) : null}
              감정: {getSentimentLabel(sentimentAnalysis.label)}
            </Badge>
          </div>
        )}
      </div>
    </div>
  );
}
