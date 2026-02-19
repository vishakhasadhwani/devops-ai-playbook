# EKS Deployment Guide

This guide outlines the steps to deploy the boutique microservices application on Amazon EKS.

---

## Important: GitHub Actions Secrets

> **Note:** The GitHub Actions secrets are currently configured with Anish's AWS credentials for testing purposes. 
> 
> For your own deployment, please update the following secrets in your GitHub repository with your own credentials:
> 
> - `AWS_ACCESS_KEY_ID`
> - `AWS_SECRET_ACCESS_KEY`
> - `AWS_REGION`
> - `AWS_ACCOUNT_ID`
> 
> Go to: **Settings → Secrets and variables → Actions** in your GitHub repository to update them.

> Currently the pipeline is setup for branch name project-demo, to navigate to CI yml file **Actions -> click on any of the runs -> ci.yml 
---

## Prerequisites

- AWS CLI configured with access key and secret key
- Terraform installed
- kubectl installed
- AWS credentials with appropriate permissions
- Node.js and npm installed (for local setup)

---

## Infrastructure Diagram

```
                                    ┌─────────────┐
                                    │   Frontend  │
                                    │ (Port 3000) │
                                    │             │
                                    └──────┬──────┘
                                           │
                                    ┌──────▼──────┐
                                    │   Gateway   │
                                    │  (Port 3001)│
                                    │(API Gateway)│
                                    └──────┬──────┘
                                           │
            ┌──────────────────────────────┼──────────────────────────────┐
            │                              │                              │
     ┌──────▼──────┐              ┌───────▼───────┐             ┌───────▼───────┐
     │    Auth     │              │Product service│             │     Users     │
     │  (Port 3002)│              │   (Port 3003) │             │  (Port 3006)  │
     │  (Login,    │              │  (Catalog,    │             │  (Profile,    │
     │  Register)  │              │   Inventory)  │             │   Manage)     │
     └──────┬──────┘              └───────┬───────┘             └───────┬───────┘
            │                              │                              │
     ┌──────▼──────┐              ┌───────▼───────┐             ┌───────▼───────┐
     │   Orders    │              │ Order Service │             │     Orders    │
     │  (Port 3004)│              │   (Port 3005) │             │  (Management) │
     │ (Cart,      │              │               │             │  (Port 3005)  │
     │  Checkout)  │              │               │             └───────────────┘
     └─────────────┘              └───────────────┘
            │
     ┌──────▼──────┐
     │  PostgreSQL │
     │  (Port 5432)│
     │  (Database) │
     └─────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        Monitoring Stack                                    │
│  ┌─────────────┐                           ┌─────────────┐                 │
│  │ Prometheus  │◄──────────────────────────│   Grafana   │                 │
│  │ (Port 9090) │                           │  (Port 3007)│                 │
│  └─────────────┘                           └─────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Service Overview

| Service | Port | Role |
|---------|------|------|
| **Frontend** | 3000 (ext) → 80 (int) | React UI - User interface for the boutique application |
| **Gateway** | 3001 | API Gateway - Routes requests to backend services, handles load balancing |
| **Auth** | 3002 | Authentication - Login, register, JWT token management |
| **Product Service** | 3003 | Product Catalog - Product listings, inventory management |
| **Order Service** | 3004 | Order Processing - Cart, checkout, order placement |
| **Orders** | 3005 | Order Management - Order history, tracking, management |
| **User Service** | 3006 | User Management - User profiles, preferences, account management |
| **PostgreSQL** | 5432 | Database - Stores all application data (auth_db, products_db, orders_db, users_db) |
| **Prometheus** | 9090 | Monitoring - Metrics collection and storage |
| **Grafana** | 3007 | Visualization - Dashboards and metrics visualization |

---

## Local Development Setup (Manual Commands)

If you want to run the application locally without Docker, follow these steps:

### Step 1: Install Dependencies

Navigate to the project directory and install dependencies:

```bash
cd boutique-microservices
npm install
```

### Step 2: Build the Application

Build all backend services:

```bash
cd boutique-microservices
npm run build:backend
```

Build frontend:

```bash
npm run build:frontend
```

Build everything:

```bash
npm run build:frontend
npm run build:backend
```
Start the services :

```bash
npm run dev:frontend
npm run dev:backend
```

### Step 3: Start the Services

Start all backend services:

```bash
cd boutique-microservices
npm run dev:backend
```

Start frontend:

```bash
npm run dev:frontend
```

Or start everything:

```bash
npm run dev
```

### Step 4: Run with Docker Compose

Start all services using Docker Compose:

```bash
docker-compose -f docker-compose.yml up -d
```

### Step 5: Verify Services

Check the running containers:

```bash
docker ps
```

---

## Step 1: Configure AWS CLI

```bash
aws configure
```

Enter your:
- AWS Access Key ID
- AWS Secret Access Key
- Default region name
- Default output format

---

## Step 2: Initialize and Apply Terraform

Navigate to the Infrastructure directory and initialize Terraform:

```bash
cd Infrastructure
terraform init
```

Review the infrastructure plan:

```bash
terraform plan
```

Apply the infrastructure changes:

```bash
terraform apply --auto-approve
```

---

## Step 3: Configure kubectl for EKS

Update kubeconfig to connect to your EKS cluster:

```bash
aws eks update-kubeconfig \
  --region <region> \
  --name eks-cluster
