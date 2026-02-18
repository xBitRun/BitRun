"use client";

import { useEffect, useRef, useCallback } from "react";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  color: string;
  alpha: number;
  decay: number;
}

interface PixelBlastProps {
  colors?: string[];
  particleCount?: number;
  particleSize?: number;
  speed?: number;
  blastInterval?: number;
  gravity?: number;
  friction?: number;
  className?: string;
}

export function PixelBlast({
  colors = ["#6366f1", "#8b5cf6", "#a855f7", "#ec4899", "#06b6d4", "#10b981"],
  particleCount = 80,
  particleSize = 3,
  speed = 8,
  blastInterval = 800,
  gravity = 0.15,
  friction = 0.98,
  className = "",
}: PixelBlastProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animationRef = useRef<number | null>(null);
  const particlesRef = useRef<Particle[]>([]);
  const lastBlastRef = useRef<number>(0);
  const dimensionsRef = useRef({ width: 0, height: 0 });

  const getRandomColor = useCallback(() => {
    return colors[Math.floor(Math.random() * colors.length)];
  }, [colors]);

  const createBlast = useCallback(
    (x: number, y: number) => {
      for (let i = 0; i < particleCount; i++) {
        const angle = Math.random() * Math.PI * 2;
        const velocity = speed * (0.3 + Math.random() * 0.7);
        const size = particleSize * (0.5 + Math.random() * 1.5);

        particlesRef.current.push({
          x,
          y,
          vx: Math.cos(angle) * velocity * (0.5 + Math.random()),
          vy: Math.sin(angle) * velocity * (0.5 + Math.random()),
          size,
          color: getRandomColor(),
          alpha: 1,
          decay: 0.012 + Math.random() * 0.018,
        });
      }
    },
    [particleCount, particleSize, speed, getRandomColor]
  );

  const animateFnRef = useRef<() => void>(() => {});

  const animate = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    const { width, height } = dimensionsRef.current;

    if (!canvas || !ctx || !width || !height) {
      animationRef.current = requestAnimationFrame(animateFnRef.current);
      return;
    }

    // Clear canvas with slight trail effect
    ctx.fillStyle = "rgba(9, 9, 11, 0.15)";
    ctx.fillRect(0, 0, width, height);

    // Auto blast
    const now = Date.now();
    if (now - lastBlastRef.current > blastInterval) {
      const x = width * 0.15 + Math.random() * width * 0.7;
      const y = height * 0.15 + Math.random() * height * 0.7;
      createBlast(x, y);
      lastBlastRef.current = now;
    }

    // Update and draw particles
    particlesRef.current = particlesRef.current.filter((p) => {
      // Physics
      p.vy += gravity;
      p.vx *= friction;
      p.vy *= friction;
      p.x += p.vx;
      p.y += p.vy;
      p.alpha -= p.decay;

      if (p.alpha <= 0) return false;

      // Draw pixel
      ctx.save();
      ctx.globalAlpha = p.alpha;
      ctx.fillStyle = p.color;

      // Pixelated effect - snap to grid
      const px = Math.floor(p.x / particleSize) * particleSize;
      const py = Math.floor(p.y / particleSize) * particleSize;
      ctx.fillRect(px, py, p.size, p.size);

      // Add glow effect
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 8;
      ctx.fillRect(px, py, p.size, p.size);

      ctx.restore();

      return true;
    });

    animationRef.current = requestAnimationFrame(animateFnRef.current);
  }, [blastInterval, createBlast, gravity, friction, particleSize]);

  // Update animateFnRef in effect to avoid render-phase ref update
  useEffect(() => {
    animateFnRef.current = animate;
  }, [animate]);

  const handleResize = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;

    if (!canvas || !container) return;

    const rect = container.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;

    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.scale(dpr, dpr);
    }

    dimensionsRef.current = { width: rect.width, height: rect.height };

    // Initial blasts
    particlesRef.current = [];
    for (let i = 0; i < 5; i++) {
      setTimeout(() => {
        if (dimensionsRef.current.width && dimensionsRef.current.height) {
          createBlast(
            dimensionsRef.current.width * 0.2 + Math.random() * dimensionsRef.current.width * 0.6,
            dimensionsRef.current.height * 0.2 + Math.random() * dimensionsRef.current.height * 0.6
          );
        }
      }, i * 150);
    }
  }, [createBlast]);

  useEffect(() => {
    handleResize();
    window.addEventListener("resize", handleResize);
    animationRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [handleResize, animate]);

  return (
    <div ref={containerRef} className={`absolute inset-0 overflow-hidden ${className}`}>
      <canvas
        ref={canvasRef}
        className="block w-full h-full"
        style={{ background: "rgb(9, 9, 11)" }}
      />
    </div>
  );
}
