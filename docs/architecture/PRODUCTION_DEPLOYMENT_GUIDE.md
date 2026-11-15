# NEOMON Production Deployment Guide

## 1. System Architecture Overview

NEOMON is deployed as a resilient, decoupled micro-architecture:
- **Next.js Web Frontend** (Port 3000): Standalone Node.js container serving interactive collaborative UI, real-time dashboards, and evidence graphs.
- **FastAPI Core Backend** (Port 8000): High-performance asynchronous API engine handling authentication, RBAC, research workflows, and knowledge queries.
- **PostgreSQL 16+** (Port 5432): Durable ACID relational storage managing users, workspaces, investigations, claims, citations, and background job states.
- **Redis 7+** (Port 6379): In-memory distributed store for sliding-window rate limiting, token caching, and cross-worker signaling.
- **Asynchronous Background Worker**: Dedicated background process executing long-running autonomous research pipelines, evidence calibrations, and export generation with bounded concurrency.

---

## 2. Infrastructure Prerequisites

| Component | Minimum Specification | Recommended Production Spec |
| :--- | :--- | :--- |
| **CPU** | 2 vCPU | 4–8 vCPU |
| **Memory** | 4 GB RAM | 16 GB RAM |
| **Disk Storage** | 20 GB SSD | 100+ GB NVMe SSD |
| **Container Engine** | Docker Engine 24+ & Compose v2 | Kubernetes 1.28+ / Docker Swarm |
| **Database** | PostgreSQL 15+ | AWS Aurora PostgreSQL / Managed PG 16 |
| **Cache** | Redis 6.2+ | AWS ElastiCache / Redis 7+ Cluster |

---

## 3. Quickstart Deployment with Docker Compose

1. **Clone the Repository & Navigate to Root**:
   ```bash
   cd /opt/neomon
   ```

2. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   # Edit .env with production passwords, secrets, and domain names
   nano .env
   ```

3. **Build & Start Services**:
   ```bash
   docker compose build
   docker compose up -d
   ```

4. **Verify Health**:
   ```bash
   # Check container status
   docker compose ps

   # Probe backend health
   curl -f http://localhost:8000/api/v1/health

   # Probe system readiness
   curl -f http://localhost:8000/ready
   ```

---

## 4. Reverse Proxy & TLS Configuration (Nginx Example)

```nginx
server {
    listen 80;
    server_name neomon.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name neomon.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/neomon.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/neomon.yourdomain.com/privkey.pem;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # API and Health Endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }

    location /ready {
        proxy_pass http://127.0.0.1:8000/ready;
    }

    # Frontend UI
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 5. Kubernetes & Horizontal Pod Autoscaling (HPA)

For cloud native deployments, decouple stateless API pods from stateful worker pods:
- API Pods scale horizontally on CPU utilization (`targetAverageUtilization: 75%`).
- Worker Pods scale based on queue depth (`SELECT COUNT(*) FROM background_jobs WHERE status = 'queued'`).
- Always run database migrations as a Helm pre-install / pre-upgrade Job.
