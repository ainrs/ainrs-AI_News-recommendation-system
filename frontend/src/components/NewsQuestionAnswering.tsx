'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { apiClient } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/authContext';

interface NewsQuestionAnsweringProps {
  newsId: string;
}

export default function NewsQuestionAnswering({ newsId }: NewsQuestionAnsweringProps) {
  const { isAuthenticated } = useAuth();
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<string | null>(null);
  const [history, setHistory] = useState<Array<{ question: string; answer: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 질문 제출 처리
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!question.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.ai.askQuestionAboutNews(newsId, question);

      // 새 질문과 답변을 기록에 추가
      setHistory([...history, { question, answer: response.answer }]);

      // 응답 저장 및 입력 필드 초기화
      setAnswer(response.answer);
      setQuestion('');
    } catch (err) {
      console.error('질문 처리 중 오류:', err);
      setError('질문에 답변하는 도중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  };

  const suggestedQuestions = [
    '이 뉴스의 핵심 내용은 무엇인가요?',
    '이 기술의 주요 장점은 무엇인가요?',
    '이 내용이 미래에 미칠 영향은 무엇인가요?',
    '이 뉴스에서 가장 중요한 통계는 무엇인가요?'
  ];

  const handleSuggestedQuestion = (q: string) => {
    setQuestion(q);
  };

  if (!isAuthenticated) {
    return (
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>AI에게 질문하기</CardTitle>
          <CardDescription>뉴스 내용에 대해 질문하고 AI의 답변을 받아보세요</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-4">
            <p className="text-muted-foreground mb-4">
              이 기능을 사용하려면 로그인이 필요합니다
            </p>
            <Button variant="outline" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
              로그인하기
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>AI에게 질문하기</CardTitle>
        <CardDescription>뉴스 내용에 대해 궁금한 점을 AI에게 물어보세요</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 이전 질문/답변 기록 */}
        {history.length > 0 && (
          <div className="space-y-4 mb-4">
            {history.map((item, index) => (
              <div key={index} className="space-y-2">
                <div className="bg-muted p-3 rounded-md">
                  <p className="font-medium">Q: {item.question}</p>
                </div>
                <div className="bg-blue-50 p-3 rounded-md">
                  <p className="text-blue-800">A: {item.answer}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 에러 메시지 */}
        {error && (
          <div className="bg-red-50 text-red-600 p-3 rounded-md">
            {error}
          </div>
        )}

        {/* 질문 입력 폼 */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Textarea
              placeholder="질문을 입력하세요..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="min-h-[100px]"
              disabled={loading}
            />
          </div>

          <Button type="submit" disabled={loading || !question.trim()}>
            {loading ? '처리 중...' : '질문하기'}
          </Button>
        </form>

        {/* 추천 질문 */}
        {history.length === 0 && (
          <div className="mt-4">
            <p className="text-sm text-muted-foreground mb-2">추천 질문:</p>
            <div className="flex flex-wrap gap-2">
              {suggestedQuestions.map((q, idx) => (
                <Button
                  key={idx}
                  variant="outline"
                  size="sm"
                  onClick={() => handleSuggestedQuestion(q)}
                  className="text-xs"
                >
                  {q}
                </Button>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
