'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAuth } from '@/lib/auth/authContext';
import EmailVerification from './EmailVerification';

interface LoginFormProps {
  onLoginSuccess?: () => void;
}

export default function LoginForm({ onLoginSuccess }: LoginFormProps) {
  // 인증 컨텍스트 사용
  const { login, register, error, isLoading, getPendingVerificationEmail } = useAuth();

  // 로그인 폼 상태
  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // 회원가입 폼 상태
  const [registerUsername, setRegisterUsername] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerPasswordConfirm, setRegisterPasswordConfirm] = useState('');

  // 폼 에러 상태
  const [formError, setFormError] = useState<string | null>(null);

  // 이메일 인증 상태
  const [showEmailVerification, setShowEmailVerification] = useState(false);

  // 인증이 필요한 이메일이 있는지 확인
  useEffect(() => {
    const pendingEmail = getPendingVerificationEmail();
    if (pendingEmail) {
      setShowEmailVerification(true);
    }
  }, [getPendingVerificationEmail]);

  // 로그인 핸들러
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!loginUsername || !loginPassword) {
      setFormError('사용자 이름과 비밀번호를 입력해주세요');
      return;
    }

    const success = await login(loginUsername, loginPassword);
    if (success && onLoginSuccess) {
      onLoginSuccess();
    }
  };

  // 회원가입 핸들러
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!registerUsername || !registerEmail || !registerPassword) {
      setFormError('모든 필드를 입력해주세요');
      return;
    }

    if (registerPassword !== registerPasswordConfirm) {
      setFormError('비밀번호가 일치하지 않습니다');
      return;
    }

    const success = await register(registerUsername, registerEmail, registerPassword);
    if (success) {
      const pendingEmail = getPendingVerificationEmail();
      if (pendingEmail) {
        // 이메일 인증이 필요한 경우 인증 화면으로 전환
        setShowEmailVerification(true);
      } else if (onLoginSuccess) {
        // 이메일 인증이 필요 없는 경우 바로 성공 처리
        onLoginSuccess();
      }
    }
  };

  // 이메일 인증 성공 핸들러
  const handleVerificationSuccess = () => {
    setShowEmailVerification(false);
    if (onLoginSuccess) {
      onLoginSuccess();
    }
  };

  // 이메일 인증 화면이 표시되어야 하는 경우
  if (showEmailVerification) {
    return <EmailVerification onVerificationSuccess={handleVerificationSuccess} />;
  }

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle className="text-center text-2xl">버라이어티.AI</CardTitle>
        <CardDescription className="text-center">
          로그인하여 맞춤형 AI 뉴스를 경험하세요
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="login">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="login">로그인</TabsTrigger>
            <TabsTrigger value="register">회원가입</TabsTrigger>
          </TabsList>

          {/* 오류 표시 */}
          {(error || formError) && (
            <Alert variant="destructive" className="mt-4">
              <AlertDescription>{formError || error}</AlertDescription>
            </Alert>
          )}

          {/* 로그인 폼 */}
          <TabsContent value="login">
            <form onSubmit={handleLogin} className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="username">사용자 이름</Label>
                <Input
                  id="username"
                  type="text"
                  value={loginUsername}
                  onChange={(e) => setLoginUsername(e.target.value)}
                  placeholder="사용자 이름을 입력하세요"
                  disabled={isLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">비밀번호</Label>
                <Input
                  id="password"
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="비밀번호를 입력하세요"
                  disabled={isLoading}
                />
              </div>
              <Button
                type="submit"
                className="w-full bg-[hsl(var(--variety-blue))]"
                disabled={isLoading}
              >
                {isLoading ? '로그인 중...' : '로그인'}
              </Button>
            </form>
          </TabsContent>

          {/* 회원가입 폼 */}
          <TabsContent value="register">
            <form onSubmit={handleRegister} className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="register-username">사용자 이름</Label>
                <Input
                  id="register-username"
                  type="text"
                  value={registerUsername}
                  onChange={(e) => setRegisterUsername(e.target.value)}
                  placeholder="사용자 이름을 입력하세요"
                  disabled={isLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="register-email">이메일</Label>
                <Input
                  id="register-email"
                  type="email"
                  value={registerEmail}
                  onChange={(e) => setRegisterEmail(e.target.value)}
                  placeholder="이메일을 입력하세요"
                  disabled={isLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="register-password">비밀번호</Label>
                <Input
                  id="register-password"
                  type="password"
                  value={registerPassword}
                  onChange={(e) => setRegisterPassword(e.target.value)}
                  placeholder="비밀번호를 입력하세요"
                  disabled={isLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="register-password-confirm">비밀번호 확인</Label>
                <Input
                  id="register-password-confirm"
                  type="password"
                  value={registerPasswordConfirm}
                  onChange={(e) => setRegisterPasswordConfirm(e.target.value)}
                  placeholder="비밀번호를 다시 입력하세요"
                  disabled={isLoading}
                />
              </div>
              <Button
                type="submit"
                className="w-full bg-[hsl(var(--variety-blue))]"
                disabled={isLoading}
              >
                {isLoading ? '계정 생성 중...' : '계정 생성'}
              </Button>
            </form>
          </TabsContent>
        </Tabs>
      </CardContent>
      <CardFooter className="text-center text-sm text-muted-foreground">
        버라이어티.AI에 로그인하면 최신 AI 기술로 맞춤화된 뉴스를 제공받을 수 있습니다.
      </CardFooter>
    </Card>
  );
}
