"use client";

import { useRef, useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { AnimatedCounter } from "./counter";

interface CardData {
  target: number;
  suffix: string;
  titleKey: string;
  descKey: string;
  gridClass: string;
}

const cards: CardData[] = [
  {
    target: 4,
    suffix: "+",
    titleKey: "bento.exchanges.title",
    descKey: "bento.exchanges.desc",
    gridClass: "bento-card-1 bento-card-wide",
  },
  {
    target: 8,
    suffix: "+",
    titleKey: "bento.models.title",
    descKey: "bento.models.desc",
    gridClass: "bento-card-2",
  },
  {
    target: 24,
    suffix: "/7",
    titleKey: "bento.automated.title",
    descKey: "bento.automated.desc",
    gridClass: "bento-card-3",
  },
  {
    target: 4,
    suffix: "",
    titleKey: "bento.consensus.title",
    descKey: "bento.consensus.desc",
    gridClass: "bento-card-4",
  },
];

function BentoCard({
  card,
  t,
}: {
  card: CardData;
  t: ReturnType<typeof useTranslations>;
}) {
  const cardRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const el = cardRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      el.style.setProperty("--glow-x", `${x}px`);
      el.style.setProperty("--glow-y", `${y}px`);
      el.style.setProperty("--glow-intensity", "1");
    },
    []
  );

  const handleMouseLeave = useCallback(() => {
    const el = cardRef.current;
    if (!el) return;
    el.style.setProperty("--glow-intensity", "0");
  }, []);

  return (
    <div
      ref={cardRef}
      className={`bento-card ${card.gridClass}`}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <AnimatedCounter
        target={card.target}
        suffix={card.suffix}
        className="text-gradient-animated block text-[3.5rem] font-extrabold leading-none sm:text-[4.5rem] lg:text-[5rem]"
        duration={1500}
      />
      <h3 className="mt-1 text-base font-semibold text-foreground sm:text-lg">
        {t(card.titleKey)}
      </h3>
      <p className="mt-0 text-sm leading-snug text-muted-foreground">
        {t(card.descKey)}
      </p>
    </div>
  );
}

export function FeatureCards() {
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
    <section className="relative z-22 px-4 py-20 sm:px-8 lg:-mt-16">
      <div className="mx-auto max-w-[1000px]">
        {/* Section header */}
        <div
          ref={sectionRef}
          className={`mb-16 text-center fade-in-section ${visible ? "visible" : ""}`}
        >
          <h2 className="section-title-rb text-gradient-animated inline-block">
            {t("bento.sectionTitle")}
          </h2>
          <p className="section-subtitle-rb mt-1 text-center">
            {t("bento.sectionSubtitle")}
          </p>
        </div>

        {/* Bento grid */}
        <div className="bento-grid">
          {cards.map((card, i) => (
            <BentoCard key={i} card={card} t={t} />
          ))}
        </div>
      </div>
    </section>
  );
}
