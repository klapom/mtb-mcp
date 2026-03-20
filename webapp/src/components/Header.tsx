export function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-[100] h-[var(--header-height)] bg-[rgba(15,15,30,0.85)] backdrop-blur-[20px] border-b border-border-subtle flex items-center justify-between px-4">
      <div className="flex items-center gap-2 text-lg font-bold tracking-tight">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <circle cx="14" cy="14" r="12" stroke="#0f9b58" strokeWidth="2" />
          <path d="M8 18 L14 8 L20 18" stroke="#0f9b58" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="14" cy="18" r="2" fill="#0f9b58" />
        </svg>
        <span className="text-white">Trail</span>
        <span className="text-accent-green">Pilot</span>
      </div>
      <div className="flex gap-2">
        <button className="w-9 h-9 rounded-full bg-white/6 flex items-center justify-center text-base hover:bg-white/12 transition-colors">
          📍
        </button>
      </div>
    </header>
  );
}
