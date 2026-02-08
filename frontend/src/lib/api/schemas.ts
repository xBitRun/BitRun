/**
 * Zod schemas for API response validation.
 *
 * Validates API responses at runtime to catch backend contract changes early.
 * Only critical/high-frequency endpoints are validated; add more as needed.
 */

import { z } from 'zod';

// ==================== Auth ====================

export const LoginResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string(),
});

export const UserProfileSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  username: z.string(),
  created_at: z.string(),
});

// ==================== Strategies ====================

export const StrategySchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  status: z.string(),
  trading_mode: z.string(),
  prompt: z.string().optional(),
  description: z.string().optional(),
  account_id: z.string().uuid().nullable().optional(),
  config: z.record(z.unknown()).nullable().optional(),
  created_at: z.string(),
  updated_at: z.string().optional(),
  last_run_at: z.string().nullable().optional(),
  next_run_at: z.string().nullable().optional(),
});

export const StrategyListSchema = z.array(StrategySchema);

// ==================== Accounts ====================

export const AccountSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  exchange: z.string(),
  is_testnet: z.boolean(),
  is_active: z.boolean().optional(),
  created_at: z.string(),
});

export const AccountListSchema = z.array(AccountSchema);

// ==================== Dashboard ====================

export const DashboardStatsSchema = z.object({
  total_equity: z.number().optional(),
  daily_pnl: z.number().optional(),
  daily_pnl_percentage: z.number().optional(),
  active_strategies: z.number().optional(),
  total_strategies: z.number().optional(),
  active_positions: z.number().optional(),
  total_accounts: z.number().optional(),
});

// ==================== Validation Helper ====================

/**
 * Validate API response data against a Zod schema.
 *
 * In development: logs warnings for validation failures but still returns data.
 * In production: silently passes through (validation is best-effort).
 *
 * @param data - The API response data to validate
 * @param schema - Zod schema to validate against
 * @param context - Description of what's being validated (for logging)
 * @returns The original data (typed via schema)
 */
export function validateResponse<T>(
  data: unknown,
  schema: z.ZodSchema<T>,
  context: string = 'API response',
): T {
  const result = schema.safeParse(data);

  if (!result.success) {
    const isDev = process.env.NODE_ENV === 'development';
    if (isDev) {
      console.warn(
        `[API Validation] ${context} failed validation:`,
        result.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`),
      );
    }
    // Return original data even on failure (graceful degradation)
    return data as T;
  }

  return result.data;
}
