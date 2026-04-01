# Video Series — Part 3: Deployment Demo — This Repository

**Goal:** Align the video walkthrough with **real paths and projects** in the DevOps Practice Guide repo so viewers can reproduce the demo.

---

## What to demo (choose your depth)

This repository contains two complementary tracks:

1. **Full-stack CI/CD pipeline** (`projects/fullstack-cicd-pipeline/`) — **architecture and learning narrative** (diagrams, foundations README, intended layout for Docker/K8s/IaC/monitoring). Use this to explain concepts and the “happy path” on a whiteboard or in slides.
2. **Boutique microservices** (`projects/boutique-microservices/` + [projects/README.md](../../projects/README.md)) — **hands-on** local Docker Compose and **Amazon EKS** deployment with monitoring and GitOps-style steps.

Part 3 works well as: **concepts from (1)** → **live commands on (2)** so viewers see both the map and the terrain.

---

## Demo script (single narrative)

### 1. Teaching frame — full-stack CI/CD story

**Root:** `projects/fullstack-cicd-pipeline/`

1. **Architecture diagram** — GitHub → Actions → registry → Kubernetes → monitoring ([README.md](../../projects/fullstack-cicd-pipeline/README.md)).
2. **Learning order** — [Foundations/README.md](../../projects/fullstack-cicd-pipeline/Foundations/README.md) (networking → Linux → cloud → Docker → K8s → CI/CD → Terraform).

### 2. Runnable app — local Docker Compose

**Root:** `projects/boutique-microservices/` — full procedure and URLs in [projects/README.md](../../projects/README.md).

```bash
cd projects/boutique-microservices
docker-compose -f docker-compose.yml up -d
```

Confirm ports, Grafana credentials, and health URLs in that README before recording.

### 3. Cloud path — Amazon EKS (boutique)

Follow [projects/README.md](../../projects/README.md) (EKS deployment guide):

| Step | What to show |
|------|----------------|
| Architecture | Diagram: frontend, gateway, services, PostgreSQL, Prometheus, Grafana |
| AWS + Terraform | `Infrastructure/` — init / plan / apply with **your** credentials |
| kubectl | `aws eks update-kubeconfig`; namespaces `boutique`, `argocd`, `monitoring` |
| CI | Branch/pipeline notes (`project-demo`, `ci.yml`) |
| GitOps | `gitops/k8s`, ECR image tags after pipeline success |
| Verify | Port-forwards for UI, Grafana, Argo CD; optional DB restore job |

**Safety:** The guide warns that **example AWS credentials and account-specific values** may appear in docs or manifests. Tell viewers to **replace** account IDs, regions, and secrets with their own.

### What to emphasize on camera

- **Same thread as Part 2:** local parity → CI artifact → cluster → observability.
- **Secrets:** pipeline variables and cluster secrets — not plain text in Git.

---

## Suggested talking points (cross-part recap)

| Topic | Call back to |
|--------|----------------|
| Why CI runs before deploy | Part 2 — pipeline stages |
| Why Grafana/Prometheus appear again | Part 2 — observability pillars |
| What “production-like” means | Part 1 — containers + orchestration |

---

## Checklist before recording

- [ ] README commands run on a clean machine (or note prerequisites explicitly).
- [ ] Redact or replace secrets; use placeholder narration where needed.
- [ ] Show **one** successful path end-to-end rather than every optional branch.
- [ ] Link viewers to this file and the project READMEs in the video description.

---

## Series navigation

- **Part 1:** [Beginner concepts](part-01-beginner-concepts.md)
- **Part 2:** [Workflow, pipelines, observability](part-02-workflow-pipelines-observability.md)
- **Part 4:** [AIOps implementation](part-04-aiops.md)

---

*Previous: [Part 2](part-02-workflow-pipelines-observability.md) | Next: [Part 4](part-04-aiops.md)*
