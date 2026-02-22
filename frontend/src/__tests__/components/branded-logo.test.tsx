/**
 * Tests for BrandedLogo component
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import {
  BrandedLogo,
  Logo,
  LogoCompact,
  LogoIcon,
} from "@/components/brand/branded-logo";

// Mock next/image
jest.mock("next/image", () => ({
  __esModule: true,
  default: ({
    src,
    alt,
    width,
    height,
    className,
  }: {
    src: string;
    alt: string;
    width: number;
    height: number;
    className?: string;
  }) => (
    <img
      src={src}
      alt={alt}
      width={width}
      height={height}
      className={className}
      data-testid="logo-image"
    />
  ),
}));

// Mock brand-context
const mockGetLogoSrc = jest.fn();
const mockGetLogoAlt = jest.fn(() => "Test Brand");

jest.mock("@/lib/brand-context", () => ({
  useBrand: () => ({
    getLogoSrc: mockGetLogoSrc,
    getLogoAlt: mockGetLogoAlt,
    name: "Test Brand Name",
    shortName: "TBN",
  }),
}));

describe("BrandedLogo", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("text-only logo (no image)", () => {
    it("renders text logo when no image configured", () => {
      mockGetLogoSrc.mockReturnValue(null);

      render(<BrandedLogo />);

      expect(screen.getByText("Test Brand Name")).toBeInTheDocument();
    });

    it("uses shortName for compact variant", () => {
      mockGetLogoSrc.mockReturnValue(null);

      render(<BrandedLogo variant="compact" />);

      expect(screen.getByText("TBN")).toBeInTheDocument();
    });

    it("uses shortName for icon variant", () => {
      mockGetLogoSrc.mockReturnValue(null);

      render(<BrandedLogo variant="icon" />);

      expect(screen.getByText("TBN")).toBeInTheDocument();
    });

    it("applies custom className to text logo", () => {
      mockGetLogoSrc.mockReturnValue(null);

      render(<BrandedLogo className="custom-text-logo" />);

      const text = screen.getByText("Test Brand Name");
      expect(text).toHaveClass("custom-text-logo");
    });

    it("has aria-label for accessibility", () => {
      mockGetLogoSrc.mockReturnValue(null);

      render(<BrandedLogo />);

      const text = screen.getByText("Test Brand Name");
      expect(text).toHaveAttribute("aria-label", "Test Brand");
    });
  });

  describe("image logo", () => {
    it("renders image when logo source configured", () => {
      mockGetLogoSrc.mockReturnValue("/logo.svg");

      render(<BrandedLogo />);

      expect(screen.getByTestId("logo-image")).toBeInTheDocument();
      expect(screen.getByAltText("Test Brand")).toBeInTheDocument();
    });

    it("passes width and height to image", () => {
      mockGetLogoSrc.mockReturnValue("/logo.svg");

      render(<BrandedLogo width={200} height={60} />);

      const img = screen.getByTestId("logo-image");
      expect(img).toHaveAttribute("width", "200");
      expect(img).toHaveAttribute("height", "60");
    });

    it("uses default width and height", () => {
      mockGetLogoSrc.mockReturnValue("/logo.svg");

      render(<BrandedLogo />);

      const img = screen.getByTestId("logo-image");
      expect(img).toHaveAttribute("width", "160");
      expect(img).toHaveAttribute("height", "48");
    });

    it("applies custom className to image", () => {
      mockGetLogoSrc.mockReturnValue("/logo.svg");

      render(<BrandedLogo className="custom-image-logo" />);

      const img = screen.getByTestId("logo-image");
      expect(img).toHaveClass("custom-image-logo");
    });

    it("requests compact variant logo source", () => {
      mockGetLogoSrc.mockReturnValue("/logo-compact.svg");

      render(<BrandedLogo variant="compact" />);

      expect(mockGetLogoSrc).toHaveBeenCalledWith("compact");
    });

    it("requests icon variant logo source", () => {
      mockGetLogoSrc.mockReturnValue("/logo-icon.svg");

      render(<BrandedLogo variant="icon" />);

      expect(mockGetLogoSrc).toHaveBeenCalledWith("icon");
    });
  });
});

describe("Logo (alias)", () => {
  it("is an alias for BrandedLogo", () => {
    mockGetLogoSrc.mockReturnValue(null);

    render(<Logo />);

    expect(screen.getByText("Test Brand Name")).toBeInTheDocument();
  });
});

describe("LogoCompact", () => {
  it("renders with compact variant", () => {
    mockGetLogoSrc.mockReturnValue(null);

    render(<LogoCompact />);

    expect(screen.getByText("TBN")).toBeInTheDocument();
  });

  it("passes through other props", () => {
    mockGetLogoSrc.mockReturnValue("/logo-compact.svg");

    render(<LogoCompact width={100} height={40} className="compact-class" />);

    expect(mockGetLogoSrc).toHaveBeenCalledWith("compact");
    const img = screen.getByTestId("logo-image");
    expect(img).toHaveAttribute("width", "100");
    expect(img).toHaveClass("compact-class");
  });
});

describe("LogoIcon", () => {
  it("renders with icon variant", () => {
    mockGetLogoSrc.mockReturnValue(null);

    render(<LogoIcon />);

    expect(screen.getByText("TBN")).toBeInTheDocument();
  });

  it("passes through other props", () => {
    mockGetLogoSrc.mockReturnValue("/logo-icon.svg");

    render(<LogoIcon width={32} height={32} className="icon-class" />);

    expect(mockGetLogoSrc).toHaveBeenCalledWith("icon");
    const img = screen.getByTestId("logo-image");
    expect(img).toHaveAttribute("width", "32");
    expect(img).toHaveClass("icon-class");
  });
});
