'use client';

import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAuth } from '@/lib/auth/authContext';
import { useRouter } from 'next/navigation';

interface EmailVerificationProps {
  onVerificationSuccess?: () => void;
  redirectPath?: string;
}

export default function EmailVerification({ onVerificationSuccess, redirectPath = '/login' }: EmailVerificationProps) {
  const { isLoading, error, verifyEmailCode, getPendingVerificationEmail, requestEmailVerification } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [verificationCode, setVerificationCode] = useState<string[]>(Array(6).fill(''));
  const [formError, setFormError] = useState<string | null>(null);
  const [resendCooldown, setResendCooldown] = useState(0);
  const inputRefs = useRef<(HTMLInputElement | null)[]>(Array(6).fill(null));

  // 이메일 인증이 필요한 이메일 주소를 가져옵니다
  useEffect(() => {
    const pendingEmail = getPendingVerificationEmail();
    if (pendingEmail) {
      setEmail(pendingEmail);
    } else {
      // 보류 중인 인증이 없으면 리다이렉트
      router.push(redirectPath);
    }
  }, [getPendingVerificationEmail, redirectPath, router]);

  // 재전송 쿨다운 타이머
  useEffect(() => {
    if (resendCooldown <= 0) return;

    const timer = setTimeout(() => {
      setResendCooldown(prev => prev - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [resendCooldown]);

  // 인증 코드 입력 처리
  const handleCodeChange = (index: number, value: string) => {
    // 숫자만 입력 가능
    if (value && !/^\d*$/.test(value)) return;

    const newCode = [...verificationCode];
    // 백스페이스 또는 입력된 문자로 업데이트
    newCode[index] = value;
    setVerificationCode(newCode);

    // 자동 포커스 이동
    if (value && index < 5) {
      // 다음 입력란으로 포커스 이동
      inputRefs.current[index + 1]?.focus();
    }
  };

  // 특수 키 처리 (백스페이스, 화살표 등)
  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !verificationCode[index] && index > 0) {
      // 현재 입력란이 비어있고 백스페이스 누르면 이전 입력란으로 이동
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowLeft' && index > 0) {
      // 왼쪽 화살표 누르면 이전 입력란으로 이동
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < 5) {
      // 오른쪽 화살표 누르면 다음 입력란으로 이동
      inputRefs.current[index + 1]?.focus();
    }
  };

  // 전체 코드 입력 확인
  const isCodeComplete = verificationCode.every(c => c !== '');

  // 인증 코드 검증
  const handleVerify = async () => {
    if (!email) return;

    if (!isCodeComplete) {
      setFormError('인증 코드를 모두 입력해주세요');
      return;
    }

    setFormError(null);
    const code = verificationCode.join('');

    const success = await verifyEmailCode(email, code);
    if (success) {
      if (onVerificationSuccess) {
        onVerificationSuccess();
      } else {
        router.push(redirectPath);
      }
    }
  };

  // 인증 코드 재전송
  const handleResendCode = async () => {
    if (!email || resendCooldown > 0) return;

    const success = await requestEmailVerification(email);
    if (success) {
      setResendCooldown(60); // 1분 쿨다운
      setVerificationCode(Array(6).fill(''));
      setFormError(null);
    }
  };

  // 로그인 페이지로 돌아가기
  const handleBackToLogin = () => {
    localStorage.removeItem('email_verification_pending');
    router.push(redirectPath);
  };

  if (!email) {
    return <div className="p-6 text-center">Loading...</div>;
  }

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle className="text-center text-2xl">Verify your email</CardTitle>
        <CardDescription className="text-center">
          Enter the code sent to {email}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* 오류 표시 */}
        {(error || formError) && (
          <Alert variant="destructive" className="mb-4">
            <AlertDescription>{formError || error}</AlertDescription>
          </Alert>
        )}

        {/* 인증 코드 입력 필드 */}
        <div className="flex justify-center space-x-2 mb-6">
          {verificationCode.map((digit, index) => (
            <Input
              key={index}
              ref={el => inputRefs.current[index] = el}
              className="w-12 h-12 text-center text-lg"
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={digit}
              onChange={e => handleCodeChange(index, e.target.value)}
              onKeyDown={e => handleKeyDown(index, e)}
              disabled={isLoading}
            />
          ))}
        </div>

        {/* 인증 버튼 */}
        <Button
          onClick={handleVerify}
          className="w-full"
          disabled={!isCodeComplete || isLoading}
        >
          {isLoading ? '인증 중...' : '인증하기'}
        </Button>

        {/* 재전송 버튼 */}
        <div className="mt-4 text-center">
          <Button
            variant="link"
            onClick={handleResendCode}
            disabled={resendCooldown > 0 || isLoading}
          >
            {resendCooldown > 0 ? `재전송 (${resendCooldown}초)` : '인증 코드 재전송'}
          </Button>
        </div>
      </CardContent>
      <CardFooter className="flex justify-center">
        <Button variant="ghost" onClick={handleBackToLogin}>
          ← Back to sign-in
        </Button>
      </CardFooter>
    </Card>
  );
}
