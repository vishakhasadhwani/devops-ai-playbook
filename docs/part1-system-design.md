# Part 1 — System Design Foundations

> Companion doc for the YouTube series: **DevOps + AIOps Series** — Part 1

---

## Overview

This crash course breaks down the 12 core system design pillars behind modern DevOps and cloud architectures:

1. Distributed Systems
2. Monolith vs Microservices
3. API Communication
4. Service Discovery
5. Load Balancing
6. High Availability
7. Autoscaling
8. Reliability with Kubernetes
9. Security
10. Observability
11. Deployment Strategies
12. GitOps

Every concept connects directly to something running in this project. This is not just theory.

In the real world, nobody cares if you can define Kubernetes or list AWS services. What actually matters is whether you can design systems that scale, stay reliable under failure, and are operable in production. Every architectural decision is a trade-off — and if you don't understand those trade-offs, your system will break in ways you didn't anticipate.

---

## 1. Distributed Systems

**Pillar: Scalability + Fault Tolerance**

Small applications run like this: `Users → Nginx → Application → Database` — everything on one machine. Simple, fast to build, easy to reason about.

But as traffic grows, one machine hits its limits. CPU maxes out. Memory fills up. A single hardware failure takes everything down.

So the system gets split across multiple machines that communicate over the network. That is a distributed system.

**The benefit:** You can scale horizontally by adding more machines instead of endlessly upgrading one. You get fault tolerance because no single machine is a point of failure.

**The tradeoff:** Now you have network latency, partial failures, and consistency challenges. A request might reach machine A but the response never comes back. Did it succeed? Did it fail? This is the core challenge of distributed systems — designing for failure as a default, not an exception.

**In this project:** The entire platform is a distributed system. The frontend, 6 backend services, database, Prometheus, Grafana — all running as separate containers across multiple nodes in an EKS cluster. Each service is independently deployed and communicates over the network.

---

## 2. Monolith vs Microservices

**Pillar: Scalability + Modularity + Independent Deployability**

Imagine building your first application. You have one codebase, one deployment, one database. Login, products, orders, users — all inside the same application. This is a monolith. It works perfectly when you're starting.

But here's what breaks as you grow:

- The notification service starts consuming too much memory — and takes down the entire application with it
- The product service needs to handle 10x more traffic during a sale — but you can't scale just that service, you must scale the whole application
- A bug in the payments module requires redeploying everything including the login page

So companies decompose the monolith into **microservices** — where each business capability runs as an independent service with its own codebase, its own deployment, and its own database.

Now you can scale only the services that need it. A bug in one service doesn't cascade into others. Teams can deploy independently without coordinating with every other team.

**The tradeoff:** Now you have network calls between services instead of in-memory function calls. You have distributed data, more moving parts, and operational complexity.

**In this project:** We have 7 services — gateway, auth, product-service, order-service, orders, user-service, and frontend. Each has its own Dockerfile, its own Kubernetes deployment, and its own PostgreSQL database. They communicate through the gateway.

---

## 3. API Communication

**Pillar: Loose Coupling + Interface Design**

Once you split into microservices, services need to talk to each other. That communication happens through APIs — a contract between services.

### Synchronous — REST or gRPC

One service calls another and waits for a response. Simple, predictable. Used when you need an immediate answer. REST uses HTTP and JSON. gRPC uses binary encoding over HTTP/2 — faster and more efficient, common in internal service-to-service communication at scale.

### Asynchronous — Message Queues

One service sends a message and doesn't wait. The other service processes it when it's ready. Used for tasks that don't need an immediate response — sending emails, processing payments, generating reports. Kafka and RabbitMQ are common implementations. This decouples services completely — if the consumer is down, messages queue up and get processed when it recovers.

### Idempotency

A network failure happens. The client sends a request to create an order, times out, and retries. If the API isn't designed carefully — two orders get created. Idempotency means sending the same request multiple times produces the same result. Critical for payment APIs, order creation, any write operation.

### API Versioning

Your API evolves. You change a response format. Old clients break. API versioning solves this — `/api/v1/orders` stays the same while `/api/v2/orders` introduces the new format.

**In this project:** All services communicate synchronously through REST APIs. The gateway routes `/api/auth` to the auth service, `/api/products` to the product service, and so on. The frontend never talks directly to individual services — everything goes through the gateway.

---

## 4. Service Discovery

**Pillar: Loose Coupling + Dynamic Routing**

