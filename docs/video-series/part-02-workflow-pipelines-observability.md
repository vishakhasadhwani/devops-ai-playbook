# Video Series — Part 2: From Local to Cloud — Pipelines & Observability

**Goal:** Walk through the **end-to-end workflow**: develop and run locally, automate quality gates in CI/CD, deploy to cloud environments, and **observe** what happens in production.

---

## 1. The thread: local → pipeline → cloud

A practical mental model:

1. **Local:** Fast feedback while coding (unit tests, lint, run via Docker Compose or native runtimes).
2. **Source control:** Push triggers automation; human review via pull requests.
3. **CI pipeline:** Build, test, scan — produce a **trusted artifact** (often container images).
4. **Registry:** Store versioned images (or packages) for deployment.
5. **CD / GitOps:** Promote artifacts to **dev → staging → production** with policy and approvals.
6. **Cloud:** Managed Kubernetes, load balancers, databases, IAM — provisioned with **IaC** where possible.
7. **Observability:** Logs, metrics, traces — close the feedback loop for incidents and performance.

---

## 2. Local development (why it matters)

- **Parity:** Docker Compose (or similar) helps align dependencies and ports with what you will run in the cluster.
- **Speed:** Developers iterate without waiting for cloud for every change.
- **Contract:** API boundaries and health checks defined locally reduce surprises after deploy.

In this repo, see for example:

- `projects/boutique-microservices/docker-compose.yml` — runnable local stack for the boutique demo (see [projects/README.md](../../projects/README.md)).
- [projects/fullstack-cicd-pipeline/README.md](../../projects/fullstack-cicd-pipeline/README.md) — target architecture and learning layout for a full-stack CI/CD story (implementation may grow over time).

---

## 3. CI/CD pipeline — typical stages

A common GitHub Actions–style flow (names vary by team):

| Stage        | Purpose |
|--------------|---------|
| **Trigger**  | Push, PR, tag, or schedule |
| **Build**    | Compile / bundle; create artifacts |
| **Test**     | Unit, integration; fail fast |
| **Security** | SAST, dependency scan, container scan |
| **Publish**  | Push images to a registry with immutable tags |
| **Deploy**   | Update Kubernetes manifests, Helm, or GitOps repo |

**Principles:**

- **Fail fast** in CI — cheap to fix before merge.
- **Immutable artifacts** — deploy the same bits that passed tests.
- **Environment promotion** — same artifact, different config/secrets per env.

---

## 4. Cloud deployment patterns (high level)

- **Kubernetes:** Industry-standard for packaging and scaling container workloads; cloud vendors offer managed control planes (EKS, GKE, AKS).
- **IaC:** Terraform (or similar) creates VPCs, clusters, IAM — reviewed like app code.
- **GitOps (optional but common):** Cluster state desired in Git; controllers reconcile (e.g. Argo CD). The boutique EKS material in this repo references GitOps-style workflows.

---

## 5. Observability — operational clarity

### 5.1 Logs

- **Use structured logs** (JSON or key=value) where possible for search and correlation.
- Aggregate logs (e.g. to a central store) for **forensics** and **audit**.

### 5.2 Metrics

- **RED** (Rate, Errors, Duration) for services — good starting lens.
- **USE** (Utilization, Saturation, Errors) for resources.
- Prometheus-style scraping and Grafana dashboards appear in multiple projects in this repository.

### 5.3 Traces

- Follow a request across services — essential for **microservices** debugging.
- OpenTelemetry is the common open stack for instrumentation.

### 5.4 Alerting

- Alert on **symptoms** (SLO burn, error spikes) not only on raw CPU unless that is proven to correlate with user pain.

---

## 6. How observability ties back to DevOps

- **Developers** need fast feedback from **staging** and **production** behavior.
- **Operators** need signals that tie to **releases** (deploy markers) and **rollbacks**.
- **Blameless postmortems** use logs/metrics/traces to improve the next iteration.

---

## 7. Map to this repository

| Topic | Where to look |
|-------|----------------|
| Pipeline + architecture (teaching) | [projects/fullstack-cicd-pipeline/README.md](../../projects/fullstack-cicd-pipeline/README.md) |
| GitHub Actions / CI (boutique EKS flow) | `projects/boutique-microservices/` (workflows and branch notes in [projects/README.md](../../projects/README.md)) |
| Local Docker Compose | `projects/boutique-microservices/docker-compose.yml` |
| EKS deploy, GitOps, Grafana, Prometheus | [projects/README.md](../../projects/README.md) |
| Learning order (foundations) | [projects/fullstack-cicd-pipeline/Foundations/README.md](../../projects/fullstack-cicd-pipeline/Foundations/README.md) |

---

## Series navigation

- **Part 1:** [Beginner concepts](part-01-beginner-concepts.md)
- **Part 3:** [Deployment demo of this repo](part-03-deployment-demo.md)
- **Part 4:** [AIOps implementation](part-04-aiops.md)

---

*Previous: [Part 1](part-01-beginner-concepts.md) | Next: [Part 3](part-03-deployment-demo.md)*
