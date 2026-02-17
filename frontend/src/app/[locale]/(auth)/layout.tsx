"use client";

import { Header } from "@/components/layout/header";
import { DarkVeilBackground } from "@/components/landing";
import { LandingFooter } from "@/components/landing/landing-footer";
import { useTheme } from "@/lib/brand-context";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const theme = useTheme();

  return (
    <div className="landing-wrapper bg-background text-foreground min-h-screen flex flex-col">
      {/* ── Navbar ── */}
      <Header variant="landing" />

      {/* ── Main Content with Background ── */}
      <section className="relative flex-1 flex items-center justify-center pt-16">
        {/* WebGL DarkVeil background */}
        <DarkVeilBackground hueShift={theme.effects?.darkVeilHueShift ?? 0} />

        {/* Login Card */}
        <div className="relative z-10 w-full max-w-[420px] bg-black/60 backdrop-blur-xl rounded-2xl border border-white/10 p-8 shadow-2xl mx-4">
          {children}
        </div>
      </section>

      {/* ── Footer ── */}
      <LandingFooter />
    </div>
  );
}
