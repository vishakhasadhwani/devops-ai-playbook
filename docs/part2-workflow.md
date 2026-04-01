# Part 2 — The DevOps Workflow: Local to Cloud

> Companion doc for the YouTube series: **DevOps Practice Guide** — Episode 2

---

## Overview

This episode traces the full journey of a code change — from a developer's laptop all the way to a cloud-hosted Kubernetes cluster, with pipelines and observability at every step.

---

## Stage 1: Local Development

### Run the Stack Locally
The project uses Docker Compose to spin up all services together.

```bash
cd projects/fullstack-cicd-pipeline
docker compose up --build
```

Services started:
- **Frontend** — React app
- **Backend** — Node.js API
- **Database** — PostgreSQL
- **Prometheus** — metrics scraping
- **Grafana** — dashboards (localhost:3000)

### Health Check
```bash
./health-check.sh
```

---

## Stage 2: Source Control & Pull Requests

1. Create a feature branch: `git checkout -b feature/my-change`
2. Make changes, commit with a clear message
3. Push and open a Pull Request on GitHub
4. PR triggers the CI pipeline automatically

---

## Stage 3: CI Pipeline (GitHub Actions)

Located at `.github/workflows/ci.yml`.

```
Code Push
   │
   ▼
Lint & Static Analysis
   │
   ▼
Unit & Integration Tests
   │
   ▼
Docker Build & Image Scan
   │
   ▼
Push Image to Registry (GHCR / DockerHub)
   │
   ▼
Notify / Gate for CD
```

Key pipeline concepts:
- **Triggers**: `push` to `main`, `pull_request`
- **Jobs**: run in parallel or sequentially
- **Secrets**: credentials stored in GitHub Secrets, never in code
- **Artifacts**: Docker images tagged with the commit SHA

---

## Stage 4: CD Pipeline — Deploy to Kubernetes

After CI passes, the CD pipeline:

1. Updates the image tag in the Kubernetes manifests (`gitops/k8s/`)
2. ArgoCD detects the change in the Git repo (GitOps pattern)
3. ArgoCD syncs the desired state to the cluster

```
Git Repo (source of truth)
        │
        ▼
    ArgoCD
        │
        ▼
  Kubernetes Cluster
  ┌─────────────────────────────┐
  │  Namespace: devops-guide    │
  │  Deployments, Services,     │
  │  Ingress, Secrets           │
  └─────────────────────────────┘
```

ArgoCD config: `gitops/argo-cd.yml`
Kustomize overlay: `gitops/kustomization.yml`

---

## Stage 5: Observability

Once deployed, three layers of observability keep watch:

### Metrics — Prometheus + Grafana
- Prometheus scrapes `/metrics` endpoints from all services
- Grafana visualises CPU, memory, request rate, error rate
- Config: `projects/fullstack-cicd-pipeline/prometheus/`

### Logs
- Application logs are structured (JSON) for easy querying
- In production these feed into an ELK stack or cloud logging (CloudWatch, GCP Logging)

### Alerts
- Prometheus Alertmanager fires alerts when thresholds are breached
- Example: error rate > 5% for 2 minutes → page on-call

---

## Environment Promotion Flow

```
Local (docker compose)
        │
        ▼
   Dev (k8s namespace)
        │
        ▼
  Staging (k8s namespace)
        │
        ▼
 Production (k8s cluster)
```

Each promotion is gated by tests and (for staging → prod) a manual approval step in the pipeline.

---

## Key Files Referenced

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Local multi-service stack |
| `.github/workflows/ci.yml` | GitHub Actions CI pipeline |
| `gitops/argo-cd.yml` | ArgoCD application definition |
| `gitops/k8s/` | Kubernetes manifests |
| `gitops/kustomization.yml` | Kustomize config for overlays |
| `projects/fullstack-cicd-pipeline/prometheus/` | Prometheus scrape config |

---

## Where to Go Next
- [Part 1 — Beginner Concepts](./part1-beginner-concepts.md)
- [Part 3 — Project Demo](./part3-demo.md): hands-on walkthrough of deploying this project
