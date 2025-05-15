'use client';

import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';

interface AITerm {
  id: string;
  term: string;
  definition: string;
}

export default function TerminologyPanel() {
  // 모의 AI 용어 데이터
  const terms: AITerm[] = [
    {
      id: '1',
      term: '어텐션 메커니즘 (Attention Mechanism)',
      definition: '딥러닝 모델이 입력 시퀀스의 특정 부분에 집중할 수 있게 하는 기술입니다.'
    },
    {
      id: '2',
      term: '트랜스포머 (Transformer)',
      definition: '자연어 처리를 위한 신경망 아키텍처로, 어텐션 메커니즘을 핵심 구성 요소로 활용합니다.'
    },
    {
      id: '3',
      term: '임베딩 (Embedding)',
      definition: '단어나 개체를 벡터 공간에 매핑하는 기술로, AI 모델이 텍스트를 이해하는 데 사용됩니다.'
    },
  ];

  return (
    <section className="mb-8 bg-white p-4 rounded-lg border">
      <h2 className="section-heading">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[hsl(var(--variety-blue))]">
          <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
        </svg>
        AI 용어 사전
      </h2>
      <div className="space-y-3">
        {terms.map((term, index) => (
          <div key={term.id}>
            <h3 className="font-medium text-[hsl(var(--variety-blue))]">{term.term}</h3>
            <p className="text-sm">{term.definition}</p>
            {index < terms.length - 1 && <Separator className="my-2" />}
          </div>
        ))}
      </div>
      <div className="mt-4">
        <Button variant="outline" size="sm" className="w-full">더 보기</Button>
      </div>
    </section>
  );
}
