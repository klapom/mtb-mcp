'use client';

import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';

export function Header() {
  const { user } = useAuth();

  return (
    <header className="fixed top-0 left-0 right-0 z-[100] h-[var(--header-height)] bg-[rgba(15,15,30,0.85)] backdrop-blur-[20px] border-b border-border-subtle flex items-center justify-between px-4">
      <Link href="/" className="flex items-center gap-2 text-lg font-bold tracking-tight">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <circle cx="14" cy="14" r="12" stroke="#0f9b58" strokeWidth="2" />
          <path d="M8 18 L14 8 L20 18" stroke="#0f9b58" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="14" cy="18" r="2" fill="#0f9b58" />
        </svg>
        <span className="text-white">Trail</span>
        <span className="text-accent-green">Pilot</span>
      </Link>
      <div className="flex gap-2 items-center">
        {user ? (
          <Link
            href="/profile"
            className="w-9 h-9 rounded-full flex items-center justify-center overflow-hidden hover:ring-2 ring-accent-green/50 transition-all"
          >
            {user.avatar_url ? (
              <img src={user.avatar_url} alt="" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full bg-accent-green/20 flex items-center justify-center text-accent-green font-bold text-sm">
                {user.display_name[0]?.toUpperCase()}
              </div>
            )}
          </Link>
        ) : (
          <Link
            href="/login"
            className="px-3 py-1.5 rounded-lg bg-accent-green/20 text-accent-green text-sm font-medium hover:bg-accent-green/30 transition-colors"
          >
            Login
          </Link>
        )}
      </div>
    </header>
  );
}
