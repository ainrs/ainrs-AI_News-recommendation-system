/**
 * RSS 피드 서비스
 * 다양한 소스에서 RSS 피드를 가져와 파싱하는 기능을 제공합니다.
 */

import type { News } from './types';
import { apiClient } from './client';

interface RSSItem {
  title: string;
  link: string;
  pubDate: string;
  creator?: string;
  content?: string;
  contentSnippet?: string;
  categories?: string[];
  guid?: string;
  isoDate?: string;
}

interface RSSFeed {
  items: RSSItem[];
  feedUrl: string;
  title: string;
  description: string;
  generator?: string;
  link: string;
  language?: string;
  lastBuildDate?: string;
}

// RSS 피드 소스 목록
const RSS_SOURCES = [
  {
    id: 'techcrunch',
    name: 'TechCrunch',
    url: 'https://techcrunch.com/feed/',
    category: ['기술', '스타트업'],
    language: 'en'
  },
  {
    id: 'zdnet-kr',
    name: 'ZDNet Korea',
    url: 'https://www.zdnet.co.kr/xml/rss/bestnews.xml',
    category: ['IT', '기술'],
    language: 'ko'
  },
  {
    id: 'bloter',
    name: '블로터',
    url: 'https://www.bloter.net/feed',
    category: ['IT', '기술'],
    language: 'ko'
  },
  {
    id: 'venture-square',
    name: '벤처스퀘어',
    url: 'https://www.venturesquare.net/feed',
    category: ['스타트업', '투자'],
    language: 'ko'
  },
  {
    id: 'aitimes',
    name: 'AI타임스',
    url: 'https://www.aitimes.com/rss/rss.html',
    category: ['AI', '인공지능'],
    language: 'ko'
  }
];

// HTML 콘텐츠에서 첫 번째 이미지 URL을 추출하는 함수
function extractImageFromContent(content: string): string {
  // 간단한 정규식으로 이미지 URL 추출
  const imgRegex = /<img[^>]+src="([^">]+)"/;
  const match = content.match(imgRegex);

  return match ? match[1] : '';
}

// 제목과 콘텐츠에서 키워드를 추출하는 함수
function extractKeywords(title: string, content: string): string[] {
  // 간단한 구현: 제목에서 주요 단어 추출
  const combinedText = `${title} ${content}`;
  const words = combinedText
    .toLowerCase()
    .replace(/[^\w\s가-힣]/g, '')
    .split(/\s+/)
    .filter(word => word.length > 1)
    .filter(word => !['the', 'and', 'in', 'on', 'at', 'to', 'for', 'with', '이', '그', '저', '것', '은', '는', '이다', '있다'].includes(word));

  // 빈도수 기반으로 키워드 추출
  const wordFreq: Record<string, number> = {};
  for (const word of words) {
    wordFreq[word] = (wordFreq[word] || 0) + 1;
  }

  return Object.entries(wordFreq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(entry => entry[0]);
}

// 백엔드 API를 통해 RSS 뉴스 가져오기
export async function fetchRSSNews(category?: string): Promise<News[]> {
  try {
    // 백엔드 API를 통해 RSS 피드 데이터 가져오기
    return await apiClient.ai.getRSSFeeds(category);
  } catch (error) {
    console.error('RSS 피드를 가져오는 중 오류 발생:', error);
    // 오류 발생 시 빈 배열 반환
    return [];
  }
}

export const rssService = {
  fetchRSSNews,
  getSources: () => RSS_SOURCES,
};

export default rssService;
