'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import {
  CircleCheck,
  CircleX,
  AlertTriangle,
  ThumbsUp,
  ThumbsDown,
  Scale,
  Info
} from 'lucide-react';

interface NewsAIAnalysisProps {
  newsId: string;
  trustScore?: number;
  sentimentScore?: number;
  sentiment?: {
    label: string;
    positive: number;
    negative: number;
    neutral: number;
  };
  keyPhrases?: string[];
  loading?: boolean;
}

export default function NewsAIAnalysis({
  newsId,
  trustScore,
  sentimentScore,
  sentiment = { label: 'neutral', positive: 0, negative: 0, neutral: 0 },
  keyPhrases = [],
  loading = false
}: NewsAIAnalysisProps) {

  // 신뢰도 점수를 기반으로 레벨 결정
  const getTrustLevel = (score?: number) => {
    if (score === undefined) return { text: '알 수 없음', color: 'gray', icon: Info };
    if (score >= 0.8) return { text: '매우 높음', color: 'green', icon: CircleCheck };
    if (score >= 0.6) return { text: '높음', color: 'blue', icon: CircleCheck };
    if (score >= 0.4) return { text: '보통', color: 'yellow', icon: AlertTriangle };
    if (score >= 0.2) return { text: '낮음', color: 'orange', icon: AlertTriangle };
    return { text: '매우 낮음', color: 'red', icon: CircleX };
  };

  // 감정 분석 점수를 기반으로 레벨 결정
  const getSentimentLevel = (score?: number) => {
    if (score === undefined) return { text: '중립', color: 'gray', icon: Scale };
    if (score >= 0.6) return { text: '긍정적', color: 'green', icon: ThumbsUp };
    if (score <= -0.6) return { text: '부정적', color: 'red', icon: ThumbsDown };
    return { text: '중립', color: 'blue', icon: Scale };
  };

  const trustLevel = getTrustLevel(trustScore);
  const sentimentLevel = getSentimentLevel(sentimentScore);

  if (loading) {
    return (
      <Card className="mb-6">
        <CardHeader>
          <CardTitle><Skeleton className="h-8 w-40" /></CardTitle>
          <CardDescription><Skeleton className="h-4 w-60" /></CardDescription>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-32 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>AI 뉴스 분석</CardTitle>
        <CardDescription>이 뉴스에 대한 AI 분석 결과입니다</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="trustworthiness">
          <TabsList className="mb-4">
            <TabsTrigger value="trustworthiness">신뢰도</TabsTrigger>
            <TabsTrigger value="sentiment">감정 분석</TabsTrigger>
            <TabsTrigger value="keywords">키워드</TabsTrigger>
          </TabsList>

          {/* 신뢰도 탭 */}
          <TabsContent value="trustworthiness" className="space-y-4">
            <div className="flex items-center">
              <div className="mr-3">
                {trustLevel.icon && (
                  <trustLevel.icon
                    className={`h-10 w-10 text-${trustLevel.color}-500`}
                  />
                )}
              </div>
              <div>
                <div className="font-semibold text-lg">신뢰도: {trustLevel.text}</div>
                <div className="text-sm text-muted-foreground">
                  신뢰도 점수: {trustScore !== undefined ? `${(trustScore * 100).toFixed(1)}%` : '분석 중'}
                </div>
              </div>
            </div>

            <div className="mt-4 text-sm">
              <p>이 점수는 뉴스의 내용을 분석하여 신뢰성을 평가한 결과입니다.
              정보의 출처, 객관성, 정확성, 일관성 등을 고려합니다.</p>
            </div>

            <div className="w-full bg-gray-200 rounded-full h-2.5 mt-4">
              <div
                className={`bg-${trustLevel.color}-500 h-2.5 rounded-full`}
                style={{ width: `${(trustScore || 0) * 100}%` }}
              ></div>
            </div>
          </TabsContent>

          {/* 감정 분석 탭 */}
          <TabsContent value="sentiment" className="space-y-4">
            <div className="flex items-center">
              <div className="mr-3">
                {sentimentLevel.icon && (
                  <sentimentLevel.icon
                    className={`h-10 w-10 text-${sentimentLevel.color}-500`}
                  />
                )}
              </div>
              <div>
                <div className="font-semibold text-lg">감정 분석: {sentimentLevel.text}</div>
                <div className="text-sm text-muted-foreground">
                  감정 점수: {sentimentScore !== undefined ? sentimentScore.toFixed(2) : '분석 중'}
                </div>
              </div>
            </div>

            <div className="mt-4 text-sm">
              <p>이 점수는 뉴스의 어조와 표현을 분석하여 감정적 경향을 평가한 결과입니다.
              긍정, 부정, 중립적 표현의 비율을 나타냅니다.</p>
            </div>

            {sentiment && (
              <div className="grid grid-cols-3 gap-2 mt-4">
                <div className="bg-green-50 p-3 rounded-md text-center">
                  <div className="text-green-500 font-semibold">{(sentiment.positive * 100).toFixed(1)}%</div>
                  <div className="text-xs text-muted-foreground">긍정적</div>
                </div>
                <div className="bg-blue-50 p-3 rounded-md text-center">
                  <div className="text-blue-500 font-semibold">{(sentiment.neutral * 100).toFixed(1)}%</div>
                  <div className="text-xs text-muted-foreground">중립적</div>
                </div>
                <div className="bg-red-50 p-3 rounded-md text-center">
                  <div className="text-red-500 font-semibold">{(sentiment.negative * 100).toFixed(1)}%</div>
                  <div className="text-xs text-muted-foreground">부정적</div>
                </div>
              </div>
            )}
          </TabsContent>

          {/* 키워드 탭 */}
          <TabsContent value="keywords">
            {keyPhrases && keyPhrases.length > 0 ? (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  AI가 분석한 이 뉴스의 주요 키워드입니다
                </p>
                <div className="flex flex-wrap gap-2">
                  {keyPhrases.map((phrase, index) => (
                    <span
                      key={index}
                      className="inline-block px-3 py-1 bg-slate-100 text-slate-800 rounded-full text-sm"
                    >
                      {phrase}
                    </span>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                키워드 분석 결과가 없거나 분석 중입니다
              </p>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
