import { type NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { userId, newsId, interactionType, metadata } = body;

    // 필수 필드 검증
    if (!userId || !newsId || !interactionType) {
      return NextResponse.json(
        { error: '필수 필드가 누락되었습니다.' },
        { status: 400 }
      );
    }

    // 상호작용 타입 검증
    const validInteractionTypes = ['view', 'click', 'read', 'like', 'share'];
    if (!validInteractionTypes.includes(interactionType)) {
      return NextResponse.json(
        { error: '유효하지 않은 상호작용 타입입니다.' },
        { status: 400 }
      );
    }

    // 백엔드 API 호출 (서버가 실행 중일 때만 실제 데이터 전송)
    try {
      // 백엔드 API 경로 수정 - /api/v1/interaction으로 호출
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/interaction`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          news_id: newsId,
          interaction_type: interactionType,
          metadata: metadata || {},
        }),
      });

      if (!response.ok) {
        throw new Error(`API 요청 오류: ${response.status}`);
      }

      const data = await response.json();
      return NextResponse.json(data);
    } catch (error) {
      console.error('백엔드 API 호출 중 오류:', error);

      // 백엔드 연결 오류 시에도 로컬에 상호작용 기록
      console.log(`[로컬 기록] 상호작용: ${userId}, ${newsId}, ${interactionType}`);

      // 성공 응답 반환 (실패하지 않은 것처럼)
      return NextResponse.json({
        message: '상호작용이 로컬에 기록되었습니다.',
        success: true,
        localOnly: true,
      });
    }
  } catch (error) {
    console.error('상호작용 처리 중 오류:', error);
    return NextResponse.json(
      { error: '요청 처리 중 오류가 발생했습니다.' },
      { status: 500 }
    );
  }
}
