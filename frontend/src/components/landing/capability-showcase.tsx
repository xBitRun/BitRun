"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import {
  FileText,
  BarChart3,
  Brain,
  Shield,
  Zap,
  TrendingUp,
} from "lucide-react";
import { Marquee } from "./marquee";

/* ── Process Flow Data ── */

const processSteps = [
  {
    key: "strategy",
    Icon: FileText,
    titleKey: "capabilities.strategy.title",
    descKey: "capabilities.strategy.desc",
  },
  {
    key: "analysis",
    Icon: BarChart3,
    titleKey: "capabilities.analysis.title",
    descKey: "capabilities.analysis.desc",
  },
  {
    key: "decision",
    Icon: Brain,
    titleKey: "capabilities.decision.title",
    descKey: "capabilities.decision.desc",
  },
  {
    key: "risk",
    Icon: Shield,
    titleKey: "capabilities.risk.title",
    descKey: "capabilities.risk.desc",
  },
  {
    key: "execution",
    Icon: Zap,
    titleKey: "capabilities.execution.title",
    descKey: "capabilities.execution.desc",
  },
  {
    key: "backtest",
    Icon: TrendingUp,
    titleKey: "capabilities.backtest.title",
    descKey: "capabilities.backtest.desc",
  },
] as const;

function CapabilityCard({
  number,
  Icon,
  titleKey,
  descKey,
  t,
}: {
  number: string;
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
      className="capability-carousel-card"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <span className="capability-number">{number}</span>
      <div className="capability-showcase">
        <Icon className="capability-process-icon" />
      </div>
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

        {/* Cards Carousel - 2 Rows */}
        <div className="capability-carousel-wrapper">
          {/* First Row */}
          <Marquee duration={40} direction="left" className="capability-marquee">
            {processSteps.slice(0, 3).map((step, index) => (
              <CapabilityCard
                key={step.key}
                number={String(index + 1).padStart(2, "0")}
                Icon={step.Icon}
                titleKey={step.titleKey}
                descKey={step.descKey}
                t={t}
              />
            ))}
          </Marquee>
          {/* Second Row */}
          <Marquee duration={45} direction="right" className="capability-marquee">
            {processSteps.slice(3, 6).map((step, index) => (
              <CapabilityCard
                key={step.key}
                number={String(index + 4).padStart(2, "0")}
                Icon={step.Icon}
                titleKey={step.titleKey}
                descKey={step.descKey}
                t={t}
              />
            ))}
          </Marquee>
        </div>
      </div>
    </section>
  );
}
