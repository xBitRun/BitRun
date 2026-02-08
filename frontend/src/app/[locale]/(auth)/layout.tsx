"use client";

import { Header } from "@/components/layout/header";
import { DarkVeil } from "@/components/landing/dark-veil";
import { LandingFooter } from "@/components/landing/landing-footer";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="landing-wrapper bg-[#060010] text-white min-h-screen flex flex-col">
      {/* ── Navbar ── */}
      <Header variant="landing" />

      {/* ── Main Content with Background ── */}
      <section className="relative flex-1 flex items-center justify-center pt-16">
        {/* WebGL DarkVeil background */}
        <div className="dark-veil-container">
          <DarkVeil
            hueShift={0}
            noiseIntensity={0}
            scanlineIntensity={0}
            speed={0.5}
            scanlineFrequency={0}
            warpAmount={0}
            resolutionScale={1}
          />
        </div>

        {/* Gradient blur overlay */}
        <div className="landing-gradient-blur" aria-hidden="true" />

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