You have 20 microservices running in Kubernetes. Pods start and stop constantly. IP addresses change every time a pod restarts. Services scale up and down. How does one service find another if nothing stays at the same address?

**Client-side discovery:** The calling service queries a service registry (Consul, Eureka), gets a list of healthy instances, and picks one. The client is responsible for load balancing.

**Server-side discovery:** The calling service sends the request to a fixed endpoint. A load balancer or proxy resolves it to a healthy instance. The client doesn't need to know anything about the underlying topology.

Kubernetes uses server-side discovery. Every service gets a stable DNS name. The platform automatically routes traffic to the correct pod — so instead of `http://10.0.1.45:3002`, services call `http://auth:3002`. Kubernetes DNS resolves the name, even if the pod behind it has restarted ten times today.

**In this project:** The gateway calls `http://auth:3002`, `http://product-service:3003`, `http://orders:3005` — all stable DNS names defined by Kubernetes Services. No hardcoded IPs anywhere.

---

## 5. Load Balancing

**Pillar: Scalability + High Availability + Performance**

Traffic is growing. You've scaled to 5 instances of your product service. How does traffic get distributed across them?

### Layer 4 vs Layer 7

**L4 (Transport Layer):** Operates on TCP/UDP. Fast, low overhead. Routes based on IP and port. Doesn't understand HTTP. AWS Network Load Balancer (NLB) operates at L4.

**L7 (Application Layer):** Understands HTTP, headers, URLs, cookies. Can route based on request path, content type, or host header. AWS Application Load Balancer (ALB) and Nginx operate at L7.

### Algorithms

| Algorithm | How it works | When to use |
|-----------|-------------|-------------|
| Round Robin | Requests go to each server in turn | Servers have similar capacity, requests take similar time |
| Least Connections | Next request goes to the server with fewest active connections | Variable request processing time |
| IP Hash | Client IP determines the server | Session stickiness required |
| Weighted Round Robin | Some servers get more traffic based on capacity | Servers aren't identical |

### In Kubernetes

- **ClusterIP** — Internal only. Distributes traffic across pods using round robin via kube-proxy.
- **NodePort** — Exposes the service on a port on every node. Used for development.
- **LoadBalancer** — Provisions a cloud load balancer (ALB/NLB on AWS) for external access.
- **Ingress** — Manages external HTTP/HTTPS routing with rules.

**In this project:** Inside the cluster, Kubernetes ClusterIP services load balance traffic between pods. The gateway service is the single external entry point. In production you'd put an ALB in front of it.

---

## 6. High Availability

**Pillar: Fault Tolerance + Redundancy**

If you have one instance of your service, the application goes down when it crashes. That's a single point of failure.

High availability means designing the system so that no single failure causes downtime.

- **Redundancy:** Run multiple instances of every service. If one crashes, others keep serving traffic.
- **Multi-AZ deployment:** Spread instances across multiple availability zones. If one AZ has a power outage, the others keep running.
- **Health checks:** Load balancers continuously check if instances are healthy. Unhealthy instances get removed from rotation automatically.
- **Stateless services:** If your service doesn't hold state, any instance can handle any request. This is why we use JWTs — the token carries the session state, not the server.

### RTO and RPO

**RTO (Recovery Time Objective):** How long can the system be down before it causes unacceptable business impact?

**RPO (Recovery Point Objective):** How much data loss is acceptable? If your database is backed up every hour, your RPO is one hour.

**In this project:** We provision subnets across three availability zones — `us-east-1a`, `us-east-1b`, `us-east-1c`. The EKS node group spans all three. If one zone goes down, pods get rescheduled onto nodes in the remaining zones.

---

## 7. Autoscaling

**Pillar: Scalability + Cost Efficiency + Elasticity**

Traffic spikes. You need 20 pods at 6pm and 3 pods at 3am. Paying for 20 pods all day is wasteful. Manually scaling is slow and error-prone. Autoscaling solves this.

### HPA — Horizontal Pod Autoscaler

Watches CPU and memory usage across pods. When average CPU exceeds a threshold, it adds more pods. When traffic drops, it scales down. Most commonly used autoscaler.

### VPA — Vertical Pod Autoscaler

Instead of adding pods, it adjusts the CPU and memory requests of existing pods. Useful when you can't scale horizontally. Tradeoff: requires a pod restart to apply new resource limits.

### Cluster Autoscaler

When HPA wants to add a pod but there's no node with enough capacity, the pod stays in `Pending` state. Cluster Autoscaler detects this and provisions a new node. When nodes are underutilized, it drains and removes them to save cost.

