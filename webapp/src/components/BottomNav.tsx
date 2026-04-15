'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';

const tabs = [
  { href: '/', icon: '🏠', label: 'Home' },
  { href: '/trails', icon: '🗺️', label: 'Entdecken' },
  { href: '/weather', icon: '⛅', label: 'Wetter' },
];

export function BottomNav() {
  const pathname = usePathname();
  const [moreOpen, setMoreOpen] = useState(false);
  const { user } = useAuth();

  // Don't show nav on auth pages
  if (pathname.startsWith('/login') || pathname.startsWith('/register') || pathname.startsWith('/auth/') || pathname.startsWith('/setup')) {
    return null;
  }

  const moreItems = [
    { href: '/bike', icon: '🔧', label: 'Bike' },
    { href: '/training', icon: '💪', label: 'Training' },
    { href: '/ebike', icon: '🔋', label: 'eBike' },
    { href: '/safety', icon: '⏱️', label: 'Sicherheit' },
    { href: '/profile', icon: '👤', label: 'Profil' },
    // Show trainer link if user exists (they might have athletes)
    ...(user ? [{ href: '/trainer', icon: '🏋️', label: 'Trainer' }] : []),
  ];

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  const isMoreActive = moreItems.some((item) => isActive(item.href));

  return (
    <>
      {/* More menu backdrop */}
      {moreOpen && (
        <div
          className="fixed inset-0 z-[100]"
          onClick={() => setMoreOpen(false)}
        />
      )}

      {/* More menu */}
      {moreOpen && (
        <div className="fixed bottom-[calc(var(--nav-height)+var(--safe-bottom)+4px)] right-2 z-[101] bg-bg-card border border-border-card rounded-xl shadow-[0_8px_32px_rgba(0,0,0,0.4)] py-2 min-w-[170px] animate-[menuIn_0.2s_ease]">
          {moreItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMoreOpen(false)}
              className={`flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors hover:bg-white/5 ${
                isActive(item.href) ? 'text-accent-green' : 'text-text-primary'
              }`}
            >
              <span className="text-lg w-6 text-center">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </div>
      )}

      {/* Bottom nav bar */}
      <nav className="fixed bottom-0 left-0 right-0 z-[100] h-[calc(var(--nav-height)+var(--safe-bottom))] pb-[var(--safe-bottom)] bg-[rgba(15,15,30,0.92)] backdrop-blur-[20px] border-t border-border-subtle flex">
        <div className="flex flex-1">
          {tabs.map((tab) => (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex-1 flex flex-col items-center justify-center gap-0.5 text-[10px] transition-colors relative py-1.5 active:scale-[0.92] ${
                isActive(tab.href) ? 'text-accent-green' : 'text-text-muted'
              }`}
            >
              {isActive(tab.href) && (
                <span className="absolute top-0 left-1/2 -translate-x-1/2 w-6 h-0.5 bg-accent-green rounded-b-sm" />
              )}
              <span className="text-xl leading-none">{tab.icon}</span>
              {tab.label}
            </Link>
          ))}
          <button
            onClick={() => setMoreOpen(!moreOpen)}
            className={`flex-1 flex flex-col items-center justify-center gap-0.5 text-[10px] transition-colors relative py-1.5 active:scale-[0.92] ${
              isMoreActive ? 'text-accent-green' : 'text-text-muted'
            }`}
          >
            {isMoreActive && (
              <span className="absolute top-0 left-1/2 -translate-x-1/2 w-6 h-0.5 bg-accent-green rounded-b-sm" />
            )}
            <span className="text-xl leading-none">⋯</span>
            More
          </button>
        </div>
      </nav>
    </>
  );
}
