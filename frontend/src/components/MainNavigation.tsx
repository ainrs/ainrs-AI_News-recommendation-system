'use client';

import Link from 'next/link';

export default function MainNavigation() {
  return (
    <nav className="bg-[hsl(var(--variety-light-gray))] py-2">
      <div className="variety-container">
        <div className="flex items-center gap-4 overflow-x-auto pb-1 hide-scrollbar">
          <Link href="/" className="nav-link font-medium">홈</Link>
          <Link href="/ai" className="nav-link">인공지능</Link>
          <Link href="/bigdata" className="nav-link">빅데이터</Link>
          <Link href="/cloud" className="nav-link">클라우드</Link>
          <Link href="/robots" className="nav-link">로봇</Link>
          <Link href="/blockchain" className="nav-link">블록체인</Link>
          <Link href="/metaverse" className="nav-link">메타버스</Link>
          <Link href="/companies" className="nav-link">IT기업</Link>
          <Link href="/startups" className="nav-link">스타트업</Link>
          <Link href="/services" className="nav-link">AI서비스</Link>
          <Link href="/column" className="nav-link">칼럼</Link>
        </div>
      </div>
    </nav>
  );
}
