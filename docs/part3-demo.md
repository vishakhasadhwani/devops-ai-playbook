# Part 3 — Project Demo: Deploying the Full-Stack App

> Companion doc for the YouTube series: **DevOps Practice Guide** — Episode 3

---

## What We're Deploying

A full-stack application composed of:
- **Frontend** — React
- **Backend** — Node.js API
- **Database** — PostgreSQL
- **Observability** — Prometheus + Grafana
- **Orchestration** — Kubernetes (via ArgoCD + Kustomize)
- **Infrastructure** — Terraform (AWS)

---

## Prerequisites

| Tool | Version |
|------|---------|
| Docker | 24+ |
| kubectl | 1.28+ |
| Terraform | 1.5+ |
| ArgoCD CLI | 2.9+ |
| GitHub CLI (`gh`) | 2+ |

---

## Step 1 — Run Locally

```bash
git clone https://github.com/<your-org>/DevOps-Practice-Guide
cd DevOps-Practice-Guide/projects/fullstack-cicd-pipeline

docker compose up --build
```

Verify all services are healthy:
```bash
./health-check.sh
```

Open in browser:
- App: http://localhost:3000
- Grafana: http://localhost:3001 (admin / admin)
- Prometheus: http://localhost:9090

---

## Step 2 — Provision Cloud Infrastructure (Terraform)

```bash
cd projects/Infrastructure

# Review what will be created
terraform init
terraform plan -var-file="terraform.tfvars"

# Apply
terraform apply -var-file="terraform.tfvars"
```

What Terraform provisions:
- VPC, subnets, security groups
- EKS cluster (or equivalent)
- RDS PostgreSQL instance
- IAM roles for the pipeline

Key files:
```
projects/Infrastructure/
├── main.tf           # Core resources
├── variables.tf      # Input variables
├── outputs.tf        # Cluster endpoint, DB URL, etc.
├── provider.tf       # AWS provider config
├── terraform.tfvars  # Your environment values
└── modules/          # Reusable modules
```

---

## Step 3 — Configure kubectl

After `terraform apply`, grab the cluster context:
```bash
aws eks update-kubeconfig --region <region> --name <cluster-name>
kubectl get nodes
```

---

## Step 4 — Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for pods
kubectl wait --for=condition=available deployment -n argocd --all --timeout=120s

# Get initial admin password
argocd admin initial-password -n argocd
```

---

## Step 5 — Deploy the App via ArgoCD

```bash
kubectl apply -f gitops/namespace.yml
kubectl apply -f gitops/secrets.yml
kubectl apply -f gitops/argo-cd.yml
```

ArgoCD will now watch the `gitops/` directory and sync changes automatically.

Check sync status:
```bash
argocd app list
argocd app get devops-guide
```

Or open the ArgoCD UI:
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
# https://localhost:8080
```

---

## Step 6 — Trigger the CI/CD Pipeline

1. Make a small change (e.g., update a frontend string)
2. Commit and push to a feature branch
3. Open a PR — watch GitHub Actions run the CI pipeline
4. Merge to `main` — watch ArgoCD sync the new image to the cluster

```bash
git checkout -b demo/update-title
# make a change
git commit -am "demo: update page title"
git push origin demo/update-title
gh pr create --fill
```

---

## Step 7 — Verify Observability

```bash
kubectl port-forward svc/prometheus -n monitoring 9090:9090
kubectl port-forward svc/grafana -n monitoring 3000:3000
```

In Grafana, check:
- Request rate per service
- Error rate (should be 0%)
- Pod CPU and memory usage

---

## Step 8 — Teardown

```bash
# Remove ArgoCD app
argocd app delete devops-guide

# Destroy infrastructure
cd projects/Infrastructure
terraform destroy -var-file="terraform.tfvars"
```

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Pods in `CrashLoopBackOff` | `kubectl logs <pod>` |
| Image pull errors | Confirm registry credentials in `gitops/secrets.yml` |
| ArgoCD out of sync | `argocd app sync devops-guide` |
| Terraform plan fails | Verify AWS credentials: `aws sts get-caller-identity` |

---

## Where to Go Next
- [Part 2 — The Workflow](./part2-workflow.md)
- [Part 4 — AIOps Implementation](./part4-aiops.md): adding AI-driven operations to the stack
