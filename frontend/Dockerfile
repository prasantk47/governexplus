FROM node:20-alpine AS builder

WORKDIR /app

# Allow overriding VITE_API_URL at build time.
# Leave empty so api.ts falls back to /api (proxied by nginx).
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the app (skip TypeScript check, use Vite only)
RUN npx vite build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Allow switching between nginx configs at build time (default: nginx.conf)
ARG NGINX_CONF=nginx.conf
COPY ${NGINX_CONF} /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
