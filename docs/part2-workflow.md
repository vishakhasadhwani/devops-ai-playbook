# Part 2 — Understanding the Workflow

> Companion doc for the YouTube series: **DevOps + AIOps Series** — Part 2

---

## Overview

Before writing any code or deployment configs, you need to understand how the entire system flows. This part traces the complete journey — from a developer writing code locally, all the way to an AI assistant diagnosing incidents in production.

```mermaid
flowchart LR
    A[👩‍💻 Developer] --> B[Local Docker]
    B --> C[Git Push]
    C --> D[GitHub Actions CI]
    D --> E[ECR Images]
    E --> F[ArgoCD GitOps]
    F --> G[EKS Cluster]
    G --> H[Prometheus + Grafana]
    H --> I[CloudWatch Logs]
    I --> J[Kira — AIOps Agent]
```

---

## Stage 1: Local Development

Every change starts on a developer's machine. The full application stack runs locally using Docker Compose — no cloud account required.

```mermaid
flowchart TD
    Dev[Developer writes code] --> DC[docker-compose up]
    DC --> F[Frontend :3000]
    DC --> G[Gateway :3001]
    DC --> A[Auth :3002]
    DC --> P[Product Service :3003]
    DC --> OS[Order Service :3004]
    DC --> O[Orders :3005]
    DC --> U[User Service :3006]
    DC --> DB[(PostgreSQL :5432)]
    DC --> PR[Prometheus :9090]
    DC --> GR[Grafana :3007]

    G --> A
    G --> P
    G --> OS
    G --> O
    G --> U
    A --> DB
    P --> DB
    O --> DB
    U --> DB
```

Each service has its own `Dockerfile`. Docker Compose wires them together with a shared network, letting you test the full system locally before touching any cloud infrastructure.

**What to verify locally:**
- All containers show `Up` in `docker ps`
- Frontend loads at http://localhost:3000
- `/api/products` returns data via the gateway
- Prometheus scrapes metrics from `/metrics` endpoints
- Grafana dashboards show live data

---

## Stage 2: Source Control

Once a change is tested locally, it goes into Git.

```mermaid
gitGraph
   commit id: "initial"
   branch feature/new-endpoint
   commit id: "add endpoint"
   commit id: "add tests"
   checkout main
   merge feature/new-endpoint id: "PR merged"
   commit id: "ci: update image tags"
```

**The flow:**
1. Developer creates a feature branch
2. Makes changes, commits with clear messages
3. Opens a Pull Request on GitHub
4. PR is reviewed and merged into `main`
5. Merge to `main` triggers the CI pipeline automatically

Everything is tracked — who changed what, when, and why. This is the foundation of GitOps.

---

## Stage 3: CI Pipeline — GitHub Actions

On every push to `main`, GitHub Actions builds Docker images for all 7 services in parallel and pushes them to Amazon ECR.

```mermaid
flowchart TD
    Push[Push to main] --> Trigger[GitHub Actions triggered]

    Trigger --> B1[Build auth]
    Trigger --> B2[Build gateway]
    Trigger --> B3[Build product-service]
    Trigger --> B4[Build order-service]
    Trigger --> B5[Build orders]
    Trigger --> B6[Build user-service]
    Trigger --> B7[Build frontend]

    B1 & B2 & B3 & B4 & B5 & B6 & B7 --> Push2[Push all images to ECR]
    Push2 --> UM[update-manifests job]
    UM --> |Updates image tags in gitops/k8s/| Commit[Commits back to main]
```

**Key concepts:**
- Each service is a separate matrix job — they all build in parallel
- Images are tagged with the commit SHA for full traceability
- The `update-manifests` job patches the image tag in every Kubernetes manifest and commits the change back
- This commit is what ArgoCD detects to trigger a rollout

**Where to check:** GitHub repo → **Actions** tab → **Boutique CI Pipeline**

---

## Stage 4: Infrastructure — Terraform on AWS

Before the cluster can run anything, the infrastructure must exist. Terraform provisions everything from scratch.

