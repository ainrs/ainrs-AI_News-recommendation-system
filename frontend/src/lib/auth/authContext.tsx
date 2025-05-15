'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiClient } from '@/lib/api/client';

// 사용자 인터페이스
export interface User {
  id: string;
  username: string;
  email?: string;
  accessToken?: string;
  preferences?: {
    categories?: string[];
    sources?: string[];
  };
}

// 인증 상태 인터페이스
interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
}

// 인증 컨텍스트 인터페이스
interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  register: (username: string, email: string, password: string) => Promise<boolean>;
  updateProfile: (userData: Partial<User>) => Promise<boolean>;
  requestEmailVerification: (email: string) => Promise<boolean>;
  verifyEmailCode: (email: string, code: string) => Promise<boolean>;
  getPendingVerificationEmail: () => string | null;
}

// 초기 인증 상태
const initialAuthState: AuthState = {
  user: null,
  isLoading: true,
  isAuthenticated: false,
  error: null,
};

// 기본 컨텍스트 값
const defaultAuthContext: AuthContextType = {
  ...initialAuthState,
  login: async () => false,
  logout: () => {},
  register: async () => false,
  updateProfile: async () => false,
  requestEmailVerification: async () => false,
  verifyEmailCode: async () => false,
  getPendingVerificationEmail: () => null,
};

// 인증 컨텍스트 생성
const AuthContext = createContext<AuthContextType>(defaultAuthContext);

// 인증 컨텍스트 훅
export const useAuth = () => useContext(AuthContext);

// 로컬 스토리지 키
const AUTH_STORAGE_KEY = 'variety_ai_auth';

