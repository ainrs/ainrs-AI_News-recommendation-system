'use client';

import { useState, useEffect, useCallback } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Bell, Wifi, WifiOff, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import { newsService } from '@/lib/api/newsService';
import type { News } from '@/lib/api/types';

interface RealTimeUpdate {
  type: 'new_article' | 'category_update' | 'trending_change';
  data: any;
  timestamp: string;
}

interface RealTimeNewsUpdatesProps {
  onNewArticle?: (article: News) => void;
  categories?: string[];
}

export function RealTimeNewsUpdates({
  onNewArticle,
  categories = []
}: RealTimeNewsUpdatesProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [updates, setUpdates] = useState<RealTimeUpdate[]>([]);
  const [newArticlesCount, setNewArticlesCount] = useState(0);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isPolling, setIsPolling] = useState(false);

  // WebSocket이 지원되지 않는 환경에서는 폴링 사용
  const usePolling = useCallback(() => {
    return typeof window === 'undefined' || !window.WebSocket;
  }, []);

  // 폴링 기반 실시간 업데이트
  const startPolling = useCallback(async () => {
    if (isPolling) return;

    setIsPolling(true);
    setIsConnected(true);

    const pollInterval = setInterval(async () => {
      try {
        // 최신 뉴스 확인 (마지막 업데이트 이후)
        const latestNews = await newsService.getLatestNews(5);

        if (latestNews && latestNews.length > 0) {
          const lastUpdateTime = lastUpdate ? new Date(lastUpdate) : new Date(Date.now() - 5 * 60 * 1000); // 5분 전

          const newArticles = latestNews.filter(article =>
            new Date(article.published_date) > lastUpdateTime
          );

          if (newArticles.length > 0) {
            newArticles.forEach(article => {
              const update: RealTimeUpdate = {
                type: 'new_article',
                data: article,
                timestamp: new Date().toISOString()
              };

              setUpdates(prev => [update, ...prev.slice(0, 19)]); // 최근 20개만 유지
              setNewArticlesCount(prev => prev + 1);

              if (onNewArticle) {
                onNewArticle(article);
              }
            });

            setLastUpdate(new Date().toISOString());
          }
        }

        setRetryCount(0); // 성공 시 재시도 카운트 리셋
      } catch (error) {
        console.error('폴링 업데이트 실패:', error);
        setRetryCount(prev => prev + 1);

        if (retryCount >= 3) {
          setIsConnected(false);
          setIsPolling(false);
          clearInterval(pollInterval);
        }
      }
    }, 30000); // 30초마다 폴링

    // 컴포넌트 언마운트 시 정리
    return () => {
      clearInterval(pollInterval);
      setIsPolling(false);
    };
  }, [isPolling, lastUpdate, onNewArticle, retryCount]);

  // WebSocket 연결 시도
  const connectWebSocket = useCallback(() => {
    if (usePolling()) {
      startPolling();
      return;
    }

    try {
      // WebSocket URL 구성 (실제 환경에서는 환경변수 사용)
      const wsUrl = process.env.NODE_ENV === 'production'
        ? 'wss://your-backend-domain.com/ws/news-updates'
        : 'ws://localhost:8000/ws/news-updates';

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket 연결됨');
        setIsConnected(true);
        setRetryCount(0);

        // 관심 카테고리 구독
        if (categories.length > 0) {
          ws.send(JSON.stringify({
            type: 'subscribe_categories',
            categories: categories
          }));
        }
      };

      ws.onmessage = (event) => {
        try {
          const update: RealTimeUpdate = JSON.parse(event.data);

          setUpdates(prev => [update, ...prev.slice(0, 19)]); // 최근 20개만 유지
          setLastUpdate(new Date().toISOString());

          if (update.type === 'new_article') {
            setNewArticlesCount(prev => prev + 1);
            if (onNewArticle) {
              onNewArticle(update.data);
            }
          }
        } catch (error) {
          console.error('WebSocket 메시지 파싱 오류:', error);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket 연결 종료');
        setIsConnected(false);

        // 자동 재연결 (최대 5회)
        if (retryCount < 5) {
          setTimeout(() => {
            setRetryCount(prev => prev + 1);
            connectWebSocket();
          }, Math.pow(2, retryCount) * 1000); // 지수 백오프
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket 오류:', error);
        setIsConnected(false);
      };

      return () => {
        ws.close();
      };
    } catch (error) {
      console.error('WebSocket 연결 실패:', error);
      // WebSocket 실패 시 폴링으로 대체
      startPolling();
    }
  }, [categories, retryCount, startPolling, usePolling, onNewArticle]);

  // 컴포넌트 마운트 시 연결 시작
  useEffect(() => {
    const cleanup = connectWebSocket();
    return cleanup;
  }, [connectWebSocket]);

  // 수동 새로고침
  const handleRefresh = async () => {
    try {
      const latestNews = await newsService.getLatestNews(10);
      if (latestNews && latestNews.length > 0) {
        const update: RealTimeUpdate = {
          type: 'category_update',
          data: { message: '뉴스 목록이 새로고침되었습니다', count: latestNews.length },
          timestamp: new Date().toISOString()
        };
        setUpdates(prev => [update, ...prev.slice(0, 19)]);
        setLastUpdate(new Date().toISOString());
      }
    } catch (error) {
      console.error('수동 새로고침 실패:', error);
    }
  };

  // 알림 카운트 리셋
  const resetNotificationCount = () => {
    setNewArticlesCount(0);
  };

  // 업데이트 타입별 아이콘 및 메시지
  const getUpdateDisplay = (update: RealTimeUpdate) => {
    switch (update.type) {
      case 'new_article':
        return {
          icon: '📰',
          message: `새 기사: ${update.data.title}`,
          link: `/news/${update.data._id || update.data.id}`
        };
      case 'category_update':
        return {
          icon: '🏷️',
          message: update.data.message || '카테고리가 업데이트되었습니다',
          link: null
        };
      case 'trending_change':
        return {
          icon: '📈',
          message: '인기 뉴스가 변경되었습니다',
          link: null
        };
      default:
        return {
          icon: '📢',
          message: '새 업데이트가 있습니다',
          link: null
        };
    }
  };

  return (
    <Card className="mb-6">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-lg">
          <div className="flex items-center space-x-2">
            <Bell className="w-5 h-5" />
            <span>실시간 업데이트</span>
            {newArticlesCount > 0 && (
              <Badge variant="destructive" className="text-xs">
                {newArticlesCount}개 신규
              </Badge>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              className="p-1"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
            <div className="flex items-center space-x-1">
              {isConnected ? (
                <Wifi className="w-4 h-4 text-green-500" />
              ) : (
                <WifiOff className="w-4 h-4 text-red-500" />
              )}
              <span className={`text-xs ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
                {isConnected ? '연결됨' : '연결 안됨'}
              </span>
            </div>
          </div>
        </CardTitle>
      </CardHeader>

      <CardContent className="pt-0">
        {!isConnected && retryCount >= 3 && (
          <Alert className="mb-4">
            <AlertDescription>
              실시간 연결이 끊어졌습니다. 수동으로 새로고침해주세요.
              <Button
                variant="outline"
                size="sm"
                onClick={connectWebSocket}
                className="ml-2"
              >
                다시 연결
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {lastUpdate && (
          <div className="text-xs text-gray-500 mb-3">
            마지막 업데이트: {new Date(lastUpdate).toLocaleTimeString()}
          </div>
        )}

        {newArticlesCount > 0 && (
          <div className="mb-3">
            <Button
              variant="outline"
              size="sm"
              onClick={resetNotificationCount}
              className="text-xs"
            >
              {newArticlesCount}개 신규 알림 확인
            </Button>
          </div>
        )}

        <div className="space-y-2 max-h-64 overflow-y-auto">
          {updates.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-4">
              아직 업데이트가 없습니다
            </p>
          ) : (
            updates.map((update, index) => {
              const display = getUpdateDisplay(update);

              return (
                <div
                  key={index}
                  className="flex items-start space-x-2 p-2 rounded-lg hover:bg-gray-50 text-sm"
                >
                  <span className="text-lg">{display.icon}</span>
                  <div className="flex-1 min-w-0">
                    {display.link ? (
                      <Link
                        href={display.link}
                        className="text-blue-600 hover:text-blue-800 font-medium line-clamp-2"
                      >
                        {display.message}
                      </Link>
                    ) : (
                      <p className="text-gray-700 line-clamp-2">{display.message}</p>
                    )}
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(update.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}
