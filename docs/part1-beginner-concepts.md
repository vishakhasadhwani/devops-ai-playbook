# Part 1 — Beginner Concepts You Need to Know

> Companion doc for the YouTube series: **DevOps Practice Guide** — Episode 1 (8 min)

---

## What is DevOps?

DevOps is a culture and set of practices that unifies software **Dev**elopment and IT **Op**eration**s**. The goal is to shorten the feedback loop between writing code and running it in production, while maintaining quality and reliability.

---

## Core Concepts to Understand First

### 1. Version Control (Git)
Every DevOps workflow starts here. Git lets teams track changes, collaborate, and roll back safely.
- `git init`, `git clone`, `git pull`, `git push`
- Branching strategies: `main`, feature branches, pull requests
- Commit hygiene: small, descriptive commits

### 2. Linux & Shell Basics
Most servers run Linux. You need to be comfortable with:
- File system navigation (`ls`, `cd`, `cat`, `grep`)
- Permissions (`chmod`, `chown`)
- Process management (`ps`, `kill`, `systemctl`)
- Shell scripting for automation

### 3. Containers (Docker)
Containers package your app and all its dependencies into a portable unit.
- **Dockerfile** — defines how to build the image
- **Image** — the blueprint
- **Container** — a running instance of an image
- Key commands: `docker build`, `docker run`, `docker ps`, `docker logs`

### 4. CI/CD — What It Means
| Term | What It Does |
|------|-------------|
| **CI** (Continuous Integration) | Automatically build and test every code push |
| **CD** (Continuous Delivery) | Automatically deploy tested code to an environment |
| **Pipeline** | The sequence of steps that takes code from commit to production |

### 5. Infrastructure as Code (IaC)
Instead of clicking through a cloud console, you define infrastructure in files (Terraform, Ansible) and version-control them just like application code.

### 6. Observability — The Three Pillars
| Pillar | Tool Examples | Purpose |
|--------|--------------|---------|
| **Metrics** | Prometheus, Grafana | Measure system health over time |
| **Logs** | ELK Stack | Record what happened and when |
| **Traces** | Jaeger, OpenTelemetry | Follow a request across services |

---

## Beginner Learning Path

1. Git fundamentals
2. Linux basics & shell scripting
3. Docker — build, run, and compose containers
4. Understand YAML (used everywhere: k8s, CI pipelines, configs)
5. Read a CI/CD pipeline file (see `.github/workflows/` in this repo)

---

## Key Terms Glossary

| Term | Definition |
|------|-----------|
| Artifact | A build output (JAR, Docker image, binary) |
| Environment | A runtime target: `dev`, `staging`, `production` |
| Pipeline | Automated sequence: build → test → deploy |
| Orchestration | Managing many containers (Kubernetes) |
| IaC | Infrastructure defined and managed as code |
| Observability | Ability to understand a system's internal state from its outputs |

---

## Where to Go Next
- [Part 2 — The DevOps Workflow](./part2-workflow.md): local → cloud deployment walkthrough
- Explore the pipeline config: `.github/workflows/`
- Run the app locally: `projects/fullstack-cicd-pipeline/`
