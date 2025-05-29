'use client';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/lib/auth/authContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { apiClient } from '@/lib/api/client';
import type { Comment } from '@/lib/api/client';
import { format } from 'date-fns';
import { ko } from 'date-fns/locale';

interface NewsCommentsProps {
  newsId: string;
}

export default function NewsComments({ newsId }: NewsCommentsProps) {
  const { user, isAuthenticated } = useAuth();
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const commentInputRef = useRef<HTMLTextAreaElement>(null);

  // 댓글 불러오기
  useEffect(() => {
    if (newsId) {
      fetchComments();
    }
  }, [newsId]);

  const fetchComments = async () => {
    setLoading(true);
    setError(null);

    try {
      const commentsData = await apiClient.news.getComments(newsId);
      setComments(commentsData);
    } catch (err) {
      console.error('댓글을 불러오는 중 오류:', err);
      setError('댓글을 불러오는 중 오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  };

  // 댓글 작성
  const handleSubmitComment = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isAuthenticated || !user) {
      alert('댓글을 작성하려면 로그인이 필요합니다');
      return;
    }

    if (!newComment.trim()) return;

    setSubmitting(true);
    try {
      const comment = await apiClient.news.addComment(
        newsId,
        user.id,
        newComment
      );

      // 새 댓글 목록에 추가
      setComments(prev => [comment, ...prev]);
      setNewComment('');

      // AI 추천 시스템에 사용자 활동 기록
      await apiClient.users.recordInteraction(user.id, newsId, 'comment');
    } catch (err) {
      console.error('댓글 작성 중 오류:', err);
      alert('댓글 작성 중 오류가 발생했습니다');
    } finally {
      setSubmitting(false);
    }
  };

  // 댓글 포커스
  const focusCommentInput = () => {
    if (commentInputRef.current) {
      commentInputRef.current.focus();
    }
  };

  // 날짜 포맷
  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'yyyy년 M월 d일 HH:mm', { locale: ko });
    } catch (error) {
      return dateString;
    }
  };

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-xl font-bold mb-4">댓글 {comments.length}개</h3>

      {/* 댓글 작성 폼 */}
      {isAuthenticated ? (
        <form onSubmit={handleSubmitComment} className="mb-6">
          <div className="flex gap-3">
            <Avatar className="h-10 w-10">
              <AvatarImage src={`https://ui-avatars.com/api/?name=${user?.username}&background=random`} />
              <AvatarFallback>{user?.username?.substring(0, 2).toUpperCase()}</AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <Textarea
                ref={commentInputRef}
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="댓글을 작성해주세요"
                className="w-full mb-2"
              />
              <div className="flex justify-end">
                <Button
                  type="submit"
                  disabled={submitting || !newComment.trim()}
                >
                  {submitting ? '작성 중...' : '댓글 작성'}
                </Button>
              </div>
            </div>
          </div>
        </form>
      ) : (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg text-center">
          <p>댓글을 작성하려면 로그인이 필요합니다</p>
          <Button className="mt-2" onClick={() => window.location.href = '/'}>
            로그인하기
          </Button>
        </div>
      )}

      {/* 오류 메시지 */}
      {error && (
        <div className="bg-red-50 text-red-700 p-3 rounded-md mb-4">
          {error}
        </div>
      )}

      {/* 댓글 목록 */}
      {loading ? (
        <div className="text-center py-4">
          <p>댓글을 불러오는 중...</p>
        </div>
      ) : comments.length === 0 ? (
        <div className="text-center py-4 text-gray-500">
          <p>아직 댓글이 없습니다. 첫 댓글을 작성해보세요!</p>
        </div>
      ) : (
        <div className="space-y-4">
          {comments.map((comment) => (
            <div key={comment.id} className="border-b pb-4 last:border-0">
              <div className="flex items-start gap-3">
                <Avatar className="h-10 w-10">
                  <AvatarImage src={`https://ui-avatars.com/api/?name=${comment.userName}&background=random`} />
                  <AvatarFallback>{comment.userName.substring(0, 2).toUpperCase()}</AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium">{comment.userName}</span>
                    <span className="text-xs text-gray-500">{formatDate(comment.createdAt)}</span>
                  </div>
                  <p className="text-gray-800">{comment.content}</p>
                  <div className="flex items-center mt-2 text-xs text-gray-500">
                    <button className="hover:text-blue-600">좋아요 {comment.likes > 0 ? comment.likes : ''}</button>
                    <span className="mx-2">•</span>
                    <button className="hover:text-blue-600">답글</button>
                  </div>

                  {/* 대댓글이 있는 경우 */}
                  {comment.replies && comment.replies.length > 0 && (
                    <div className="mt-3 ml-6 space-y-3">
                      {comment.replies.map((reply) => (
                        <div key={reply.id} className="flex items-start gap-3">
                          <Avatar className="h-8 w-8">
                            <AvatarImage src={`https://ui-avatars.com/api/?name=${reply.userName}&background=random`} />
                            <AvatarFallback>{reply.userName.substring(0, 2).toUpperCase()}</AvatarFallback>
                          </Avatar>
                          <div>
                            <div className="flex items-center mb-1">
                              <span className="font-medium text-sm">{reply.userName}</span>
                              <span className="text-xs text-gray-500 ml-2">{formatDate(reply.createdAt)}</span>
                            </div>
                            <p className="text-gray-800 text-sm">{reply.content}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