```mermaid
flowchart TD
    TF[terraform apply] --> VPC[VPC — 3 AZs]
    VPC --> Sub1[Subnet us-east-1a]
    VPC --> Sub2[Subnet us-east-1b]
    VPC --> Sub3[Subnet us-east-1c]

    TF --> EKS[EKS Cluster]
    EKS --> NG[Node Group\nm7i-flex.large]
    Sub1 & Sub2 & Sub3 --> NG

    TF --> ECR1[ECR: frontend]
    TF --> ECR2[ECR: gateway]
    TF --> ECR3[ECR: auth]
    TF --> ECR4[ECR: ...]

    TF --> Helm1[Helm: ArgoCD\nnamespace: argocd]
    TF --> Helm2[Helm: kube-prometheus-stack\nnamespace: monitoring]
```

Terraform also installs ArgoCD and the Prometheus/Grafana stack into the cluster via Helm — so the entire platform is ready to receive workloads the moment `terraform apply` finishes.

---

## Stage 5: GitOps Deployment — ArgoCD

ArgoCD runs inside the cluster and watches the `main` branch. The moment the CI pipeline commits updated image tags back to Git, ArgoCD detects the change and rolls out the new version.

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant GH as GitHub (main)
    participant CI as GitHub Actions
    participant ECR as Amazon ECR
    participant Argo as ArgoCD
    participant EKS as EKS Cluster

    Dev->>GH: git push
    GH->>CI: trigger pipeline
    CI->>ECR: docker push (new image)
    CI->>GH: commit updated image tag
    Argo->>GH: polls every 3 mins / webhook
    GH-->>Argo: detects new commit
    Argo->>EKS: kubectl apply (rolling update)
    EKS-->>Argo: sync complete
```

**What ArgoCD does:**
- Continuously compares the desired state in Git against the live state in the cluster
- If they differ, it syncs — applying only what changed
- If someone manually changes something in the cluster, ArgoCD reverts it to match Git
- Every deployment is auditable — it's just a Git commit

**Key files:**
- `gitops/argo-cd.yml` — registers the repo and branch with ArgoCD
- `gitops/kustomization.yml` — lists all Kubernetes resources to apply
- `gitops/k8s/` — all service deployments, services, database, secrets

---

## Stage 6: Observability

Once the application is running in EKS, three layers of observability keep watch.

```mermaid
flowchart LR
    subgraph Services [boutique namespace]
        GW[gateway /metrics]
        AU[auth /metrics]
        PS[product-service /metrics]
        OS[order-service /metrics]
        OR[orders /metrics]
        US[user-service /metrics]
    end

    subgraph Monitoring [monitoring namespace]
        SM[ServiceMonitor] -->|scrape every 15s| PR[Prometheus]
        PR --> GR[Grafana\nDashboard]
    end

    subgraph Logging [amazon-cloudwatch namespace]
        FB[Fluent Bit] -->|pod logs| CW[CloudWatch\n/eks/boutique/pods]
    end

    GW & AU & PS & OS & OR & US --> SM
    GW & AU & PS & OS & OR & US --> FB
```

**Metrics — Prometheus + Grafana**
- Every service exposes a `/metrics` endpoint using `prom-client`
- A `ServiceMonitor` resource tells the Prometheus Operator which pods to scrape
- Grafana is pre-loaded with a boutique dashboard via a ConfigMap labelled `grafana_dashboard: "1"` — the Grafana sidecar auto-imports it

**Logs — Fluent Bit + CloudWatch**
- Fluent Bit runs as a DaemonSet in `amazon-cloudwatch`
- Captures stdout from every pod and ships logs to CloudWatch
- Log group: `/eks/boutique/pods`

**What to check in Grafana:**
- Request rate by service
- p95 / p99 response times
- 4xx and 5xx error rates
- Pod CPU and memory usage
- Pod restart count — surfaces crash loops early

---

## Stage 7: AIOps — Kira (Bedrock Agent)

This is where the workflow goes beyond traditional DevOps. When something goes wrong in production, instead of manually digging through logs and metrics, you ask Kira.

```mermaid
flowchart TD
    Incident[Incident detected\nor engineer asks a question] --> UI[Streamlit UI\napp.py]
    UI --> Agent[Bedrock Agent\nKira]

    Agent --> |Hypothesis: check logs| FL[Lambda: fetch_logs\nCloudWatch Logs]
    Agent --> |Hypothesis: check metrics| FM[Lambda: fetch_metrics\nPrometheus API]
    Agent --> |Hypothesis: check health| FH[Lambda: fetch_health\nEKS + Node Groups]

    FL --> |Log entries + timestamps| Agent
    FM --> |CPU, memory, latency, errors| Agent
    FH --> |Pod health, restarts, replicas| Agent

    Agent --> |Root cause + evidence + fix| UI
    UI --> Engineer[Engineer sees:\n- Root cause\n- Evidence from logs/metrics\n- Immediate fix\n- Prevention steps]
