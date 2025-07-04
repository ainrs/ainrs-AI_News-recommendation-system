'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAuth } from '@/lib/auth/authContext';
import { checkBackendConnection } from '@/lib/api/client';
import { Loader2 } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function LoginForm() {
  const { login, error, isLoading } = useAuth();
  const router = useRouter();

  // 로그인 폼 상태
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  // 백엔드 연결 상태
  const [backendStatus, setBackendStatus] = useState<{
    connected: boolean;
    message?: string;
    checking: boolean;
  }>({
    connected: true,
    checking: true
  });

  // 백엔드 연결 상태 확인
  useEffect(() => {
    const checkConnection = async () => {
      setBackendStatus(prev => ({ ...prev, checking: true }));
      try {
        const status = await checkBackendConnection();
        setBackendStatus({
          connected: status.connected,
          message: status.message,
          checking: false
        });
      } catch (error) {
        setBackendStatus({
          connected: false,
          message: '백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.',
          checking: false
        });
      }
    };

    checkConnection();
  }, []);

  // 로그인 핸들러
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!username || !password) {
      setFormError('사용자 이름과 비밀번호를 입력해주세요');
      return;
    }

    if (!backendStatus.connected) {
      setFormError('백엔드 서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.');
      return;
    }

    const success = await login(username, password);
    if (success) {
      router.push('/'); // 로그인 성공 시 홈으로 이동
    }
  };

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle className="text-center text-2xl">로그인</CardTitle>
        <CardDescription className="text-center">
          계정에 로그인하여 맞춤형 AI 뉴스를 경험하세요
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* 백엔드 연결 상태 표시 */}
        {backendStatus.checking && (
          <Alert className="mb-4 flex items-center gap-2">
            <Loader2 className="animate-spin w-4 h-4 mr-2" />
            <AlertDescription>서버 연결 상태 확인 중...</AlertDescription>
          </Alert>
        )}
        {!backendStatus.checking && !backendStatus.connected && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>
              {backendStatus.message ||
                '백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.'}
            </AlertDescription>
          </Alert>
        )}

        {/* 오류 표시 */}
        {(error || formError) && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{formError || error}</AlertDescription>
          </Alert>
        )}

        {/* 로그인 폼 */}
        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="username">사용자 이름</Label>
            <Input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="사용자 이름을 입력하세요"
              disabled={isLoading || backendStatus.checking || !backendStatus.connected}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">비밀번호</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="비밀번호를 입력하세요"
              disabled={isLoading || backendStatus.checking || !backendStatus.connected}
            />
          </div>
          <Button
            type="submit"
            className="w-full bg-[hsl(var(--variety-blue))]"
            disabled={isLoading || backendStatus.checking || !backendStatus.connected}
          >
            {isLoading ? '로그인 중...' : '로그인'}
          </Button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-muted-foreground">
            계정이 없으신가요?{' '}
            <Link href="/signup" className="text-[hsl(var(--variety-blue))] hover:underline font-medium">
              회원가입
            </Link>
          </p>
        </div>
      </CardContent>
      <CardFooter className="text-center text-sm text-muted-foreground">
        버라이어티.AI에 로그인하면 최신 AI 기술로 맞춤화된 뉴스를 제공받을 수 있습니다.
      </CardFooter>
    </Card>
  );
}
