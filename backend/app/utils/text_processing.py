import re
import html
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

def clean_html(html_text: str) -> str:
    """
    HTML 태그를 제거하고 텍스트를 정리합니다.

    Args:
        html_text: 정리할 HTML 텍스트

    Returns:
        정리된 텍스트
    """
    if not html_text:
        return ""

    # BeautifulSoup으로 HTML 파싱
    soup = BeautifulSoup(html_text, "html.parser")

    # 스크립트, 스타일 태그 제거
    for script in soup(["script", "style"]):
        script.extract()

    # 텍스트 추출
    text = soup.get_text()

    # HTML 엔티티 디코딩
    text = html.unescape(text)

    # 여러 공백 제거
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    텍스트에서 키워드를 추출합니다.
    이 함수는 간단한 통계적 방법을 사용합니다.
    실제 환경에서는 더 정교한 알고리즘을 사용해야 합니다.

    Args:
        text: 키워드를 추출할 텍스트
        max_keywords: 최대 키워드 수

    Returns:
        추출된 키워드 목록
    """
    import re
    from collections import Counter

    # 불용어 정의
    stopwords = set([
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "as", "at",
        "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "could", "did", "do",
        "does", "doing", "down", "during", "each", "few", "for", "from", "further", "had", "has", "have", "having",
        "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how",
        "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "it", "it's", "its", "itself", "let's",
        "me", "more", "most", "my", "myself", "nor", "of", "on", "once", "only", "or", "other", "ought", "our",
        "ours", "ourselves", "out", "over", "own", "same", "she", "she'd", "she'll", "she's", "should", "so", "some",
        "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's",
        "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under",
        "until", "up", "very", "was", "we", "we'd", "we'll", "we're", "we've", "were", "what", "what's", "when",
        "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "would",
        "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
    ])

    # 텍스트 전처리
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)  # 구두점 제거

    # 단어 추출 및 불용어 제거
    words = [word for word in text.split() if word not in stopwords and len(word) > 2]

    # 단어 빈도 카운트
    word_counts = Counter(words)

    # 가장 빈번한 키워드 추출
    keywords = [word for word, count in word_counts.most_common(max_keywords)]

    return keywords

def summarize_text(text: str, max_sentences: int = 5) -> str:
    """
    텍스트를 요약합니다.
    이 함수는 간단한 추출 요약 방법을 사용합니다.
    실제 환경에서는 더 정교한 알고리즘을 사용해야 합니다.

    Args:
        text: 요약할 텍스트
        max_sentences: 최대 문장 수

    Returns:
        요약된 텍스트
    """
    import re
    from collections import Counter
    import numpy as np

    # 텍스트를 문장으로 분리
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text)
    if not sentences:
        return ""

    # 너무 짧은 문장 제거
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    # 이미 충분히 짧으면 원본 반환
    if len(sentences) <= max_sentences:
        return text

    # 각 문장의 단어 빈도수 계산
    word_frequencies = Counter()
    for sentence in sentences:
        words = re.sub(r'[^\w\s]', '', sentence.lower()).split()
        word_frequencies.update(words)

    # 최대 빈도수로 정규화
    max_frequency = max(word_frequencies.values()) if word_frequencies else 1
    for word in word_frequencies:
        word_frequencies[word] = word_frequencies[word] / max_frequency

    # 각 문장의 점수 계산
    sentence_scores = {}
    for i, sentence in enumerate(sentences):
        words = re.sub(r'[^\w\s]', '', sentence.lower()).split()
        score = sum(word_frequencies[word] for word in words) / len(words) if words else 0
        sentence_scores[i] = score

    # 점수가 높은 문장 선택
    top_indices = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:max_sentences]
    top_indices.sort()  # 원래 순서 유지

    # 선택된 문장으로 요약 생성
    summary = " ".join(sentences[i] for i in top_indices)

    return summary

def normalize_text(text: str) -> str:
    """
    텍스트를 정규화합니다 (소문자로 변환, 특수 문자 제거 등)

    Args:
        text: 정규화할 텍스트

    Returns:
        정규화된 텍스트
    """
    if not text:
        return ""

    # 소문자로 변환
    text = text.lower()

    # 여러 공백을 하나로 압축
    text = re.sub(r'\s+', ' ', text).strip()

    # 특수 문자 제거 (알파벳, 숫자, 공백만 유지)
    text = re.sub(r'[^\w\s]', '', text)

    return text

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    긴 텍스트를 청크로 나눕니다.

    Args:
        text: 청크로 나눌 텍스트
        chunk_size: 각 청크의 최대 문자 수
        overlap: 인접 청크 간의 중복 문자 수

    Returns:
        텍스트 청크 목록
    """
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        # 청크 끝 위치 계산
        end = min(start + chunk_size, len(text))

        # 단어 경계에서 끝내기 위해 조정
        if end < len(text):
            # 다음 공백 찾기
            next_space = text.find(' ', end)
            if next_space != -1 and next_space - end < 50:  # 50자 이내에 공백이 있다면
                end = next_space

        # 청크 추가
        chunks.append(text[start:end])

        # 다음 시작 위치 계산 (중복 고려)
        start = end - overlap

        # 중복이 텍스트 길이보다 크면 종료
        if start < 0:
            break

    return chunks