### KEDA — Kubernetes Event Driven Autoscaler

HPA scales based on CPU and memory. KEDA scales based on external events and metrics — the length of a Kafka queue, the number of HTTP requests queued, a schedule, a Prometheus metric.

Example: Your order processing service consumes from a Kafka topic. At peak hours 10,000 messages queue up. KEDA sees the queue depth and scales the consumer pods from 2 to 20 — purely based on queue length, not CPU. When the queue drains, it scales back down.

**In this project:** Current setup uses fixed replica counts. KEDA would be the natural next step — scale the order-service based on incoming order volume, scale the product-service based on request rate measured in Prometheus.

---

## 8. Reliability with Kubernetes

**Pillar: Resilience + Self-Healing**

In traditional infrastructure, if a process crashes someone gets paged. They SSH in, restart the service, go back to sleep. Kubernetes introduces self-healing infrastructure — the platform handles this automatically.

**Liveness Probe:** Kubernetes asks the container: "are you still alive?" If the container stops responding, Kubernetes kills it and starts a new one. Used to detect deadlocks and unrecoverable states.

**Readiness Probe:** Kubernetes asks: "are you ready to receive traffic?" A pod might be running but still initializing — connecting to the database, loading config, warming up a cache. The readiness probe keeps it out of the load balancer rotation until it's actually ready.

**Resource Requests and Limits:** You specify how much CPU and memory a container needs (`request`) and the maximum it's allowed to use (`limit`). The scheduler uses requests to decide which node to place the pod on. Limits prevent one misbehaving container from starving every other container on the node.

**Pod Disruption Budgets:** Sets a minimum number of pods that must stay available during any disruption (rolling update, node drain). Protects against accidental downtime during maintenance.

**ReplicaSets:** Kubernetes continuously watches the cluster. If a pod crashes, a node goes down, or a container is killed, Kubernetes automatically replaces it to maintain the desired replica count.

**In this project:** Every service Deployment has a desired replica count. If a pod crashes, Kubernetes replaces it. The database uses a StatefulSet with a persistent volume — so data survives pod restarts.

---

## 9. Security

**Pillar: Zero Trust + Defense in Depth**

Security isn't a feature you add at the end. It's layered throughout the entire architecture — multiple independent security layers so that compromising one doesn't compromise everything.

**Authentication vs Authorization**
- *Authentication:* Who are you? Verify identity.
- *Authorization:* What are you allowed to do? Roles, permissions, access policies.

**JWT — JSON Web Token:** After login, the server returns a signed token that encodes your identity and permissions. Every subsequent request carries this token. The server verifies the signature without hitting the database. Stateless, scalable, session lives in the token not the server.

**bcrypt:** Passwords are never stored as plain text. bcrypt hashes the password with a random salt. Even if the database is compromised, the attacker gets hashes — computationally infeasible to reverse.

**Zero Trust:** Verify every request regardless of where it comes from. Never trust, always verify. Every service-to-service call gets authenticated. Even internal traffic.

**Kubernetes Secrets:** Credentials are stored as Kubernetes Secrets — not hardcoded in environment variables or code. Mounted into pods at runtime.

**IAM Roles — Least Privilege:** Every AWS resource gets only the permissions it needs. Our EKS nodes have IAM roles that allow them to pull images from ECR — nothing more. If a node is compromised, the blast radius is minimal.

**Network Policies:** Define which pods can talk to which other pods. By default every pod can reach every other pod. In a hardened production setup, you'd restrict this — the auth service only accepts traffic from the gateway.

**In this project:** JWT authentication in the auth service, bcrypt for password hashing, Kubernetes Secrets for database credentials, IAM roles for ECR access, and Helmet.js for HTTP security headers on every service.

---

## 10. Observability

**Pillar: Visibility + Debuggability + Operational Confidence**

A user reports the app is slow. Your system has 20 services. Which one is the bottleneck? Without observability you're guessing. With it, you know in seconds.

### The Three Pillars

**Metrics:** Quantitative measurements over time — request rate, error rate, CPU usage, response time, queue depth. Answers: *is the system behaving normally?* → Prometheus + Grafana.

**Logs:** A timestamped record of events — every request received, every error thrown, every database query. Answers: *what exactly happened?* → CloudWatch, ELK Stack.

