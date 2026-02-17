"use client";

import { DarkVeil } from "./dark-veil";

interface DarkVeilBackgroundProps {
  /** 色相偏移角度，可通过 theme.effects?.darkVeilHueShift 传入 */
  hueShift?: number;
  /** 是否显示渐变叠加层，默认 true */
  showGradientBlur?: boolean;
}

/**
 * 封装 DarkVeil WebGL 背景组件
 * - 包含定位容器和渐变叠加层
 * - Auth Layout 和 Landing Page 可共用
 */
export function DarkVeilBackground({
  hueShift = 0,
  showGradientBlur = true,
}: DarkVeilBackgroundProps) {
  return (
    <>
      {/* WebGL DarkVeil background */}
      <div className="dark-veil-container">
        <DarkVeil
          hueShift={hueShift}
          noiseIntensity={0}
          scanlineIntensity={0}
          speed={0.5}
          scanlineFrequency={0}
          warpAmount={0}
          resolutionScale={1}
        />
      </div>

      {/* Gradient blur overlay */}
      {showGradientBlur && (
        <div className="landing-gradient-blur" aria-hidden="true" />
      )}
    </>
  );
}
