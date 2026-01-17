# Story 4.10: Production Build, Docker & CI/CD Integration

Status: done

## Story

As a developer,
I want to create an optimized production build with proper Docker setup and CI/CD pipeline,
So that the application deploys automatically when pushing to prod branch with proper persistence and routing.

## Acceptance Criteria

1. **AC1: Vite Production Config** - vite.config.ts has production optimizations (manualChunks, minify, no sourcemaps)
2. **AC2: Nginx Configuration** - nginx.conf with gzip compression, static asset caching, and SPA fallback
3. **AC3: Multi-stage Dockerfile** - Dockerfile uses multi-stage build with nginx (not serve)
4. **AC4: Docker Compose Production** - docker-compose.yml configured for production with external Traefik network
5. **AC5: Volume Persistence** - Postgres data persisted to /mnt/data/meteo-score/postgres_data
6. **AC6: GitHub Actions CI/CD** - .github/workflows/deploy.yml deploys on push to prod branch
7. **AC7: Traefik Labels** - Frontend and backend have proper Traefik labels for HTTPS routing
8. **AC8: Build Validation** - Production build succeeds without errors
9. **AC9: SPA Routing** - Nginx try_files ensures SPA routing works for all frontend routes

## Tasks / Subtasks

- [x] Task 1: Optimize vite.config.ts for production (AC: 1)
  - [x] 1.1: Add manualChunks for vendor (solid-js, @solidjs/router) and d3
  - [x] 1.2: Set sourcemap: false for production
  - [x] 1.3: Configure minify: 'esbuild' and chunkSizeWarningLimit

- [x] Task 2: Create nginx.conf for static file serving (AC: 2, 9)
  - [x] 2.1: Configure gzip compression for text/js/css/json
  - [x] 2.2: Set up cache headers for static assets (1 year, immutable)
  - [x] 2.3: Configure try_files for SPA routing fallback to index.html
  - [x] 2.4: Add /api/ proxy pass to backend:8000

- [x] Task 3: Update frontend Dockerfile for nginx (AC: 3)
  - [x] 3.1: Update build stage to use node:20-alpine
  - [x] 3.2: Change production stage from serve to nginx:alpine
  - [x] 3.3: Copy built files to /usr/share/nginx/html
  - [x] 3.4: Copy nginx.conf to /etc/nginx/conf.d/default.conf
  - [x] 3.5: Expose port 80

- [x] Task 4: Rewrite docker-compose.yml for production (AC: 4, 5, 7)
  - [x] 4.1: Use external traefik_default network (remove built-in traefik service)
  - [x] 4.2: Configure postgres volume to /mnt/data/meteo-score/postgres_data
  - [x] 4.3: Add Traefik labels for frontend (Host rule, websecure, letsencrypt)
  - [x] 4.4: Add Traefik labels for backend API (/api path prefix)
  - [x] 4.5: Remove adminer service (not needed in production)
  - [x] 4.6: Update healthchecks for nginx (port 80)

- [x] Task 5: Create GitHub Actions workflow (AC: 6)
  - [x] 5.1: Create .github/workflows/deploy.yml
  - [x] 5.2: Trigger on push to prod branch
  - [x] 5.3: SSH to VPS and pull latest code
  - [x] 5.4: Build and restart services with zero-downtime rolling update
  - [x] 5.5: Prune old Docker images

- [x] Task 6: Verification (AC: 8)
  - [x] 6.1: Run `npm run build` - no errors
  - [x] 6.2: Run `npm run type-check` - no errors
  - [x] 6.3: Validate docker-compose.yml syntax

## Dev Notes

### Current Implementation State

**ALREADY EXISTS:**

1. **vite.config.ts** (`frontend/vite.config.ts`):
   - Basic config with solid plugin
   - Dev server proxy for /api
   - Build target: esnext, sourcemap: true (needs to be false for prod)
   - NO production optimizations (no manualChunks)

2. **Dockerfile** (`frontend/Dockerfile`):
   - Multi-stage build exists BUT uses `serve` package
   - Uses node:18-alpine (should update to node:20-alpine)
   - Exposes port 3000 (should be 80 with nginx)

