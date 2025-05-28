"use client";

import { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import Header from "@/components/Header";
import MainNavigation from "@/components/MainNavigation";
import Footer from "@/components/Footer";
import NewsSection from "@/components/NewsSection";
import TrendingNewsSection from "@/components/TrendingNewsSection";
import TerminologyPanel from "@/components/TerminologyPanel";
import SubscriptionPanel from "@/components/SubscriptionPanel";
import RecommendedNewsSection from "@/components/RecommendedNewsSection";
import RelatedNewsSection from "@/components/RelatedNewsSection";
import LoginForm from "@/components/LoginForm";
import { apiClient } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/authContext";
import { newsService } from "@/lib/api/newsService";

export default function Home() {
  const { user, isAuthenticated, isLoading } = useAuth();

  // 첫 번째 뉴스 아이템 ID 상태
  const [firstNewsId, setFirstNewsId] = useState<string>("");
  // 콜드 스타트 추천 뉴스 상태
  const [coldStartRecommendations, setColdStartRecommendations] = useState<any[]>([]);
  // 콜드 스타트 로딩 상태
  const [coldStartLoading, setColdStartLoading] = useState<boolean>(false);

  // 첫 번째 뉴스 아이템 ID 및 콜드 스타트 추천을 가져오기 위한 API 호출
  useEffect(() => {
    async function fetchInitialData() {
      try {
        // 콜드 스타트 추천 호출 상태 설정
        setColdStartLoading(true);

        // 병렬로 첫 번째 뉴스와 콜드 스타트 추천 요청
        const [newsItemsPromise, coldStartPromise] = await Promise.allSettled([
          // 첫 번째 뉴스 가져오기
          apiClient.news.getAll({ limit: 1 }),
          // 콜드 스타트 추천 가져오기
          newsService.getColdStartRecommendations(5)
        ]);

        // 첫 번째 뉴스 처리
        if (newsItemsPromise.status === 'fulfilled' && newsItemsPromise.value && newsItemsPromise.value.length > 0) {
          setFirstNewsId(newsItemsPromise.value[0]._id || newsItemsPromise.value[0].id || "");
        }

        // 콜드 스타트 추천 처리
        if (coldStartPromise.status === 'fulfilled' && coldStartPromise.value) {
          setColdStartRecommendations(coldStartPromise.value);
          console.log("콜드 스타트 추천 로드 완료:", coldStartPromise.value.length);
        } else {
          console.warn("콜드 스타트 추천 로드 실패:", coldStartPromise);
        }
      } catch (error) {
        console.error("초기 데이터를 가져오는 중 오류:", error);
      } finally {
        setColdStartLoading(false);
      }
    }

    fetchInitialData();
  }, []);

  // 로그인 폼 표시 여부 상태
  const [showLoginForm, setShowLoginForm] = useState(false);

  // 로컬 스토리지에서 로그인 폼 표시 여부 읽기
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const shouldShowLogin = localStorage.getItem('variety_ai_show_login') === 'true';
      setShowLoginForm(shouldShowLogin);

      // 상태를 읽은 후 리셋
      if (shouldShowLogin) {
        localStorage.removeItem('variety_ai_show_login');
      }
    }
  }, []);

  // 실제 로그인 폼 표시 로직
  if (!isLoading && (showLoginForm || (!isAuthenticated && showLoginForm))) {
    return (
      <div className="min-h-screen flex flex-col">
        {/* 헤더 */}
        <Header />

        {/* 메인 내비게이션 */}
        <MainNavigation />

        {/* 로그인 및 회원가입 화면 */}
        <main className="flex-grow bg-background flex items-center justify-center p-6">
          <div className="w-full max-w-md">
            <LoginForm onLoginSuccess={() => setShowLoginForm(false)} />
          </div>
        </main>

        {/* 푸터 */}
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* 헤더 */}
      <Header />

      {/* 메인 내비게이션 */}
      <MainNavigation />

      {/* 메인 콘텐츠 */}
      <main className="flex-grow bg-background">
        <div className="variety-container py-6">
          <div className="flex flex-col lg:flex-row gap-8">
            {/* 왼쪽 메인 콘텐츠 */}
            <div className="w-full lg:w-2/3">
              {/* 날짜 표시 */}
              <div className="text-sm text-muted-foreground mb-4">
                <ClientDateDisplay />
              </div>

              {/* 주요 뉴스 - 모든 카테고리의 신뢰도 높은 최신 뉴스 */}
              <NewsSection
                title="주요 뉴스"
                limit={4}
                showTrending={false}
              />

              {/* 섹션별 뉴스 */}
              <section className="mb-10">
                <Tabs defaultValue="ai" className="w-full">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="ai">인공지능</TabsTrigger>
                    <TabsTrigger value="data">빅데이터</TabsTrigger>
                    <TabsTrigger value="cloud">클라우드</TabsTrigger>
                    <TabsTrigger value="startup">스타트업</TabsTrigger>
                  </TabsList>
                  <TabsContent value="ai" className="pt-4">
                    <NewsSection
                      title=""
                      category="인공지능"
                      limit={4}
                    />
                  </TabsContent>

                  <TabsContent value="data" className="pt-4">
                    <NewsSection
                      title=""
                      category="빅데이터"
                      limit={4}
                    />
                  </TabsContent>

                  <TabsContent value="cloud" className="pt-4">
                    <NewsSection
                      title=""
                      category="클라우드"
                      limit={4}
                    />
                  </TabsContent>

                  <TabsContent value="startup" className="pt-4">
                    <NewsSection
                      title=""
                      category="스타트업"
                      limit={4}
                    />
                  </TabsContent>
                </Tabs>
              </section>

              {/* AI 서비스 리뷰 */}
              <NewsSection
                title="AI 서비스 리뷰"
                category="ai-서비스"
                limit={3}
                view="grid"
              />
            </div>

            {/* 오른쪽 사이드바 */}
            <div className="w-full lg:w-1/3">
              {/* 인기 뉴스 */}
              <TrendingNewsSection />

              {/* 맞춤 추천 뉴스 */}
              {(user || firstNewsId || coldStartRecommendations.length > 0) && (
                <>
                  <RecommendedNewsSection
                    userId={user?.id || firstNewsId}
                    limit={5}
                    fallbackData={coldStartRecommendations}
                    isColdStartLoading={coldStartLoading}
                  />

                  {/* 관련 뉴스 */}
                  <RelatedNewsSection
                    newsId={firstNewsId}
                    limit={4}
                  />
                </>
              )}

              {/* AI 용어 사전 */}
              <TerminologyPanel />

              {/* 구독 안내 */}
              <SubscriptionPanel />
            </div>
          </div>
        </div>
      </main>

      {/* 푸터 */}
      <Footer />
    </div>
  );
}

// 클라이언트 컴포넌트로 현재 날짜 표시
function ClientDateDisplay() {
  const [date, setDate] = useState("");

  useEffect(() => {
    setDate(
      new Date().toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        weekday: 'long'
      })
    );
  }, []);

  return <span>{date}</span>;
}