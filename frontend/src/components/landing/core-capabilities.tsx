"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { FileText, Users, BarChart3 } from "lucide-react";

/* ── Core Capabilities Data ── */

const coreCapabilities = [
  {
    key: "nlp",
    Icon: FileText,
    titleKey: "coreCapabilities.nlp.title",
    descKey: "coreCapabilities.nlp.desc",
  },
  {
    key: "debate",
    Icon: Users,
    titleKey: "coreCapabilities.debate.title",
    descKey: "coreCapabilities.debate.desc",
  },
  {
    key: "backtest",
    Icon: BarChart3,
    titleKey: "coreCapabilities.backtest.title",
    descKey: "coreCapabilities.backtest.desc",
  },
] as const;

function CoreCapabilityCard({
  Icon,
  titleKey,
  descKey,
  t,
}: {
  Icon: React.ComponentType<{ className?: string }>;
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
      className="core-capability-card"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <div className="core-capability-icon-wrapper">
        <Icon className="core-capability-icon" />
      </div>
      <h3 className="core-capability-title">{t(titleKey)}</h3>
      <p className="core-capability-desc">{t(descKey)}</p>
    </div>
  );
}

/* ── Main Component ── */

export function CoreCapabilities() {
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
    <section className="relative z-22 w-full py-20">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-8">
        {/* Section header */}
        <div
          ref={sectionRef}
          className={`mb-16 text-center fade-in-section ${visible ? "visible" : ""}`}
        >
          <h2 className="section-title-rb text-gradient-animated inline-block">
            {t("coreCapabilities.title")}
          </h2>
          <p className="section-subtitle-rb mt-1 text-center px-4">
            {t("coreCapabilities.subtitle")}
          </p>
        </div>

        {/* Cards Grid */}
        <div className={`core-capabilities-grid ${visible ? "core-capabilities-grid-visible" : ""}`}>
          {coreCapabilities.map((capability) => (
            <CoreCapabilityCard
              key={capability.key}
              Icon={capability.Icon}
              titleKey={capability.titleKey}
              descKey={capability.descKey}
              t={t}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
