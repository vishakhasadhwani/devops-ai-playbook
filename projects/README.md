# Boutique Microservices — Deployment Guide

This guide walks through the full deployment of the boutique e-commerce application — from running it locally with Docker, to provisioning AWS infrastructure with Terraform, to running it on Kubernetes with a full CI/CD pipeline, GitOps, and observability stack.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Local Development with Docker](#local-development-with-docker)
3. [Infrastructure Provisioning on AWS](#infrastructure-provisioning-on-aws)
4. [From Docker to Kubernetes](#from-docker-to-kubernetes)
5. [Setting Up the CI/CD Pipeline](#setting-up-the-cicd-pipeline)
6. [Setting Up ArgoCD (GitOps)](#setting-up-argocd-gitops)
7. [Setting Up Observability](#setting-up-observability)
8. [Port Forwarding Reference](#port-forwarding-reference)
9. [Credentials](#credentials)
10. [Cleanup](#cleanup)

---

## Architecture Overview

```
                                    ┌─────────────┐
                                    │   Frontend  │
                                    │ (Port 3000) │
                                    └──────┬──────┘
                                           │
                                    ┌──────▼──────┐
                                    │   Gateway   │
                                    │ (Port 3001) │
                                    └──────┬──────┘
                                           │
            ┌──────────────────────────────┼──────────────────────────────┐
            │                              │                              │
     ┌──────▼──────┐              ┌────────▼──────┐             ┌────────▼──────┐
     │    Auth     │              │Product Service│             │  User Service │
     │ (Port 3002) │              │  (Port 3003)  │             │  (Port 3006)  │
     └──────┬──────┘              └───────┬───────┘             └───────┬───────┘
            │                             │
     ┌──────▼──────┐              ┌───────▼───────┐
     │Order Service│              │    Orders     │
     │ (Port 3004) │              │  (Port 3005)  │
     └──────┬──────┘              └───────────────┘
            │
     ┌──────▼──────┐
     │  PostgreSQL │
     │ (Port 5432) │
     └─────────────┘

┌──────────────────────────────────────────────────┐
│                 Monitoring Stack                 │
│   Prometheus (9090) ◄──── Grafana (8080)         │
└──────────────────────────────────────────────────┘
```

| Service | Port | Role |
|---------|------|------|
| Frontend | 3000 | React UI |
| Gateway | 3001 | Routes all client requests to backend services |
| Auth | 3002 | Login and registration |
| Product Service | 3003 | Product catalog and inventory |
| Order Service | 3004 | Cart and checkout |
| Orders | 3005 | Order history and management |
| User Service | 3006 | User profiles and account management |
| PostgreSQL | 5432 | Stores auth_db, products_db, orders_db, users_db |
| Prometheus | 9090 | Metrics collection |
| Grafana | 8080 | Metrics dashboards |

---

## Local Development with Docker

Before deploying to the cloud, you can run the entire application locally using Docker Compose. This is the fastest way to test changes.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Node.js](https://nodejs.org/) 18+ (only needed if running without Docker)

### Start with Docker Compose

From the `projects/boutique-microservices/` directory:

```bash
cd projects/boutique-microservices
docker-compose -f docker-compose.yml up -d
```

This builds all service images and starts containers for every service plus PostgreSQL, Prometheus, and Grafana.

### Verify everything is running

```bash
docker ps
```

You should see containers for: `frontend`, `gateway`, `auth`, `product-service`, `order-service`, `orders`, `user-service`, `postgres`, `prometheus`, `grafana`.

### Access the application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Gateway metrics | http://localhost:3001/metrics |
| Grafana | http://localhost:3007 (admin / admin) |
| Prometheus | http://localhost:9090 |

### Run without Docker (Node.js)

```bash
cd projects/boutique-microservices
npm install
npm run dev          # starts all services concurrently
```

Or individually:

```bash
npm run dev:backend   # all backend services
npm run dev:frontend  # React frontend only
```

### Stop all services

```bash
docker-compose -f docker-compose.yml down
```

---

## Infrastructure Provisioning on AWS

The Terraform configuration in `projects/Infrastructure/` provisions everything needed to run the application on EKS.

### What Terraform creates

| Resource | Details |
|----------|---------|
| VPC | 3 public subnets across us-east-1a/b/c |
| EKS Cluster | `eks-cluster`, Kubernetes 1.34 |
| Node Group | `m7i-flex.large`, 1–2 nodes, on-demand |
| ECR Repositories | One per service (7 total) |
| ArgoCD | Installed via Helm into `argocd` namespace |
| Prometheus + Grafana | Installed via `kube-prometheus-stack` Helm chart into `monitoring` namespace |

### Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.5
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) configured

```bash
aws configure
# Enter: Access Key ID, Secret Access Key, region (us-east-1), output format (json)
```

Verify:
```bash
aws sts get-caller-identity
```

### Apply infrastructure

```bash
cd projects/Infrastructure
terraform init
terraform plan        # review what will be created
terraform apply --auto-approve
```

This takes ~15 minutes. Terraform outputs the cluster name and ECR URLs when done.

### Connect kubectl to the cluster

```bash
aws eks update-kubeconfig \
  --region us-east-1 \
  --name eks-cluster
```

Verify nodes are ready:

```bash
kubectl get nodes
```

---

## From Docker to Kubernetes

Each service has a `Dockerfile` in its directory under `projects/boutique-microservices/`. When deployed to Kubernetes, these become container images stored in ECR, referenced by the manifests in `gitops/k8s/`.

### How it maps

| Docker Compose concept | Kubernetes equivalent |
|------------------------|----------------------|
| `image:` in docker-compose.yml | ECR image URI in deployment manifest |
| `ports:` | `containerPort` + `Service` resource |
| `environment:` | `env:` or `secretKeyRef` in pod spec |
| `depends_on:` | Kubernetes starts all pods; services retry until DB is ready |
| `volumes:` (for postgres) | `PersistentVolumeClaim` via EBS CSI driver |

### Manifest structure

```
gitops/
├── argo-cd.yml              # ArgoCD Application — registers this repo for GitOps
├── kustomization.yml        # Kustomize entry point — lists all resources
├── namespace.yml            # Creates boutique namespace
├── secrets.yml              # DB connection strings as a Kubernetes Secret
└── k8s/
    ├── backend/             # One Deployment + Service per backend service
    ├── frontend/            # Frontend Deployment + Service
    ├── database/            # PostgreSQL StatefulSet, Service, restore Job
    └── grafana-dashboard.yml # Pre-loaded Grafana dashboard (ConfigMap)
```

### Apply all manifests

```bash
kubectl apply -k gitops/
```

Check pods are coming up:

```bash
kubectl get pods -n boutique
```

Wait until all show `Running`. The database pod may take 30–60 seconds longer than the others.

### Restore the database

The application needs seed data. A Kubernetes Job loads the SQL dump into PostgreSQL.

**Wait for the database to be ready first:**

```bash
kubectl get pods -n boutique -l app=boutique-postgres
# Wait until READY shows 1/1
```

**Apply the restore job:**

```bash
kubectl apply -f gitops/k8s/database/restore-job.yml
```

**Monitor it:**

```bash
kubectl get pods -n boutique -l job-name=boutique-db-restore
# It will go Running → Completed
```

**Check restore logs:**

```bash
kubectl logs -n boutique -l job-name=boutique-db-restore
```

You should see SQL being executed across all 4 databases. `Completed` status means it ran successfully — this is expected and normal.

---

## Setting Up the CI/CD Pipeline

The GitHub Actions pipeline (`.github/workflows/ci.yml`) automatically builds Docker images and pushes them to ECR on every push to `main`. It then updates the image tags in the k8s manifests so ArgoCD can sync the new version.

### Pipeline jobs

```
push to main
     │
     ▼
build-and-push (7 parallel jobs)
  └── For each service: docker build → docker push to ECR
     │
     ▼
update-manifests
  └── Updates image tags in gitops/k8s/
  └── Commits back to main
```

### Step 1: Create an IAM user for GitHub Actions

1. Go to **AWS Console → IAM → Users → Create user**
2. Name: `github-actions-ci`
3. Attach managed policies:
   - `AmazonEC2ContainerRegistryFullAccess`
4. Go to the user → **Security credentials → Create access key**
5. Select **Application running outside AWS**
6. Copy both the **Access Key ID** and **Secret Access Key** (only shown once)

### Step 2: Add secrets to GitHub

Go to your repository → **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value |
|-------------|-------|
| `AWS_ACCESS_KEY_ID` | Access key from Step 1 |
| `AWS_SECRET_ACCESS_KEY` | Secret key from Step 1 |
| `AWS_REGION` | `us-east-1` (or your region) |
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID |

To find your account ID:
```bash
aws sts get-caller-identity --query Account --output text
```

### Step 3: Trigger the pipeline

Push any change to `main`:

```bash
git add .
git commit -m "trigger CI"
git push origin main
```

### Step 4: Check pipeline status

1. Go to your repo → **Actions** tab
2. Click the latest **Boutique CI Pipeline** run
3. You'll see two jobs:
   - **build-and-push** — 7 parallel matrix jobs. Each builds and pushes one service image to ECR.
   - **update-manifests** — runs after all builds succeed. Replaces image tags in `gitops/k8s/` and commits back.
4. Click any job → expand any step to see full logs
5. Green checkmark = success. Red X = failed — click the step to see the error.

### Step 5: Verify images in ECR

```bash
aws ecr describe-images \
  --repository-name frontend \
  --region us-east-1 \
  --query 'imageDetails[*].imageTags' \
  --output table
```

The tag will be the commit SHA (e.g. `3e910aa...`).

---

## Setting Up ArgoCD (GitOps)

ArgoCD watches the `main` branch of this repo. Any change pushed to `gitops/` is automatically synced to the cluster — no manual `kubectl apply` needed after setup.

### What to know

- ArgoCD is already installed by Terraform into the `argocd` namespace
- The `gitops/argo-cd.yml` file defines the **Application** — it tells ArgoCD which repo, branch, and path to watch
- When the CI pipeline updates image tags and commits to `main`, ArgoCD detects the change and rolls out the new pods automatically

### Register the application

```bash
kubectl apply -f gitops/argo-cd.yml -n argocd
```

### Check sync status

```bash
kubectl get application -n argocd
```

You should see `STATUS: Synced` and `HEALTH: Healthy` once the initial sync completes.

### Access the ArgoCD UI

```bash
kubectl port-forward svc/argocd-server 8443:443 -n argocd &
```

Open https://localhost:8443

Get the admin password:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

- Username: `admin`

In the UI you can see each service's sync status, last deployed commit, pod health, and manually trigger a sync if needed.

### How automated sync works

The `syncPolicy` in `argo-cd.yml` can be set to automated:

```yaml
syncPolicy:
  automated:
    prune: true      # delete resources removed from git
    selfHeal: true   # re-sync if someone manually changes the cluster
```

Currently sync is manual (`syncPolicy: {}`). Enable automated sync when you're confident the pipeline is stable.

---

## Setting Up Observability

### Prometheus

Prometheus is installed by Terraform via `kube-prometheus-stack`. It scrapes metrics from the cluster and the boutique services.

#### How services expose metrics

Each backend service exposes a `/metrics` endpoint (Node.js `prom-client`). A `ServiceMonitor` resource tells Prometheus where to scrape:

```yaml
# gitops/k8s/backend/service-monitor.yml
spec:
  namespaceSelector:
    matchNames:
      - boutique
  selector:
    matchLabels:
      app: gateway
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
```

The `ServiceMonitor` has the label `release: kube-prometheus-stack` which is how the Prometheus Operator discovers it automatically.

#### Access Prometheus

```bash
kubectl port-forward svc/kube-prometheus-stack-prometheus 9090:9090 -n monitoring &
```

Open http://localhost:9090

#### Useful PromQL queries to try

```promql
# Request rate per service
sum by (job) (rate(http_requests_total[5m]))

# 95th percentile response time
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))

# 5xx error rate per service
sum by (job) (rate(http_requests_total{status_code=~"5.."}[5m]))

# Pod CPU usage
sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="boutique"}[5m]))

# Pod memory usage
sum by (pod) (container_memory_working_set_bytes{namespace="boutique"})

# Pod restart count
kube_pod_container_status_restarts_total{namespace="boutique"}

# Which services are up
up{job=~"gateway|auth|product-service|order-service|orders|user-service"}

# Node.js heap memory
nodejs_heap_size_used_bytes
```

Go to **Graph** tab to visualise any query over time.

---

### Grafana

Grafana is also installed by `kube-prometheus-stack`. It is pre-configured with Prometheus as a datasource and comes with a custom boutique dashboard automatically loaded.

#### How the dashboard is pre-loaded

The dashboard lives in `gitops/k8s/grafana-dashboard.yml` as a `ConfigMap`. It has the label:

```yaml
labels:
  grafana_dashboard: "1"
```

The `kube-prometheus-stack` Helm chart includes a **Grafana sidecar** that watches for ConfigMaps with this label across all namespaces. When it finds one, it automatically imports the JSON dashboard into Grafana — no manual import needed.

#### Access Grafana

```bash
kubectl port-forward svc/kube-prometheus-stack-grafana 8080:80 -n monitoring &
```

Open http://localhost:8080

Get the admin password:
```bash
kubectl get secret kube-prometheus-stack-grafana -n monitoring \
  -o jsonpath="{.data.admin-password}" | base64 --decode
```

- Username: `admin`

#### What's in the pre-loaded dashboard

The **Boutique Microservices** dashboard includes:

| Panel | What it shows |
|-------|--------------|
| Request Rate — $service | HTTP requests/sec broken down by status code |
| Response Time — $service | p95 and p99 latency |
| Active Requests | In-flight requests at any moment |
| Error Rate | 5xx rate as a percentage of total traffic |
| Request Rate by Service | All services on one graph |
| Node.js Heap Memory | Used vs total heap per service |
| Node.js Event Loop Lag | Latency in the JS event loop (indicator of CPU pressure) |
| Pod CPU Usage | CPU per pod in the boutique namespace |
| Pod Memory Usage | Memory per pod |
| Pod Restart Count | Surfaces crash-looping pods |
| Service Health | UP/DOWN status per service |
| HTTP Error Rate by Service | 4xx and 5xx breakdown per service |

The dashboard has a **Service** dropdown variable at the top — use it to filter all panels to a specific service.

---

### Log Forwarding to CloudWatch (Optional)

Install Fluent Bit to forward pod logs to CloudWatch:

```bash
helm repo add aws https://aws.github.io/eks-charts
helm repo update

helm upgrade --install aws-for-fluent-bit aws/aws-for-fluent-bit \
  --namespace amazon-cloudwatch \
  --create-namespace \
  --set cloudWatch.enabled=true \
  --set cloudWatch.region=us-east-1 \
  --set cloudWatch.logGroupName=/eks/boutique/pods \
  --set cloudWatch.logStreamPrefix=from-fluent-bit- \
  --set firehose.enabled=false \
  --set kinesis.enabled=false \
  --set elasticsearch.enabled=false
```

Verify:
```bash
kubectl get pods -n amazon-cloudwatch
```

Logs appear in **CloudWatch → Log groups → /eks/boutique/pods**.

---

## Port Forwarding Reference

Run all at once in the background:

```bash
kubectl port-forward svc/frontend 3000:3000 -n boutique &
kubectl port-forward svc/gateway 3001:3001 -n boutique &
kubectl port-forward svc/kube-prometheus-stack-prometheus 9090:9090 -n monitoring &
kubectl port-forward svc/kube-prometheus-stack-grafana 8080:80 -n monitoring &
kubectl port-forward svc/argocd-server 8443:443 -n argocd &
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Gateway / Metrics | http://localhost:3001/metrics |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:8080 |
| ArgoCD | https://localhost:8443 |

---

## Credentials

### Grafana
```bash
kubectl get secret kube-prometheus-stack-grafana -n monitoring \
  -o jsonpath="{.data.admin-password}" | base64 --decode
```
Username: `admin`

### ArgoCD
```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```
Username: `admin`

---

## Cleanup

```bash
cd projects/Infrastructure
terraform destroy --auto-approve
```
