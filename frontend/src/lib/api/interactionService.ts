/**
 * 사용자 상호작용 서비스
 * 사용자의 뉴스 상호작용을 기록하고 가져오는 기능을 제공합니다.
 */

export interface InteractionMetadata {
  dwellTimeSeconds?: number;
  scrollDepthPercent?: number;
  commentId?: string;
  referrer?: string;
  deviceType?: string;
  [key: string]: string | number | boolean | undefined;
}

export interface InteractionData {
  userId: string;
  newsId: string;
  interactionType: 'view' | 'click' | 'read' | 'like' | 'share';
  metadata?: InteractionMetadata;
}

/**
 * 상호작용을 기록합니다.
 */
export async function recordInteraction(data: InteractionData): Promise<boolean> {
  try {
    const response = await fetch('/api/interaction', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`상호작용 기록 API 오류: ${response.status}`);
    }

    return true;
  } catch (error) {
    console.error('상호작용 기록 중 오류:', error);
    // API 호출 실패 시에도 로컬 콘솔에 기록
    console.log(`[로컬] 상호작용 기록: ${data.userId}, ${data.newsId}, ${data.interactionType}`);
    return false;
  }
}

// 로컬에서 사용자가 이미 좋아요, 북마크 등을 눌렀는지 확인하는 함수
// 실제로는 백엔드에서 데이터를 가져와야 하지만, 로컬에서 임시로 상태를 관리
const localInteractions = new Map<string, Set<string>>();

export function hasInteracted(userId: string, newsId: string, interactionType: string): boolean {
  const key = `${userId}-${interactionType}`;
  const interactions = localInteractions.get(key);
  return interactions ? interactions.has(newsId) : false;
}

export function setLocalInteraction(
  userId: string,
  newsId: string,
  interactionType: string,
  value: boolean
): void {
  const key = `${userId}-${interactionType}`;
  let interactions = localInteractions.get(key);

  if (!interactions) {
    interactions = new Set<string>();
    localInteractions.set(key, interactions);
  }

  if (value) {
    interactions.add(newsId);
  } else {
    interactions.delete(newsId);
  }
}

// 서비스 객체 export
export const interactionService = {
  recordInteraction,
  hasInteracted,
  setLocalInteraction,
};

export default interactionService;
