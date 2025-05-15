import { type NextRequest, NextResponse } from 'next/server';
import Parser from 'rss-parser';

// RSS 파서 인스턴스 생성
const parser = new Parser({
  customFields: {
    item: [
      ['content:encoded', 'content'],
      ['dc:creator', 'creator'],
      ['media:content', 'media'],
    ],
  },
});

export async function GET(request: NextRequest) {
  try {
    // URL 파라미터에서 RSS 피드 URL 가져오기
    const url = new URL(request.url);
    const feedUrl = url.searchParams.get('url');

    if (!feedUrl) {
      return NextResponse.json(
        { error: 'URL 파라미터가 필요합니다.' },
        { status: 400 }
      );
    }

    // CORS 문제를 피하기 위해 서버에서 RSS 피드 가져오기
    const response = await fetch(feedUrl);

    if (!response.ok) {
      return NextResponse.json(
        { error: `RSS 피드를 가져오는데 실패했습니다: ${response.statusText}` },
        { status: response.status }
      );
    }

    const xml = await response.text();

    // rss-parser 라이브러리를 사용해 XML 파싱
    const feed = await parser.parseString(xml);

    return NextResponse.json(feed);
  } catch (error) {
    console.error('RSS 피드 처리 중 오류:', error);
    return NextResponse.json(
      { error: '서버 오류가 발생했습니다.' },
      { status: 500 }
    );
  }
}
