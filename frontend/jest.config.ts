import type { Config } from "jest";
import nextJest from "next/jest";

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files
  dir: "./",
});

const config: Config = {
  // Add more setup options before each test is run
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  
  // Test environment
  testEnvironment: "jsdom",
  
  // Module name mapper for path aliases
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
  },
  
  // Test file patterns
  testMatch: [
    "<rootDir>/src/**/*.test.{ts,tsx}",
    "<rootDir>/tests/**/*.test.{ts,tsx}",
  ],
  
  // Coverage reporters (json-summary for CI summary)
  coverageReporters: ["json", "json-summary", "lcov", "text"],

  // Coverage configuration
  collectCoverageFrom: [
    "src/**/*.{ts,tsx}",
    "!src/**/*.d.ts",
    "!src/**/index.ts",
    "!src/app/**/layout.tsx",
    "!src/app/**/loading.tsx",
    "!src/app/**/error.tsx",
    "!src/app/**/not-found.tsx",
    "!src/app/**/page.tsx",
    "!src/app/**/global-error.tsx",
    "!src/components/ui/**",
    "!src/components/landing/**",  // 营销页，无核心业务逻辑
    "!src/components/charts/tradingview-chart.tsx",  // 第三方 TradingView widget
    "!src/i18n/**",
    "!src/providers/**",
    "!src/messages/**",
    "!src/**/*.config.*",
  ],
  
  // Coverage thresholds (progressive - raise as coverage improves)
  coverageThreshold: {
    global: {
      branches: 55,
      functions: 65,
      lines: 70,
      statements: 70,
    },
  },
  
  // Transform configuration
  transform: {
    "^.+\\.(ts|tsx)$": ["ts-jest", { useESM: true }],
  },
  
  // Module file extensions
  moduleFileExtensions: ["ts", "tsx", "js", "jsx", "json", "node"],
  
  // Ignore patterns
  testPathIgnorePatterns: [
    "<rootDir>/node_modules/",
    "<rootDir>/.next/",
    "<rootDir>/.next/standalone/",
    "<rootDir>/e2e/",
  ],

  modulePathIgnorePatterns: ["<rootDir>/.next/standalone/"],
  
  // Transform ignore patterns
  transformIgnorePatterns: [
    "/node_modules/(?!(react-markdown|remark-gfm|unified|unist-util|vfile|mdast|micromark|hast|rehype|rehype-react)/)",
    "^.+\\.module\\.(css|sass|scss)$",
  ],
};

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
export default createJestConfig(config);
