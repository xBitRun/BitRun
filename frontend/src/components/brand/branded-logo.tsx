"use client";

import Image from "next/image";
import { cn } from "@/lib/utils";
import { useBrand } from "@/lib/brand-context";

export interface BrandedLogoProps {
  variant?: "default" | "compact" | "icon";
  className?: string;
  width?: number;
  height?: number;
  priority?: boolean;
}

/**
 * Smart logo component that automatically uses brand configuration
 * - If logo image is configured, displays the image
 * - If no logo image, displays text-only logo using brand name/shortName
 */
export function BrandedLogo({
  variant = "default",
  className,
  width = 160,
  height = 48,
  priority = false,
}: BrandedLogoProps) {
  const { getLogoSrc, getLogoAlt, name, shortName } = useBrand();
  const logoSrc = getLogoSrc(variant);

  // No logo image configured, use text-only logo
  if (!logoSrc) {
    const displayName =
      variant === "icon" || variant === "compact" ? shortName : name;

    return (
      <span
        className={cn(
          "font-extrabold tracking-tight text-white",
          "text-lg sm:text-xl",
          className,
        )}
        aria-label={getLogoAlt()}
      >
        {displayName}
      </span>
    );
  }

  // Logo image configured, display the image
  // At this point logoSrc is guaranteed to be a string (not null)
  const imageSrc: string = logoSrc;

  return (
    <Image
      src={imageSrc}
      alt={getLogoAlt()}
      width={width}
      height={height}
      className={cn("h-full w-auto", className)}
      priority={priority}
    />
  );
}

// Export named variants for convenience
export const Logo = BrandedLogo;

export function LogoCompact(
  props: Omit<BrandedLogoProps, "variant"> & { className?: string },
) {
  return <BrandedLogo {...props} variant="compact" />;
}

export function LogoIcon(
  props: Omit<BrandedLogoProps, "variant"> & { className?: string },
) {
  return <BrandedLogo {...props} variant="icon" />;
}
