'use client';

import { Button } from '@/components/ui/button';

export default function SubscriptionPanel() {
  return (
    <section className="mb-8 bg-gradient-to-r from-blue-500 to-purple-600 p-6 rounded-lg text-white">
      <h2 className="text-xl font-bold mb-2">NVIPBION.AI 프리미엄</h2>
      <p className="mb-4">최신 AI 분석 보고서와 전문가 인사이트를 받아보세요.</p>
      <Button className="w-full bg-white text-blue-600 hover:bg-blue-50">구독하기</Button>
    </section>
  );
}