// 인증 컨텍스트 프로바이더
export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(initialAuthState);

  // 로컬 스토리지에서 인증 정보 복원
  useEffect(() => {
    const restoreAuth = () => {
      try {
        // SSR에서 localStorage를 접근할 수 없으므로 확인 필요
        if (typeof window === 'undefined') return;

        setState(prev => ({ ...prev, isLoading: true }));

        const storedAuth = localStorage.getItem(AUTH_STORAGE_KEY);
        if (storedAuth) {
          const { user, expiry } = JSON.parse(storedAuth);

          // 만료 시간 확인
          if (expiry && new Date(expiry) > new Date()) {
            setState({
              user,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });
            return;
          }

          // 만료된 경우 로컬 스토리지 정리
          localStorage.removeItem(AUTH_STORAGE_KEY);
        }

        setState(prev => ({ ...prev, isLoading: false }));
      } catch (err) {
        console.error('인증 정보 복원 중 오류:', err);
        setState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: '인증 정보를 불러오는 중 오류가 발생했습니다',
        });
      }
    };

    restoreAuth();
  }, []);

  // 인증 정보 저장 함수
  const saveAuthToStorage = (user: User) => {
    try {
      // 24시간 유효한 만료 시간 설정
      const expiryDate = new Date();
      expiryDate.setHours(expiryDate.getHours() + 24);

      localStorage.setItem(
        AUTH_STORAGE_KEY,
        JSON.stringify({
          user,
          expiry: expiryDate.toISOString(),
        })
      );
    } catch (err) {
      console.error('인증 정보 저장 중 오류:', err);
    }
  };

  // 로그인 함수
  const login = async (username: string, password: string): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      // 백엔드 API로 로그인 요청
      const response = await apiClient.auth.login(username, password);

      const user: User = {
        id: response.user_id,
        username: response.username,
        accessToken: response.access_token,
      };

      // 상태 업데이트 및 스토리지 저장
      setState({
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });

      saveAuthToStorage(user);
      return true;
    } catch (err) {
      let errorMessage = '로그인 중 오류가 발생했습니다';

      if (err instanceof Error) {
        errorMessage = err.message;
      }

      setState(prev => ({
        ...prev,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: errorMessage,
      }));

      return false;
    }
  };

  // 로그아웃 함수
  const logout = () => {
    // 실제 환경에서는 백엔드 API로 로그아웃 요청
    // apiClient.auth.logout();

    // 로컬 스토리지에서 인증 정보 제거
    localStorage.removeItem(AUTH_STORAGE_KEY);

    // 상태 초기화
    setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
  };

  // 회원가입 함수
  const register = async (username: string, email: string, password: string): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      // 백엔드 API로 회원가입 요청
      const response = await apiClient.auth.register(username, email, password);

      // 이메일 인증이 필요한 경우
      if (response.verification_required) {
        setState(prev => ({
          ...prev,
          isLoading: false,
          error: null,
          // 사용자는 아직 인증되지 않았으므로 로그인 상태로 설정하지 않음
        }));

        // 인증이 필요하다는 정보를 로컬 스토리지에 저장
        localStorage.setItem('email_verification_pending', email);

        return true; // 회원가입 자체는 성공했지만 이메일 인증이 필요함
      }

      // 이메일 인증이 필요없는 경우 바로 로그인 처리
      const user: User = {
        id: response.user_id,
        username,
        email,
        accessToken: 'temporary_token', // 실제로는 로그인 과정을 통해 얻어야 함
      };

      // 상태 업데이트 및 스토리지 저장
      setState({
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });

      saveAuthToStorage(user);
      return true;
    } catch (err) {
      let errorMessage = '회원가입 중 오류가 발생했습니다';

      if (err instanceof Error) {
        errorMessage = err.message;
      }

      setState(prev => ({
        ...prev,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: errorMessage,
      }));

      return false;
    }
  };

  // 프로필 업데이트 함수
  const updateProfile = async (userData: Partial<User>): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      // 실제 환경에서는 백엔드 API로 프로필 업데이트 요청
      // const response = await apiClient.auth.updateProfile(userData);

      // 현재 사용자 정보가 없으면 실패
      if (!state.user) {
        throw new Error('로그인되지 않은 상태입니다');
      }

      // 기존 사용자 정보와 업데이트 정보 병합
      const updatedUser: User = {
        ...state.user,
        ...userData,
      };

      // 상태 업데이트 및 스토리지 저장
      setState(prev => ({
        ...prev,
        user: updatedUser,
        isLoading: false,
      }));

      saveAuthToStorage(updatedUser);
      return true;
    } catch (err) {
      let errorMessage = '프로필 업데이트 중 오류가 발생했습니다';

      if (err instanceof Error) {
        errorMessage = err.message;
      }

      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));

      return false;
    }
  };

  // 이메일 인증 요청 함수
  const requestEmailVerification = async (email: string): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      await apiClient.auth.requestVerificationCode(email);
      setState(prev => ({ ...prev, isLoading: false }));
      return true;
    } catch (err) {
      let errorMessage = '인증 코드 요청 중 오류가 발생했습니다';

      if (err instanceof Error) {
        errorMessage = err.message;
      }

      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));

      return false;
    }
  };

  // 이메일 인증 코드 확인 함수
  const verifyEmailCode = async (email: string, code: string): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await apiClient.auth.verifyCode(email, code);

      if (response.verified) {
        // 이메일 인증이 완료되면 보류 중인 인증 정보 삭제
        localStorage.removeItem('email_verification_pending');

        // 여기서는 바로 로그인 상태를 만들지 않고, 로그인 페이지로 이동시키는 것이 안전합니다.
        setState(prev => ({ ...prev, isLoading: false }));
        return true;
      } else {
        throw new Error('인증 코드가 유효하지 않습니다');
      }
    } catch (err) {
      let errorMessage = '인증 코드 확인 중 오류가 발생했습니다';

      if (err instanceof Error) {
        errorMessage = err.message;
      }

      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));

      return false;
    }
  };

  // 보류 중인 이메일 인증 정보 가져오기
  const getPendingVerificationEmail = (): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('email_verification_pending');
  };

  // 인증 컨텍스트 값
  const value: AuthContextType = {
    ...state,
    login,
    logout,
    register,
    updateProfile,
    requestEmailVerification,
    verifyEmailCode,
    getPendingVerificationEmail,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
