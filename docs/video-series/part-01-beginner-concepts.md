# Video Series — Part 1: Core Concepts for Beginners

**Format:** ~8 minutes  
**Goal:** Give new learners a mental map of what “DevOps” expects you to know before you touch pipelines or the cloud.

---

## What this part covers

You do not need to master every tool on day one. You need a clear picture of **how code becomes running software** and **how teams keep it reliable**.

### 1. DevOps in one sentence

DevOps is **culture plus practice**: developers and operators share ownership of delivery and reliability, supported by **automation**, **feedback**, and **repeatable processes**.

### 2. Version control (Git)

- **Why:** Every change is tracked; you can review, roll back, and collaborate safely.
- **Minimum to recognize:** commits, branches, pull/merge requests, remotes (e.g. GitHub).
- **Link to practice:** All infrastructure and application code in this repo should live in Git so pipelines and reviews apply consistently.

### 3. Continuous Integration (CI)

- **Idea:** Frequently merge small changes; each merge triggers **build** and **automated tests** so breaks are caught early.
- **Typical steps:** checkout → install dependencies → build → test → (optional) security scans.

### 4. Continuous Delivery / Deployment (CD)

- **Delivery:** Software is **always releasable** (artifact built, tested, ready).
- **Deployment:** Approved changes **go to an environment** (staging, production) via automation.
- **Distinction:** CD is about **safe, repeatable promotion** of what CI already validated.

### 5. Containers (e.g. Docker)

- **Why:** Package app + dependencies so “runs on my machine” matches **prod-like** environments.
- **Vocabulary:** image, container, Dockerfile, registry (where images are stored).

### 6. Orchestration (e.g. Kubernetes)

- **Why:** Run many containers at scale: scheduling, health checks, scaling, networking, secrets.
- **Beginner takeaway:** Kubernetes is **not** required to *learn* DevOps, but it is central to **many** cloud-native deployments.

### 7. Infrastructure as Code (IaC)

- **Idea:** Servers, networks, and clusters are described in **files** (Terraform, CloudFormation, etc.), versioned like application code.
- **Benefit:** Repeatable environments, reviewable changes, less manual drift.

### 8. Configuration vs. infrastructure

- **Infrastructure:** VPCs, clusters, load balancers (often IaC).
- **Configuration:** App settings, feature flags, secrets (often separate, with secret stores).

### 9. Observability (preview for Part 2)

Three pillars you will hear constantly:

| Pillar    | Question it answers        | Examples              |
|-----------|----------------------------|-------------------------|
| **Logs**  | What happened? (events)    | structured app logs     |
| **Metrics** | How much / how fast?     | CPU, latency, error rate  |
| **Traces** | Which path did a request take? | distributed tracing |

You will connect this to **pipelines** and **production** in Part 2.

### 10. Security basics (enough to care)

- **Secrets** do not belong in Git in plain text; use CI secrets and cloud secret managers.
- **Scanning:** dependency and container image scans are common CI steps (see projects in this repo).

---

## Suggested “minimum viable” beginner checklist

1. Comfortable with **Git** basics (branch, PR, merge).
2. Can run an app **locally** (README steps).
3. Understand **CI vs CD** in plain language.
4. Know what a **Docker image** is and why registries exist.
5. Know that **IaC** and **observability** are standard in serious setups.

---

## How this repo continues the story

- **Part 2:** End-to-end workflow — local → pipeline → cloud, plus observability.
- **Part 3:** Hands-on deployment using projects under `projects/` in this repository.
- **Part 4:** AIOps — applying AI-assisted patterns to operations data and workflows.

---

## Related reading in this repository

- Root [README.md](../../README.md) — overview, principles, learning path.
- [projects/fullstack-cicd-pipeline/README.md](../../projects/fullstack-cicd-pipeline/README.md) — architecture you will see again in later parts.

---

*Previous: — | Next: [Part 2 — Workflow, pipelines, observability](part-02-workflow-pipelines-observability.md)*
