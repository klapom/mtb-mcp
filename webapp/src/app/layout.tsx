import type { Metadata, Viewport } from "next";
import { Header } from "@/components/Header";
import { BottomNav } from "@/components/BottomNav";
import "./globals.css";

export const metadata: Metadata = {
  title: "TrailPilot",
  description: "MTB Copilot — Weather, Trails, Tours, and more.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  userScalable: false,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="de">
      <body>
        <Header />
        <main className="pt-[var(--header-height)] pb-[calc(var(--nav-height)+var(--safe-bottom)+8px)] min-h-dvh">
          <div className="p-4 max-w-[500px] mx-auto animate-[screenIn_0.3s_ease]">
            {children}
          </div>
        </main>
        <BottomNav />
      </body>
    </html>
  );
}
