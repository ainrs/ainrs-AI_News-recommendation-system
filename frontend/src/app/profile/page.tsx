'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAuth } from '@/lib/auth/authContext';
import Header from '@/components/Header';
import MainNavigation from '@/components/MainNavigation';
import Footer from '@/components/Footer';
import UserRecommendedNews from '@/components/UserRecommendedNews';
import { apiClient } from '@/lib/api/client';

export default function ProfilePage() {
  const { user, isAuthenticated, isLoading, updateProfile, logout } = useAuth();
  const router = useRouter();

  // 사용자가 로그인하지 않은 경우 홈으로 리디렉션
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/');
    }
  }, [isLoading, isAuthenticated, router]);

  // 프로필 편집 상태
  const [editMode, setEditMode] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null);

  // 선호 카테고리 (복수 선택)
  const [categories, setCategories] = useState<string[]>([]);
  const availableCategories = [
    '인공지능', '빅데이터', '클라우드', '스타트업', '블록체인',
    '메타버스', 'IT기업', 'AI서비스', '로봇'
  ];

  // 사용자 통계 데이터
  const [userStats, setUserStats] = useState<{
    views: number;
    likes: number;
    comments: number;
    shares: number;
    categoryDistribution: Record<string, number>;
    sourceDistribution: Record<string, number>;
  }>({
    views: 0,
    likes: 0,
    comments: 0,
    shares: 0,
    categoryDistribution: {},
    sourceDistribution: {}
  });

  // 사용자 데이터 로드
  useEffect(() => {
    if (user) {
      setUsername(user.username);
      setEmail(user.email || '');
      setCategories(user.preferences?.categories || []);

      // 사용자 통계 가져오기
      async function fetchUserStats() {
        try {
          const stats = await apiClient.ai.getUserStats(user.id);
          setUserStats({
            views: stats.views,
            likes: stats.likes,
            comments: stats.comments,
            shares: stats.shares,
            categoryDistribution: stats.category_distribution,
            sourceDistribution: stats.source_distribution
          });
        } catch (error) {
          console.error('사용자 통계를 가져오는 중 오류:', error);
        }
      }

      fetchUserStats();
    }
  }, [user]);

  // 카테고리 토글 핸들러
  const toggleCategory = (category: string) => {
    if (categories.includes(category)) {
      setCategories(categories.filter(c => c !== category));
    } else {
      setCategories([...categories, category]);
    }
  };

  // 프로필 저장 핸들러
  const handleSaveProfile = async () => {
    setProfileError(null);
    setProfileSuccess(null);

    if (!username.trim()) {
      setProfileError('사용자 이름은 필수입니다');
      return;
    }

    try {
      const success = await updateProfile({
        username,
        email: email || undefined,
        preferences: {
          categories
        }
      });

      if (success) {
        setProfileSuccess('프로필이 성공적으로 업데이트되었습니다');
        setEditMode(false);
      } else {
        setProfileError('프로필 업데이트에 실패했습니다');
      }
    } catch (error) {
      setProfileError('프로필 업데이트 중 오류가 발생했습니다');
    }
  };

  // 로그인 중이거나 인증되지 않은 경우 로딩 표시
  if (isLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex flex-col">
        <Header />
        <MainNavigation />
        <main className="flex-grow flex items-center justify-center">
          <p>로딩 중...</p>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <MainNavigation />

      <main className="flex-grow bg-background">
        <div className="variety-container py-8">
          <h1 className="text-3xl font-bold mb-6">내 프로필</h1>

          <Tabs defaultValue="profile" className="space-y-4">
            <TabsList>
              <TabsTrigger value="profile">프로필 정보</TabsTrigger>
              <TabsTrigger value="preferences">콘텐츠 설정</TabsTrigger>
              <TabsTrigger value="statistics">활동 통계</TabsTrigger>
            </TabsList>

            {/* 프로필 정보 */}
            <TabsContent value="profile" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>프로필 정보</CardTitle>
                  <CardDescription>
                    개인 정보를 확인하고 업데이트하세요
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {profileError && (
                    <Alert variant="destructive" className="mb-4">
                      <AlertDescription>{profileError}</AlertDescription>
                    </Alert>
                  )}

                  {profileSuccess && (
                    <Alert className="mb-4 bg-green-50 text-green-700 border-green-200">
                      <AlertDescription>{profileSuccess}</AlertDescription>
                    </Alert>
                  )}

                  <div className="flex flex-col sm:flex-row items-center gap-4 mb-6">
                    <Avatar className="h-24 w-24">
                      <AvatarImage src={`https://ui-avatars.com/api/?name=${user?.username}&size=192&background=random`} />
                      <AvatarFallback>{user?.username?.substring(0, 2).toUpperCase()}</AvatarFallback>
                    </Avatar>

                    <div>
                      <h2 className="text-2xl font-bold">{user?.username}</h2>
                      <p className="text-gray-500">가입일: {new Date().toLocaleDateString('ko-KR')}</p>
                    </div>
                  </div>

                  {editMode ? (
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="username">사용자 이름</Label>
                        <Input
                          id="username"
                          value={username}
                          onChange={(e) => setUsername(e.target.value)}
                          placeholder="사용자 이름"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="email">이메일</Label>
                        <Input
                          id="email"
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder="이메일"
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div>
                        <Label className="text-gray-500 block">사용자 이름</Label>
                        <div>{user?.username}</div>
                      </div>

                      {user?.email && (
                        <div>
                          <Label className="text-gray-500 block">이메일</Label>
                          <div>{user.email}</div>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
                <CardFooter className="flex justify-between">
                  {editMode ? (
                    <>
                      <Button variant="outline" onClick={() => setEditMode(false)}>취소</Button>
                      <Button onClick={handleSaveProfile}>저장</Button>
                    </>
                  ) : (
                    <>
                      <Button variant="outline" onClick={() => {
                        logout();
                        router.push('/');
                      }}>로그아웃</Button>
                      <Button onClick={() => setEditMode(true)}>편집</Button>
                    </>
                  )}
                </CardFooter>
              </Card>
            </TabsContent>

            {/* 콘텐츠 설정 */}
            <TabsContent value="preferences" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>콘텐츠 선호도 설정</CardTitle>
                  <CardDescription>
                    관심 있는 카테고리를 선택하면 맞춤형 콘텐츠를 추천해 드립니다
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <Label>관심 카테고리</Label>
                    <div className="flex flex-wrap gap-2">
                      {availableCategories.map(category => (
                        <Button
                          key={category}
                          variant={categories.includes(category) ? "default" : "outline"}
                          onClick={() => toggleCategory(category)}
                          className="rounded-full"
                        >
                          {category}
                        </Button>
                      ))}
                    </div>
                  </div>
                </CardContent>
                <CardFooter>
                  <Button onClick={handleSaveProfile}>선호도 저장</Button>
                </CardFooter>
              </Card>
            </TabsContent>

            {/* 활동 통계 */}
            <TabsContent value="statistics" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>활동 통계</CardTitle>
                  <CardDescription>
                    지난 30일간의 활동 통계입니다
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-8">
                  {/* 활동 요약 */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-gray-50 p-4 rounded-lg text-center">
                      <div className="text-2xl font-bold">{userStats.views}</div>
                      <div className="text-gray-500 text-sm">조회수</div>
                    </div>
                    <div className="bg-gray-50 p-4 rounded-lg text-center">
                      <div className="text-2xl font-bold">{userStats.likes}</div>
                      <div className="text-gray-500 text-sm">좋아요</div>
                    </div>
                    <div className="bg-gray-50 p-4 rounded-lg text-center">
                      <div className="text-2xl font-bold">{userStats.comments}</div>
                      <div className="text-gray-500 text-sm">댓글</div>
                    </div>
                    <div className="bg-gray-50 p-4 rounded-lg text-center">
                      <div className="text-2xl font-bold">{userStats.shares}</div>
                      <div className="text-gray-500 text-sm">공유</div>
                    </div>
                  </div>

                  {/* 카테고리 분포 */}
                  <div>
                    <h3 className="text-lg font-semibold mb-2">카테고리별 조회 분포</h3>
                    <div className="space-y-2">
                      {Object.entries(userStats.categoryDistribution).length > 0 ? (
                        Object.entries(userStats.categoryDistribution)
                          .sort((a, b) => b[1] - a[1])
                          .map(([category, count]) => (
                            <div key={category}>
                              <div className="flex justify-between mb-1">
                                <span>{category}</span>
                                <span>{count}회</span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-2.5">
                                <div
                                  className="bg-blue-600 h-2.5 rounded-full"
                                  style={{
                                    width: `${Math.min(100, (count / Math.max(...Object.values(userStats.categoryDistribution))) * 100)}%`
                                  }}
                                ></div>
                              </div>
                            </div>
                          ))
                      ) : (
                        <p className="text-gray-500">아직 충분한 데이터가 없습니다</p>
                      )}
                    </div>
                  </div>

                  {/* 맞춤 추천 뉴스 */}
                  <div className="mt-8">
                    <UserRecommendedNews />
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </main>

      <Footer />
    </div>
  );
}
