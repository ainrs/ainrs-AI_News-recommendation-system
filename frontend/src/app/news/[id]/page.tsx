import type { Metadata } from 'next';
import NewsDetailPage from '@/components/NewsDetailPage';

interface NewsPageParams {
  params: {
    id: string;
  };
}

export async function generateMetadata({ params }: NewsPageParams): Promise<Metadata> {
  // 실제 환경에서는 API로 뉴스 제목을 가져옵니다.
  // 여기서는 간단히 ID를 사용합니다.
  return {
    title: `뉴스 - ${params.id} | 버라이어티.AI`,
    description: '버라이어티.AI 뉴스 상세 정보',
  };
}

export default function NewsPage({ params }: NewsPageParams) {
  return <NewsDetailPage newsId={params.id} />;
}
