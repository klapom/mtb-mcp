const variants: Record<string, string> = {
  green: "bg-accent-green/15 text-[#4ade80]",
  orange: "bg-accent-orange/15 text-[#fbbf24]",
  red: "bg-accent-red/15 text-[#f87171]",
  blue: "bg-accent-blue/15 text-[#60a5fa]",
  gray: "bg-white/8 text-text-secondary",
  s0: "bg-s0/15 text-s0",
  s1: "bg-s1/15 text-s1",
  s2: "bg-s2/15 text-s2",
  s3: "bg-s3/15 text-s3",
};

export function Badge({
  variant = "gray",
  children,
}: {
  variant?: string;
  children: React.ReactNode;
}) {
  const cls = variants[variant] ?? variants.gray;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold tracking-wide ${cls}`}
    >
      {children}
    </span>
  );
}