```

**How Kira investigates:**

```mermaid
sequenceDiagram
    participant Eng as Engineer
    participant Kira as Kira (Bedrock Agent)
    participant Logs as fetch_logs (Lambda)
    participant Metrics as fetch_metrics (Lambda)
    participant Health as fetch_health (Lambda)

    Eng->>Kira: "Why are we seeing 503 errors?"
    Note over Kira: Step 1: Understand the symptom
    Note over Kira: Step 2: Form a hypothesis
    Kira->>Logs: Search for 503 errors in last hour
    Logs-->>Kira: 47 entries — all from order-service
    Kira->>Health: Check order-service pod health
    Health-->>Kira: 0/1 replicas available — pod crash-looping
    Kira->>Metrics: Check order-service memory last 30m
    Metrics-->>Kira: Memory spiked to 512MB, OOM kill at 22:14
    Note over Kira: Step 4: Correlate evidence
    Kira->>Eng: Root cause: OOM kill at 22:14 due to memory spike.\nEvidence: logs show 503s starting at 22:14, pod restarting,\nmetrics confirm memory exceeded limit.\nFix: Increase memory limit in orders.yml to 768Mi.\nPrevention: Add VPA + memory alerting rule.
```

**The Kira workflow:**
1. Engineer describes a symptom
2. Kira forms a hypothesis
3. Gathers evidence using the 3 Lambda tools (logs, metrics, health)
4. Correlates data across all three sources
5. Returns root cause, supporting evidence, immediate fix, and prevention steps

**Kira never guesses.** Every conclusion is backed by specific log entries or metric values.

---

## The Complete Picture

```mermaid
flowchart TD
    Dev[👩‍💻 Developer] -->|writes code| Local[Docker Compose\nLocal Testing]
    Local -->|git push| GH[GitHub main branch]
    GH -->|triggers| CI[GitHub Actions\nBuild + Push to ECR]
    CI -->|commits image tags| GH
    GH -->|ArgoCD detects change| Argo[ArgoCD\nRolling Deploy to EKS]
    Argo --> EKS[EKS Cluster\n7 microservices]
    EKS -->|metrics /metrics| Prom[Prometheus]
    EKS -->|pod logs| FB[Fluent Bit]
    Prom --> Grafana[Grafana\nDashboards]
    FB --> CW[CloudWatch\nLog Groups]
    Grafana -->|anomaly detected| Kira[Kira — AIOps Agent\nBedrock + Lambda]
    CW --> Kira
    Kira -->|root cause + fix| Eng[👩‍💻 Engineer]

    subgraph IaC [Infrastructure as Code]
        TF[Terraform\nVPC + EKS + ECR + Helm]
    end
    TF --> EKS
```

---

## Key Files Reference

| File | Stage | Purpose |
|------|-------|---------|
| `projects/boutique-microservices/docker-compose.yml` | Stage 1 | Local stack |
| `.github/workflows/ci.yml` | Stage 3 | Build and push images |
| `projects/Infrastructure/` | Stage 4 | Terraform for AWS |
| `gitops/argo-cd.yml` | Stage 5 | ArgoCD application definition |
| `gitops/k8s/` | Stage 5 | All Kubernetes manifests |
| `gitops/k8s/backend/service-monitor.yml` | Stage 6 | Prometheus scrape config |
| `gitops/k8s/grafana-dashboard.yml` | Stage 6 | Pre-loaded Grafana dashboard |
| `projects/aiops-assistant/` | Stage 7 | Kira — AIOps Bedrock Agent |
