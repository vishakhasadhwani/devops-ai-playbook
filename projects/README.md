# EKS Deployment Guide

This guide walks through deploying the boutique microservices application end-to-end on Amazon EKS — from provisioning infrastructure to running the full stack with GitOps, monitoring, and log forwarding.

---

## Infrastructure Diagram

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

---

## Service Overview

| Service | Port | Role |
|---------|------|------|
| **Frontend** | 3000 | React UI |
| **Gateway** | 3001 | API Gateway — routes all requests to backend services |
| **Auth** | 3002 | Login and registration |
| **Product Service** | 3003 | Product catalog and inventory |
| **Order Service** | 3004 | Cart and checkout |
| **Orders** | 3005 | Order history and management |
| **User Service** | 3006 | User profiles and account management |
| **PostgreSQL** | 5432 | Database — auth_db, products_db, orders_db, users_db |
| **Prometheus** | 9090 | Metrics collection |
| **Grafana** | 8080 | Metrics dashboards |

---

## Prerequisites

Before starting, make sure you have the following installed and configured:

- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) — configured with credentials
- [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.5
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm](https://helm.sh/docs/intro/install/)
- [Git](https://git-scm.com/)
- Python 3.10+ (for AIOps assistant only)

---

## Step 1: Configure AWS CLI

```bash
aws configure
```

Enter when prompted:
- **AWS Access Key ID** — from your IAM user
- **AWS Secret Access Key** — from your IAM user
- **Default region** — e.g. `us-east-1`
- **Default output format** — `json`

Verify it works:

```bash
aws sts get-caller-identity
```

---

## Step 2: Set Up GitHub Actions Secrets

The CI pipeline builds Docker images and pushes them to ECR. It needs AWS credentials and your account details stored as GitHub Actions secrets.

### 2a. Create an IAM User for CI

1. Go to **AWS Console → IAM → Users → Create user**
2. Name it `github-actions-ci`
3. Attach the following managed policies:
   - `AmazonEC2ContainerRegistryFullAccess`
   - `AmazonS3ReadOnlyAccess` *(optional, for Terraform state)*
4. Go to the user → **Security credentials → Create access key**
5. Select **Application running outside AWS** → create
6. Copy the **Access Key ID** and **Secret Access Key** — you only see the secret once

### 2b. Add Secrets to GitHub

Go to your GitHub repository → **Settings → Secrets and variables → Actions → New repository secret**

Add the following secrets one by one:

| Secret Name | Value |
|-------------|-------|
| `AWS_ACCESS_KEY_ID` | Access key ID from Step 2a |
| `AWS_SECRET_ACCESS_KEY` | Secret access key from Step 2a |
| `AWS_REGION` | Your AWS region (e.g. `us-east-1`) |
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID |

To find your account ID:
```bash
aws sts get-caller-identity --query Account --output text
```

---

## Step 3: Provision Infrastructure with Terraform

The Terraform configuration in `projects/Infrastructure/` provisions:
- VPC with 3 public subnets
- EKS cluster (`eks-cluster`) with a managed node group
- ECR repositories for all 7 services
- ArgoCD and Prometheus/Grafana (via Helm) installed into the cluster

```bash
cd projects/Infrastructure
terraform init
terraform plan
terraform apply --auto-approve
```

This takes ~15 minutes. When complete, Terraform outputs the cluster name and ECR repository URLs.

---

## Step 4: Configure kubectl

Point kubectl at your new EKS cluster:

```bash
aws eks update-kubeconfig \
  --region us-east-1 \
  --name eks-cluster
```

Verify the connection:

```bash
kubectl get nodes
```

You should see your node(s) in `Ready` status.

---

## Step 5: Run the CI Pipeline

The pipeline is triggered automatically on every push to `main`. It:
1. Builds Docker images for all 7 services in parallel
2. Pushes them to ECR
3. Updates the image tags in the k8s manifests and commits back to the repo

### Trigger the pipeline

Push any change to the `main` branch:

```bash
git add .
git commit -m "trigger CI"
git push origin main
```

### Check pipeline status

1. Go to your GitHub repository → **Actions** tab
2. Click the latest workflow run — **Boutique CI Pipeline**
3. You will see two jobs:
   - **build-and-push** — runs 7 parallel matrix jobs (one per service). Each job builds and pushes a Docker image to ECR.
   - **update-manifests** — runs after all builds succeed. Updates the image tags in `gitops/k8s/` and commits back to the repo.
4. Click any job to expand and see logs per step
5. A green checkmark means the job succeeded. A red X means it failed — click the step to read the error.

### Verify images in ECR

Once the pipeline succeeds, confirm images were pushed:

```bash
aws ecr describe-images \
  --repository-name frontend \
  --region us-east-1 \
  --query 'imageDetails[*].imageTags' \
  --output table
```

The tag will match the commit SHA from the pipeline run.

---

## Step 6: Apply Kubernetes Manifests

Apply all resources using Kustomize:

```bash
kubectl apply -k gitops/
```

This creates the `boutique` namespace and deploys all services, the database, secrets, and monitoring resources.

Check that everything is coming up:

```bash
kubectl get pods -n boutique
kubectl get pods -n monitoring
kubectl get pods -n argocd
```

Wait until all pods show `Running` or `Completed`. This takes 2–3 minutes.

---

## Step 7: Restore the Database

The application needs seed data loaded into PostgreSQL. A Kubernetes Job handles this automatically, but it must be applied after the database pod is running.

### 7a. Wait for the database pod to be ready

```bash
kubectl get pods -n boutique -l app=boutique-postgres
```

Wait until `STATUS` shows `Running` and `READY` shows `1/1`.

### 7b. Apply the restore job

```bash
kubectl apply -f gitops/k8s/database/restore-job.yml
```

### 7c. Monitor the restore job

```bash
kubectl get pods -n boutique -l job-name=boutique-db-restore
```

The pod will show `Running` briefly then `Completed`. This is expected — it means the restore finished successfully.

To see the restore logs:

```bash
kubectl logs -n boutique -l job-name=boutique-db-restore
```

You should see SQL commands being executed. The job loads schema and seed data into all 4 databases (`auth_db`, `products_db`, `orders_db`, `users_db`).

---

## Step 8: Configure ArgoCD

Apply the ArgoCD Application manifest to register the boutique app for GitOps:

```bash
kubectl apply -f gitops/argo-cd.yml -n argocd
```

ArgoCD will now watch the `main` branch and sync any changes to `gitops/` into the cluster automatically.

---

## Step 9: Set Up Log Forwarding (Optional)

To forward pod logs to CloudWatch, install Fluent Bit:

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

Verify it's running:

```bash
kubectl get pods -n amazon-cloudwatch
```

Logs will appear in CloudWatch under the log group `/eks/boutique/pods`.

---

## Port Forwarding

Run all port forwards in the background to access services locally:

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

- Username: `admin`
- Password: output from above

### ArgoCD

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

- Username: `admin`
- Password: output from above

---

## Verification Commands

```bash
# All pods across namespaces
kubectl get pods -n boutique
kubectl get pods -n monitoring
kubectl get pods -n argocd
kubectl get pods -n amazon-cloudwatch

# Services
kubectl get svc -n boutique
kubectl get svc -n monitoring

# ArgoCD sync status
kubectl get application -n argocd
```

---

## Logs

```bash
# Any service
kubectl logs -n boutique deploy/<service-name>

# ArgoCD sync issues
kubectl logs -n argocd deploy/argocd-repo-server

# Database restore job
kubectl logs -n boutique -l job-name=boutique-db-restore
```

---

## Useful Alias

```bash
alias k=kubectl
```

Add to `~/.zshrc` or `~/.bashrc` to make it permanent.

---

## Local Development Setup

To run the application locally without Kubernetes:

```bash
cd projects/boutique-microservices
npm install
npm run dev          # starts all services
```

Or with Docker Compose:

```bash
docker-compose -f docker-compose.yml up -d
docker ps            # verify containers
docker-compose -f docker-compose.yml down
```

Local URLs:
- Frontend: http://localhost:3000
- Grafana: http://localhost:3007 (admin / admin)
- Prometheus: http://localhost:9090

---

## Cleanup

To tear down all AWS infrastructure:

```bash
cd projects/Infrastructure
terraform destroy --auto-approve
```