3. **docker-compose.yml** (project root):
   - Has built-in traefik service (REMOVE - use external)
   - Has adminer service (REMOVE - not for production)
   - Uses local volumes (CHANGE to /mnt/data path)
   - Frontend on port 3000 (CHANGE to nginx on 80)

4. **nginx.conf** - DOES NOT EXIST (needs creation)

5. **.github/workflows/** - DOES NOT EXIST (needs creation)

### Reference: sarouels-mocassins Pattern

**GitHub Actions (deploy.yml):**
```yaml
name: Deploy Prod

on:
  push:
    branches:
      - prod

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: SSH Deploy
        uses: appleboy/ssh-action@v0.1.7
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ubuntu
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /mnt/data/meteo-score
            git fetch origin
            git reset --hard origin/prod

            docker compose build

            services=$(docker compose config --services)
            for service in $services; do
              echo "Updating $service..."
              docker compose up -d --no-deps $service
              sleep 5
            done

            docker image prune -f
```

**Docker Compose Pattern (External Traefik):**
```yaml
version: '3.8'

services:
  postgres:
    image: timescale/timescaledb:latest-pg15
    volumes:
      - /mnt/data/meteo-score/postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - traefik_default
    # NO ports exposed externally

  backend:
    build: ./backend
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - traefik_default
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.meteo-api.rule=Host(`meteo-score.codeas.me`) && PathPrefix(`/api`)"
      - "traefik.http.routers.meteo-api.entrypoints=websecure"
      - "traefik.http.routers.meteo-api.tls.certresolver=letsencrypt"
      - "traefik.http.services.meteo-api.loadbalancer.server.port=8000"

  frontend:
    build: ./frontend
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - traefik_default
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.meteo-frontend.rule=Host(`meteo-score.codeas.me`)"
      - "traefik.http.routers.meteo-frontend.entrypoints=websecure"
      - "traefik.http.routers.meteo-frontend.tls.certresolver=letsencrypt"
      - "traefik.http.services.meteo-frontend.loadbalancer.server.port=80"

networks:
  traefik_default:
    external: true
```

### File Structure After Implementation

```
meteo-score/
├── .github/
│   └── workflows/
│       └── deploy.yml       # CREATE: GitHub Actions CI/CD
├── docker-compose.yml       # REWRITE: Production config with external Traefik
├── frontend/
│   ├── Dockerfile           # MODIFY: nginx instead of serve
│   ├── nginx.conf           # CREATE: nginx configuration
│   └── vite.config.ts       # MODIFY: production optimizations
└── backend/
    └── ...                  # NO CHANGES
```

### Vite Config Pattern (Final)

```typescript
import { defineConfig } from 'vite';
import solid from 'vite-plugin-solid';

export default defineConfig({
  plugins: [solid()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    target: 'esnext',
    minify: 'esbuild',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['solid-js', '@solidjs/router'],
          d3: ['d3'],
        },
      },
    },
    chunkSizeWarningLimit: 1000,
  },
  resolve: {
    conditions: ['development', 'browser'],
  },
});
```

### Nginx Config Pattern

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml;

    # Cache static assets (1 year for fingerprinted files)
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA fallback - serve index.html for all routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to backend (fallback if Traefik doesn't handle)
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Dockerfile Pattern (Nginx)

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### GitHub Secrets Required

The following secrets must be configured in GitHub repository settings:
- `VPS_HOST`: IP address or hostname of the VPS
- `VPS_SSH_KEY`: Private SSH key for authentication

### Domain Configuration

- **Domain**: meteo-score.codeas.me (to be configured)
- **SSL**: Automatic via Let's Encrypt through external Traefik
- **Entrypoint**: websecure (HTTPS on port 443)

### Volume Persistence

PostgreSQL data will be stored at `/mnt/data/meteo-score/postgres_data` on the VPS.
This path must exist and be writable by the Docker daemon.

### Testing Approach

1. **Build Test**: `npm run build` succeeds without errors
2. **Type Check**: `npm run type-check` passes
3. **Docker Compose Validation**: `docker compose config` validates syntax
4. **Local Test** (optional): Run `docker compose up` locally to verify services start

### Previous Story Learnings (from 4-9)

1. Navigation now says "Methodology" instead of "About"
2. External links have visual indicators (SVG icons)
3. TypeScript and ESLint checks should pass

### References

- [Source: ~/dev/sarouels-mocassins/.github/workflows/deploy.yml - CI/CD pattern]
- [Source: ~/dev/sarouels-mocassins/docker-compose.yml - External Traefik pattern]
- [Source: frontend/vite.config.ts - Current config]
- [Source: frontend/Dockerfile - Current Dockerfile with serve]
- [Source: docker-compose.yml - Current compose config to be replaced]

## Change Log

- 2026-01-17: Story created with comprehensive context for production build implementation
- 2026-01-17: Story updated to include GitHub Actions CI/CD, external Traefik, and volume persistence
- 2026-01-17: Implementation completed - all production infrastructure configured

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - implementation proceeded without issues.

### Completion Notes List

1. **Vite Production Config**: Added manualChunks for vendor and d3, disabled sourcemaps, configured esbuild minification.

2. **Nginx Configuration**: Created nginx.conf with gzip compression, 1-year cache headers for static assets, SPA try_files fallback, and /api/ proxy pass.

3. **Dockerfile Updated**: Switched from serve to nginx:alpine, updated to node:20-alpine for build stage, exposes port 80.

4. **Docker Compose Rewritten**:
   - Removed built-in traefik and adminer services
   - Uses external traefik_default network
   - PostgreSQL volume mapped to /mnt/data/meteo-score/postgres_data
   - Frontend and backend with proper Traefik labels (websecure, letsencrypt)
   - Host rule: meteo-score.codeas.me

5. **GitHub Actions CI/CD**: Created .github/workflows/deploy.yml with SSH deployment on push to prod branch, zero-downtime rolling updates, and image pruning.

6. **Build Results**:
   - TypeScript: PASS (0 errors)
   - Production Build: PASS
   - Bundle Size: ~52.72 KB gzipped (well under 500KB limit)
     - vendor.js: 11.62 KB (solid-js, @solidjs/router)
     - d3.js: 23.89 KB
     - index.js: 11.74 KB (app code)
     - index.css: 5.06 KB

### File List

- **frontend/vite.config.ts** - MODIFIED: Added production optimizations (manualChunks, sourcemap:false, minify)
- **frontend/nginx.conf** - CREATED: Nginx configuration with gzip, caching, SPA fallback
- **frontend/Dockerfile** - MODIFIED: Changed from serve to nginx:alpine
- **docker-compose.yml** - REWRITTEN: External Traefik, volume persistence, proper labels
- **.github/workflows/deploy.yml** - CREATED: CI/CD workflow for prod deployments
- **frontend/.dockerignore** - CREATED: Docker build context optimization

## Senior Developer Review

### Review Date
2026-01-17

### Issues Found and Fixed

#### CRITICAL Issues (2)

**C1: Frontend healthcheck uses wget but nginx:alpine doesn't have it**
- Location: docker-compose.yml:62, frontend/Dockerfile
- Problem: nginx:alpine image doesn't include wget, causing healthcheck to always fail
- Fix: Added `RUN apk add --no-cache curl` to Dockerfile, changed healthcheck to use curl

**C2: Backend healthcheck uses wrong endpoint path**
- Location: docker-compose.yml:38
- Problem: Healthcheck used `/api/health` but the FastAPI endpoint is mounted at `/health` (no /api prefix internally)
- Fix: Changed healthcheck to `curl -f http://localhost:8000/health`

#### MEDIUM Issues (2)

**M1: Missing .dockerignore for frontend**
- Location: frontend/
- Problem: No .dockerignore means node_modules and other unnecessary files get copied to build context
- Fix: Created frontend/.dockerignore excluding node_modules, dist, .git, logs, env files, test coverage

**M2: Traefik router priority not set**
- Location: docker-compose.yml
- Problem: Frontend catch-all Host rule could intercept /api requests before the more specific API router
- Fix: Added priority labels - API router: 100, Frontend router: 10

#### LOW Issues (1)

**L1: Missing gzip_proxied directive**
- Location: frontend/nginx.conf
- Problem: Gzip compression may not work for proxied requests behind Traefik
- Fix: Added `gzip_proxied any;` directive

### Post-Review Verification
- All fixes applied successfully
- Docker compose syntax validated
- Production build still succeeds

