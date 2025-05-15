'use client';

import Link from 'next/link';

export default function Footer() {
  return (
    <footer className="bg-[hsl(var(--variety-gray))] text-white">
      <div className="variety-container py-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <h2 className="text-xl font-bold mb-4">NVIPBION.AI</h2>
            <p className="text-sm opacity-80 mb-4">최신 인공지능 트렌드와 소식을 전달하는 AI 전문 미디어입니다.</p>
            <div className="flex space-x-4">
              <Link href="https://twitter.com" className="opacity-80 hover:opacity-100">
                <span className="sr-only">Twitter</span>
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 4s-.7 2.1-2 3.4c1.6 10-9.4 17.3-18 11.6 2.2.1 4.4-.6 6-2C3 15.5.5 9.6 3 5c2.2 2.6 5.6 4.1 9 4-.9-4.2 4-6.6 7-3.8 1.1 0 3-1.2 3-1.2z" />
                </svg>
              </Link>
              <Link href="https://facebook.com" className="opacity-80 hover:opacity-100">
                <span className="sr-only">Facebook</span>
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />
                </svg>
              </Link>
              <Link href="https://instagram.com" className="opacity-80 hover:opacity-100">
                <span className="sr-only">Instagram</span>
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect width="20" height="20" x="2" y="2" rx="5" ry="5" />
                  <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
                  <line x1="17.5" x2="17.51" y1="6.5" y2="6.5" />
                </svg>
              </Link>
            </div>
          </div>
          <div>
            <h3 className="font-bold mb-4">섹션</h3>
            <ul className="space-y-2 text-sm">
              <li><Link href="/ai" className="opacity-80 hover:opacity-100">인공지능</Link></li>
              <li><Link href="/bigdata" className="opacity-80 hover:opacity-100">빅데이터</Link></li>
              <li><Link href="/cloud" className="opacity-80 hover:opacity-100">클라우드</Link></li>
              <li><Link href="/robots" className="opacity-80 hover:opacity-100">로봇</Link></li>
              <li><Link href="/blockchain" className="opacity-80 hover:opacity-100">블록체인</Link></li>
              <li><Link href="/metaverse" className="opacity-80 hover:opacity-100">메타버스</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="font-bold mb-4">회사</h3>
            <ul className="space-y-2 text-sm">
              <li><Link href="/about" className="opacity-80 hover:opacity-100">소개</Link></li>
              <li><Link href="/terms" className="opacity-80 hover:opacity-100">이용약관</Link></li>
              <li><Link href="/privacy" className="opacity-80 hover:opacity-100">개인정보처리방침</Link></li>
              <li><Link href="/partnership" className="opacity-80 hover:opacity-100">제휴문의</Link></li>
              <li><Link href="/advertise" className="opacity-80 hover:opacity-100">광고문의</Link></li>
              <li><Link href="/contact" className="opacity-80 hover:opacity-100">고객센터</Link></li>
            </ul>
          </div>
        </div>
        <div className="mt-8 pt-8 border-t border-white/20 text-sm opacity-60">
          <p>© 2025 NVIPBION.AI All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