```

Create a short alias for kubectl:

```bash
alias k=kubectl
```

---

## Step 4: Run CI/CD Pipeline

1. Navigate to your project demo pipeline in GitHub
2. Run the pipeline using the `project-demo` branch

---

## Step 5: Update Image Tags

1. Go to any one ECR repository and copy the tag of one service ( tag is the commit ID )
2. Update the image tag in the deployment files:
   - `gitops/k8s/backend/` - for all backend services
   - `gitops/k8s/frontend/` - for frontend service

Paste the same tag in all service deployments.

---

## Step 6: Apply Kubernetes Manifests

Apply all Kubernetes resources:

```bash
cd gitops/k8s
kubectl apply -k .
```

---

## Step 7: Restore Database

Once the database pod is up, run the restore job:

```bash
kubectl apply -f gitops/k8s/database/restore-job.yml
```

---

## Verification Commands

### Check pods and services in boutique namespace:

```bash
k get po -n boutique
k get svc -n boutique
```

### Check services in argocd namespace:

```bash
k get svc -n argocd
```

### Check services in monitoring namespace:

```bash
k get svc -n monitoring
```

---

## Port Forwarding Commands

### Frontend:

```bash
kubectl port-forward svc/frontend 3000:3000 -n boutique
```

### Gateway:

```bash
kubectl port-forward svc/gateway 3001:3001 -n boutique
```

# To view the application metrics 
```bash
localhost:3001/metrics
```

### ArgoCD:

```bash
kubectl port-forward svc/argocd-server -n argocd 9000:80
```

### Grafana:

```bash
kubectl port-forward svc/kube-prometheus-stack-grafana 3100:80 -n monitoring
```

### Prometheus:

```bash
kubectl port-forward svc/prometheus-service 9090:9090 -n monitoring ( not too sure with the service name ) 
```

---

## Credentials

### Grafana

Get the Grafana admin password:

```bash
kubectl get secret kube-prometheus-stack-grafana -n monitoring -o jsonpath="{.data.admin-password}" | base64 --decode
```
- Username: `admin`


### ArgoCD

Get the ArgoCD admin password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

- Username: `admin`
- Password: (output from above command)

---

## Logs

### ArgoCD Repo Server Logs

```bash
kubectl logs -n argocd deploy/argocd-repo-server
```

---

## Useful Alias

Add this to your shell profile for convenience:

```bash
alias k=kubectl
```


## Cleanup all the resources 

```bash
terraform destroy --auto-approve
```

### For your reference and easier implementation, the terraform.tfvars have the hardcoded value in the repo inside the infrastructure folder 