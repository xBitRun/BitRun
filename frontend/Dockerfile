# BITRUN Frontend Dockerfile
# Next.js application with multi-stage build for production

# ==================== Dependencies Stage ====================
FROM node:20-alpine AS deps
WORKDIR /app

# Install dependencies for native modules
RUN apk add --no-cache libc6-compat

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci --legacy-peer-deps

# ==================== Builder Stage ====================
FROM node:20-alpine AS builder
WORKDIR /app

# Set build-time environment
ENV NEXT_TELEMETRY_DISABLED=1

# NEXT_PUBLIC_* variables are embedded at build time by Next.js.
# Pass via Docker build args (Railway auto-injects env vars as build args).
# API Configuration
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL

# Brand Identity
ARG NEXT_PUBLIC_BRAND_NAME
ARG NEXT_PUBLIC_BRAND_SHORT_NAME
ARG NEXT_PUBLIC_BRAND_TAGLINE
ARG NEXT_PUBLIC_BRAND_DESCRIPTION

# Brand Assets
ARG NEXT_PUBLIC_BRAND_LOGO_DEFAULT
ARG NEXT_PUBLIC_BRAND_LOGO_COMPACT
ARG NEXT_PUBLIC_BRAND_LOGO_ICON
ARG NEXT_PUBLIC_BRAND_FAVICON

# Brand Theme
ARG NEXT_PUBLIC_BRAND_THEME_PRESET
ARG NEXT_PUBLIC_BRAND_THEME_COLORS_OVERRIDE

# Brand Legal
ARG NEXT_PUBLIC_BRAND_COPYRIGHT_HOLDER
ARG NEXT_PUBLIC_BRAND_TERMS_URL
ARG NEXT_PUBLIC_BRAND_PRIVACY_URL

# Brand Links
ARG NEXT_PUBLIC_BRAND_HOMEPAGE_URL
ARG NEXT_PUBLIC_BRAND_DOCS_URL
ARG NEXT_PUBLIC_BRAND_SUPPORT_URL

# Set environment variables for build
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_BRAND_NAME=$NEXT_PUBLIC_BRAND_NAME
ENV NEXT_PUBLIC_BRAND_SHORT_NAME=$NEXT_PUBLIC_BRAND_SHORT_NAME
ENV NEXT_PUBLIC_BRAND_TAGLINE=$NEXT_PUBLIC_BRAND_TAGLINE
ENV NEXT_PUBLIC_BRAND_DESCRIPTION=$NEXT_PUBLIC_BRAND_DESCRIPTION
ENV NEXT_PUBLIC_BRAND_LOGO_DEFAULT=$NEXT_PUBLIC_BRAND_LOGO_DEFAULT
ENV NEXT_PUBLIC_BRAND_LOGO_COMPACT=$NEXT_PUBLIC_BRAND_LOGO_COMPACT
ENV NEXT_PUBLIC_BRAND_LOGO_ICON=$NEXT_PUBLIC_BRAND_LOGO_ICON
ENV NEXT_PUBLIC_BRAND_FAVICON=$NEXT_PUBLIC_BRAND_FAVICON
ENV NEXT_PUBLIC_BRAND_THEME_PRESET=$NEXT_PUBLIC_BRAND_THEME_PRESET
ENV NEXT_PUBLIC_BRAND_THEME_COLORS_OVERRIDE=$NEXT_PUBLIC_BRAND_THEME_COLORS_OVERRIDE
ENV NEXT_PUBLIC_BRAND_COPYRIGHT_HOLDER=$NEXT_PUBLIC_BRAND_COPYRIGHT_HOLDER
ENV NEXT_PUBLIC_BRAND_TERMS_URL=$NEXT_PUBLIC_BRAND_TERMS_URL
ENV NEXT_PUBLIC_BRAND_PRIVACY_URL=$NEXT_PUBLIC_BRAND_PRIVACY_URL
ENV NEXT_PUBLIC_BRAND_HOMEPAGE_URL=$NEXT_PUBLIC_BRAND_HOMEPAGE_URL
ENV NEXT_PUBLIC_BRAND_DOCS_URL=$NEXT_PUBLIC_BRAND_DOCS_URL
ENV NEXT_PUBLIC_BRAND_SUPPORT_URL=$NEXT_PUBLIC_BRAND_SUPPORT_URL

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build the application
RUN npm run build

# ==================== Development Stage ====================
FROM node:20-alpine AS development
WORKDIR /app

ENV NODE_ENV=development \
    NEXT_TELEMETRY_DISABLED=1

# Install dependencies for native modules
RUN apk add --no-cache libc6-compat

# Copy package files
COPY package.json package-lock.json* ./

# Install all dependencies (including devDependencies)
RUN npm install --legacy-peer-deps

# Copy application code
COPY . .

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs && \
    mkdir -p /app/.next && \
    chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000
ENV HOSTNAME="0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

CMD ["npm", "run", "dev"]

# ==================== Production Stage ====================
FROM node:20-alpine AS production
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

# Install runtime dependencies only
RUN apk add --no-cache libc6-compat

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built application from builder
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV HOSTNAME="0.0.0.0"

# Health check (use PORT env var, Railway sets it dynamically)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT:-3000} || exit 1

# Production server
CMD ["node", "server.js"]
