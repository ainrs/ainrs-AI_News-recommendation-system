'use client';

import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
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
        if (typeof window === 'undefined') return;

        setState(prev => ({ ...prev, isLoading: true }));

        const storedAuth = localStorage.getItem(AUTH_STORAGE_KEY);
        if (storedAuth) {
          const { user, expiry } = JSON.parse(storedAuth);

          if (expiry && new Date(expiry) > new Date()) {
            setState({
              user,
              isAuthenticated: true,
              isLoading: false,
              error: null,
            });
            return;
          }

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

      // 응답 데이터 확인
      if (!response || !response.access_token || !response.user_id) {
        throw new Error('서버 응답에 필요한 인증 정보가 없습니다.');
      }

      const user: User = {
        id: response.user_id,
        username: response.username,
        accessToken: response.access_token,
      };

      setState({
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });

      saveAuthToStorage(user);
      return true;
    } catch (err) {
      console.error('로그인 오류:', err);
      let errorMessage = '로그인 중 오류가 발생했습니다';

      if (err instanceof Error) {
        if (err.message.includes('Failed to fetch') || err.message.includes('연결할 수 없습니다')) {
          errorMessage = '서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.';
        } else if (err.message.includes('401')) {
          errorMessage = '사용자 이름 또는 비밀번호가 올바르지 않습니다.';
        } else if (err.message.includes('404')) {
          errorMessage = '로그인 API를 찾을 수 없습니다. API 서버 경로가 올바른지 확인해주세요.';
        } else if (err.message.includes('/api/v1/api/auth/login')) {
          errorMessage = 'API 경로가 올바르지 않습니다. 서버 관리자에게 문의해주세요.';
        } else {
          errorMessage = err.message;
        }
      }

      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));

      // 개발 전용 로깅
      if (process.env.NODE_ENV === 'development') {
        console.error('로그인 오류 상세:', err);
      }

      return false;
    }
  };

  // 로그아웃 함수
  const logout = () => {
    localStorage.removeItem(AUTH_STORAGE_KEY);

    setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
  };

  // 회원가입 함수
  const register = async (
    username: string,
    email: string,
    password: string
  ): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      console.log('회원가입 시도 중:', { username, email });

      // 백엔드 API로 회원가입 요청
      const response = await apiClient.auth.register(username, email, password);

      console.log('회원가입 응답:', response);

      if (response.verification_required) {
        // 이메일 인증이 필요한 경우
        setState(prev => ({
          ...prev,
          isLoading: false,
          error: null,
        }));

        localStorage.setItem('email_verification_pending', email);

        return true;
      }

      // 이메일 인증이 필요없는 경우 바로 로그인 처리
      const user: User = {
        id: response.user_id,
        username,
        email,
        accessToken: 'temporary_token',
      };

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
        if (err.message.includes('Failed to fetch') || err.message.includes('연결할 수 없습니다')) {
          errorMessage = '서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.';
        } else if (err.message.includes('409') || err.message.includes('already exists')) {
          errorMessage = '이미 등록된 사용자 이름 또는 이메일입니다.';
        } else {
          errorMessage = err.message;
        }
      }

      setState(prev => ({
        ...prev,
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
      if (!state.user) {
        throw new Error('로그인되지 않은 상태입니다');
      }

      const updatedUser: User = {
        ...state.user,
        ...userData,
      };

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
        localStorage.removeItem('email_verification_pending');
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