**Traces:** Follow a single request as it moves through multiple services. A user clicks checkout — the request hits the gateway, goes to the order service, calls the product service, writes to the database. A trace shows the full journey with timing for each step. Answers: *where did this specific request slow down?* → Jaeger, OpenTelemetry.

### The RED Method — for services

| Metric | Question |
|--------|----------|
| **R**ate | How many requests per second? |
| **E**rrors | What percentage of requests are failing? |
| **D**uration | How long are requests taking? |

### The USE Method — for infrastructure

| Metric | Question |
|--------|----------|
| **U**tilization | How busy is the resource? |
| **S**aturation | Is it being asked to do more than it can handle? |
| **E**rrors | Is it producing errors? |

**In this project:** Every service exposes a `/metrics` endpoint. Prometheus scrapes all services every 15 seconds via the `ServiceMonitor` in the GitOps manifests. Grafana is provisioned with Prometheus as the default datasource and a pre-loaded boutique dashboard auto-imported via ConfigMap label.

---

## 11. Deployment Strategies

**Pillar: Risk Management + Continuous Delivery + Rollback Safety**

You've built a new feature. How do you get it to production without breaking anything?

| Strategy | How it works | Downtime | Rollback speed | Cost |
|----------|-------------|----------|---------------|------|
| **Recreate** | Stop all old, start all new | Yes | Slow | Low |
| **Rolling Update** | Replace instances one by one | No | Medium | Low |
| **Blue-Green** | Two identical environments, switch traffic | No | Instant | High (2x infra) |
| **Canary** | Send small % of traffic to new version, gradually increase | No | Instant | Low |
| **Feature Flags** | Deploy code, control rollout via config | No | Instant | Low |

**Rolling Update** is Kubernetes default — old and new versions run simultaneously, so your API must be backwards compatible during the transition.

**Canary Release** is what Netflix, Facebook, and Google use for major releases — send 5% of traffic to the new version, monitor metrics, gradually increase.

**In this project:** Kubernetes uses rolling updates by default. Every new image pushed to ECR gets deployed by updating the image tag in the GitOps manifests — ArgoCD rolls it out with zero downtime.

---

## 12. GitOps

**Pillar: Consistency + Auditability + Infrastructure as Code**

Someone SSH's into a production server and makes a manual change. Three months later something breaks. Nobody knows what changed, who changed it, or why. GitOps eliminates this problem entirely.

**The principle:** Git is the single source of truth for everything — application code, Kubernetes manifests, infrastructure config, Helm values. Nothing gets changed manually. Everything goes through a pull request.

**How it works:** ArgoCD runs inside the cluster and continuously watches a Git repository. When it detects a change in Git, it applies that change to the cluster. If someone manually changes something directly in the cluster, ArgoCD detects the drift and reverts it back to match Git.

**Pull vs Push deployment:**
- *Traditional CI/CD is push-based* — the pipeline authenticates with the cluster and pushes changes in. The cluster must be directly accessible from CI.
- *GitOps is pull-based* — ArgoCD runs inside the cluster and pulls changes from Git. Reduces the attack surface significantly.

**The audit trail:** Every change is a Git commit — who made it, when, why, and what exactly changed. Rolling back is a `git revert`. The entire history of your infrastructure is in version control.

**In this project:** The entire Kubernetes configuration lives in `gitops/k8s/`. The `argo-cd.yml` Application manifest tells ArgoCD to watch the `main` branch. Push a change — ArgoCD deploys it. Change an image tag — ArgoCD rolls it out. The cluster always reflects what's in Git.

---

## Summary

Every tool in this project exists to solve one of these problems:

| Problem | System Design Concept | Tool in This Project |
|---------|----------------------|---------------------|
| One server isn't enough | Distributed Systems | EKS cluster |
| Tightly coupled codebase | Microservices | 7 independent services |
| Services finding each other | Service Discovery | Kubernetes DNS |
| Traffic distribution | Load Balancing | ClusterIP + ALB |
| Handling failures | High Availability | Multi-AZ subnets |
| Handling traffic spikes | Autoscaling | HPA + KEDA |
| Containers crashing | Self-healing | Kubernetes probes + ReplicaSets |
| Credential leaks | Security | IAM + Secrets + JWT |
| Finding the bottleneck | Observability | Prometheus + Grafana + CloudWatch |
| Releasing safely | Deployment Strategies | Rolling updates |
| Manual changes breaking things | GitOps | ArgoCD |

Understanding these concepts means you understand *why* the project is built the way it is — not just how to run the commands.
