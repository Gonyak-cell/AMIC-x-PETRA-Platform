# =============================================================
# AMIC x PETRA Platform — Frontend Production Dockerfile
# =============================================================
# Multi-stage build: Node (build) → Nginx (serve SPA)
# Usage: docker build -t amic-frontend .
# =============================================================

# --- Stage 1: Build ---
FROM node:20-alpine AS builder

WORKDIR /app

# 의존성 캐싱 최적화 (package*.json만 먼저 복사)
COPY package.json package-lock.json ./
RUN npm ci --prefer-offline --no-audit

# 소스 코드 복사 및 빌드
COPY . .
RUN npm run build

# --- Stage 2: Serve ---
FROM nginx:1.25-alpine

# 빌드된 SPA 복사
COPY --from=builder /app/dist /usr/share/nginx/html

# SPA 라우팅 + 캐싱 설정
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1/index.html || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
