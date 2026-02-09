"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Sparkles, Grid3X3, TrendingUp, Activity } from "lucide-react";

/* ── Brand Data ── */

const aiModels = [
  { name: "DeepSeek", accent: "#4f6df5" },
  { name: "Qwen", accent: "#7c3aed" },
  { name: "Zhipu", accent: "#3b82f6" },
  { name: "MiniMax", accent: "#6366f1" },
  { name: "Kimi", accent: "#14b8a6" },
  { name: "OpenAI", accent: "#10a37f" },
  { name: "Gemini", accent: "#4285f4" },
  { name: "Grok", accent: "#1da1f2" },
];

const exchanges = [
  { name: "Binance", accent: "#f0b90b" },
  { name: "Bybit", accent: "#f7a600" },
  { name: "OKX", accent: "#e5e5e5" },
  { name: "Hyperliquid", accent: "#a3e635" },
];

const strategies = [
  { key: "grid", Icon: Grid3X3 },
  { key: "dca", Icon: TrendingUp },
  { key: "rsi", Icon: Activity },
  { key: "aiNlp", Icon: Sparkles },
] as const;

/* ── Sub-components ── */

function BrandPill({ name, accent }: { name: string; accent: string }) {
  return (
    <div className="capability-brand-pill">
      <span
        className="capability-brand-dot"
        style={{ backgroundColor: accent, boxShadow: `0 0 8px ${accent}50` }}
      />
      <span className="capability-brand-name">{name}</span>
    </div>
  );
}

function CapabilityCard({
  number,
  children,
  titleKey,
  descKey,
  t,
}: {
  number: string;
  children: React.ReactNode;
  titleKey: string;
  descKey: string;
  t: ReturnType<typeof useTranslations>;
}) {
  const cardRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const el = cardRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      el.style.setProperty("--glow-x", `${e.clientX - rect.left}px`);
      el.style.setProperty("--glow-y", `${e.clientY - rect.top}px`);
      el.style.setProperty("--glow-intensity", "1");
    },
    []
  );

  const handleMouseLeave = useCallback(() => {
    cardRef.current?.style.setProperty("--glow-intensity", "0");
  }, []);

  return (
    <div
      ref={cardRef}
      className="bento-card capability-card"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <span className="capability-number">{number}</span>
      <div className="capability-showcase">{children}</div>
      <h3 className="capability-card-title">{t(titleKey)}</h3>
      <p className="capability-card-desc">{t(descKey)}</p>
    </div>
  );
}

/* ── Main Component ── */

export function CapabilityShowcase() {
  const t = useTranslations("landing");
  const sectionRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setVisible(true);
      },
      { threshold: 0.2 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <section className="relative z-22 w-full overflow-hidden py-20">
      <div className="mx-auto max-w-[1100px] px-4 sm:px-8">
        {/* Section header */}
        <div
          ref={sectionRef}
          className={`mb-16 text-center fade-in-section ${visible ? "visible" : ""}`}
        >
          <h2 className="section-title-rb text-gradient-animated inline-block">
            {t("capabilities.title")}
          </h2>
          <p className="section-subtitle-rb mt-1 text-center px-4">
            {t("capabilities.subtitle")}
          </p>
        </div>

        {/* Cards */}
        <div className={`capability-grid ${visible ? "capability-grid-visible" : ""}`}>
          {/* 01 — AI Models */}
          <CapabilityCard
            number="01"
            titleKey="capabilities.models.title"
            descKey="capabilities.models.desc"
            t={t}
          >
            <div className="capability-brand-grid">
              {aiModels.map((m) => (
                <BrandPill key={m.name} {...m} />
              ))}
            </div>
          </CapabilityCard>

          {/* 02 — Exchanges */}
          <CapabilityCard
            number="02"
            titleKey="capabilities.exchanges.title"
            descKey="capabilities.exchanges.desc"
            t={t}
          >
            <div className="capability-brand-grid capability-brand-grid-lg">
              {exchanges.map((ex) => (
                <BrandPill key={ex.name} {...ex} />
              ))}
            </div>
          </CapabilityCard>

          {/* 03 — Strategy Types */}
          <CapabilityCard
            number="03"
            titleKey="capabilities.strategies.title"
            descKey="capabilities.strategies.desc"
            t={t}
          >
            <div className="capability-strategy-grid">
              {strategies.map(({ key, Icon }) => (
                <div key={key} className="capability-strategy-item">
                  <Icon className="capability-strategy-icon" />
                  <span className="capability-strategy-name">
                    {t(`capabilities.strategies.items.${key}`)}
                  </span>
                </div>
              ))}
            </div>
          </CapabilityCard>
        </div>
      </div>
    </section>
  );
}
