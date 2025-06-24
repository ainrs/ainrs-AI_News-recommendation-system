'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAuth } from '@/lib/auth/authContext';
import EmailVerification from './EmailVerification';
import { checkBackendConnection } from '@/lib/api/client';
import { Loader2 } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function SignupForm() {
  const { register, error, isLoading, getPendingVerificationEmail } = useAuth();
  const router = useRouter();

  // 회원가입 폼 상태
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  // 이메일 인증 상태
  const [showEmailVerification, setShowEmailVerification] = useState(false);

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

  // 인증이 필요한 이메일이 있는지 확인
  useEffect(() => {
    const pendingEmail = getPendingVerificationEmail();
    if (pendingEmail) {
      setShowEmailVerification(true);
    }
  }, [getPendingVerificationEmail]);

  // 회원가입 핸들러
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!username || !email || !password) {
      setFormError('모든 필드를 입력해주세요');
      return;
    }

    if (password !== passwordConfirm) {
      setFormError('비밀번호가 일치하지 않습니다');
      return;
    }

    if (password.length < 6) {
      setFormError('비밀번호는 6자리 이상이어야 합니다');
      return;
    }

    if (!backendStatus.connected) {
      setFormError('백엔드 서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.');
      return;
    }

    const success = await register(username, email, password);
    if (success) {
      const pendingEmail = getPendingVerificationEmail();
      if (pendingEmail) {
        // 이메일 인증이 필요한 경우 인증 화면으로 전환
        setShowEmailVerification(true);
      } else {
        // 이메일 인증이 필요 없는 경우 바로 홈으로 이동
        router.push('/');
      }
    }
  };

  // 이메일 인증 성공 핸들러
  const handleVerificationSuccess = () => {
    setShowEmailVerification(false);
    router.push('/'); // 인증 성공 시 홈으로 이동
  };

  // 이메일 인증 화면이 표시되어야 하는 경우
  if (showEmailVerification) {
    return <EmailVerification onVerificationSuccess={handleVerificationSuccess} />;
  }

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle className="text-center text-2xl">회원가입</CardTitle>
        <CardDescription className="text-center">
          새 계정을 만들어 맞춤형 AI 뉴스를 경험하세요
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

        {/* 회원가입 폼 */}
        <form onSubmit={handleRegister} className="space-y-4">
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
            <Label htmlFor="email">이메일</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="이메일을 입력하세요"
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
              placeholder="비밀번호를 입력하세요 (6자리 이상)"
              disabled={isLoading || backendStatus.checking || !backendStatus.connected}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password-confirm">비밀번호 확인</Label>
            <Input
              id="password-confirm"
              type="password"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              placeholder="비밀번호를 다시 입력하세요"
              disabled={isLoading || backendStatus.checking || !backendStatus.connected}
            />
          </div>
          <Button
            type="submit"
            className="w-full bg-[hsl(var(--variety-blue))]"
            disabled={isLoading || backendStatus.checking || !backendStatus.connected}
          >
            {isLoading ? '계정 생성 중...' : '계정 생성'}
          </Button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-muted-foreground">
            이미 계정이 있으신가요?{' '}
            <Link href="/login" className="text-[hsl(var(--variety-blue))] hover:underline font-medium">
              로그인
            </Link>
          </p>
        </div>
      </CardContent>
      <CardFooter className="text-center text-sm text-muted-foreground">
        계정을 생성하면 이용약관과 개인정보처리방침에 동의하는 것으로 간주됩니다.
      </CardFooter>
    </Card>
  );
}
