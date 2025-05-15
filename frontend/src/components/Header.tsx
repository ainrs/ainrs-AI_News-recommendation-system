'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuth } from '@/lib/auth/authContext';
import { useRouter } from 'next/navigation';

export default function Header() {
  const { user, isAuthenticated, logout } = useAuth();
  const router = useRouter();

  // 메인 페이지에서 로그인 폼 상태 설정
  const handleLoginClick = () => {
    // 로컬 스토리지를 사용하여 상태 공유
    if (typeof window !== 'undefined') {
      localStorage.setItem('variety_ai_show_login', 'true');
      window.location.href = '/'; // 페이지 새로고침하여 설정 적용
    }
  };

  const handleLogoutClick = () => {
    logout();
    router.push('/');
  };

  return (
    <header className="bg-white border-b sticky top-0 z-10">
      <div className="variety-container py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/" className="text-2xl font-bold text-[hsl(var(--variety-blue))]">
              NVIPBION<span className="text-black">.AI</span>
            </Link>
            <div className="hidden md:flex items-center space-x-4">
              <Link href="/membership" className="nav-link">멤버십</Link>
              <Link href="/reports" className="nav-link">AI 리포트</Link>
              <Link href="/trends" className="nav-link">기술 동향</Link>
              <Link href="/startups" className="nav-link">스타트업</Link>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {isAuthenticated && user ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <div className="flex items-center gap-2 cursor-pointer">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src={`https://ui-avatars.com/api/?name=${user.username}&background=random`} />
                      <AvatarFallback>{user.username.substring(0, 2).toUpperCase()}</AvatarFallback>
                    </Avatar>
                    <span className="text-sm font-medium">{user.username}</span>
                  </div>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>내 계정</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link href="/profile">프로필 설정</Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/bookmarks">내 북마크</Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/history">읽은 기사</Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogoutClick}>
                    로그아웃
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <>
                <Button variant="ghost" size="sm" onClick={handleLoginClick}>로그인</Button>
                <Button size="sm" onClick={handleLoginClick}>회원가입</Button>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
