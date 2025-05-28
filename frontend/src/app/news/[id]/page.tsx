import type { Metadata } from 'next';
import NewsDetailPage from '@/components/NewsDetailPage';
import Header from '@/components/Header';
import MainNavigation from '@/components/MainNavigation';
import Footer from '@/components/Footer';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

interface NewsPageParams {
  params: Promise<{
    id: string;
  }>;
}

// 이 함수는 서버에서 실행되며 뉴스 데이터를 가져옵니다
async function getNewsData(id: string) {
  try {
    // 서버 환경에서 API 호출
    // 참고: 실제 환경에서 API_BASE_URL 환경 변수 설정 필요
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    const res = await fetch(`${API_BASE_URL}/api/v1/news/${id}`, {
      // 캐시 전략 설정 (선택 사항)
      next: { revalidate: 60 } // 60초마다 재검증
    });

    if (!res.ok) {
      throw new Error(`News API returned ${res.status}`);
    }

    return await res.json();
  } catch (error) {
    console.error(`Error fetching news data for ID ${id}:`, error);
    return null;
  }
}

export async function generateMetadata({ params }: NewsPageParams): Promise<Metadata> {
  // 기본 메타데이터
  let title = `뉴스 | 버라이어티.AI`;
  let description = '버라이어티.AI 뉴스 상세 정보';

  // params를 await로 접근
  const { id } = await params;

  // ID 유효성 검사를 비동기 함수 내에서 처리
  if (!id || !isValidId(id)) {
    return {
      title: '잘못된 뉴스 ID | 버라이어티.AI',
      description: '요청하신 뉴스를 찾을 수 없습니다.'
    };
  }

  try {
    // 서버 측에서 뉴스 데이터 가져오기
    const newsData = await getNewsData(id);

    if (newsData) {
      title = `${newsData.title} | 버라이어티.AI`;
      description = newsData.summary || newsData.content?.substring(0, 150) || `${newsData.title} 관련 뉴스`;
    }
  } catch (error) {
    console.error('메타데이터 생성 중 오류:', error);
  }

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: 'article',
      url: `https://variety-ai-news.com/news/${id}`,
    },
  };
}

// ID가 유효한지 확인하는 함수
function isValidId(id: string): boolean {
  // ID가 undefined, null, 빈 문자열이 아니고 'undefined'가 아닌지 확인
  return (
    id !== undefined &&
    id !== null &&
    id !== '' &&
    id !== 'undefined' &&
    id.length >= 4
  );
}

export default async function NewsPage({ params }: NewsPageParams) {
  // params를 await로 접근
  const { id } = await params;

  // URL 파라미터 유효성 검사
  if (!isValidId(id)) {
    return (
      <div className="min-h-screen flex flex-col">
        <Header />
        <MainNavigation />
        <main className="flex-grow bg-background flex items-center justify-center">
          <Card className="w-full max-w-lg mx-auto">
            <CardContent className="p-6 text-center">
              <h1 className="text-2xl font-bold mb-2">잘못된 뉴스 ID</h1>
              <p className="text-gray-600 mb-4">요청하신 뉴스를 찾을 수 없습니다.</p>
              <Button asChild>
                <a href="/">홈으로 돌아가기</a>
              </Button>
            </CardContent>
          </Card>
        </main>
        <Footer />
      </div>
    );
  }

  // 서버 측에서 뉴스 데이터 가져오기 시도 (선택 사항)
  // const newsData = await getNewsData(id);

  // 뉴스 상세 페이지 컴포넌트에 데이터 전달
  // NewsDetailPage는 여전히 클라이언트 컴포넌트로, 자체적으로 데이터를 가져올 수도 있음
  return <NewsDetailPage newsId={id} />;
}
