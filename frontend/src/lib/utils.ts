import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * 클래스네임을 병합하는 유틸리티 함수
 * tailwind 클래스와 clsx 조건부 클래스를 함께 사용할 수 있게 해줍니다.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
