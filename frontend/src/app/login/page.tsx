'use client';

import Header from '@/components/Header';
import MainNavigation from '@/components/MainNavigation';
import Footer from '@/components/Footer';
import LoginForm from '@/components/LoginForm';

export default function LoginPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <MainNavigation />

      <main className="flex-grow bg-background flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <LoginForm />
        </div>
      </main>

      <Footer />
    </div>
  );
}
