# Claude Code Setup

This project uses [Claude Code](https://claude.ai/claude-code) — Anthropic's AI coding assistant — as a hands-on tool throughout the DevOps workflow. This document covers how Claude is configured in this project: the `CLAUDE.md` instruction file and the MCP servers that extend its capabilities.

---

## What is Claude Code?

Claude Code is a CLI-based AI assistant that works directly in your terminal and IDE. It can read files, run commands, write code, interact with AWS, manage Kubernetes, and reason about infrastructure — all within your project context.

In this project, Claude Code is used to:
- Assist with Terraform and Kubernetes configuration
- Query EKS clusters and troubleshoot pods
- Interact with AWS services (ECR, EKS, Bedrock, pricing)
- Help write and deploy the AIOps assistant (Kira)

---

## CLAUDE.md — Project Instructions

`CLAUDE.md` is a file at the root of the project that Claude reads automatically at the start of every session. It sets rules and expectations for how Claude should behave within this specific project.

**Current `CLAUDE.md` for this project:**

```
You are operating in safe execution mode.

Before executing any command:
- Before taking any action, briefly explain what you're about to do in 1-2 simple sentences
- Use plain language, avoid jargon
- Say WHY, not just WHAT
- Then proceed with the action

Always prefer clear reasoning before action.
```

### What this does

This instructs Claude to explain its reasoning before taking any action — so you always know what's about to happen and why, rather than commands running silently. This is particularly useful when working with live AWS infrastructure where unintended actions can have real consequences.

### How to customise CLAUDE.md

You can add any project-specific rules. Common examples:

```markdown
# Always use the boutique namespace unless told otherwise
# Never run terraform apply without showing the plan first
# Prefer kubectl over raw AWS CLI for cluster operations
# Branch naming convention: feature/<name>, fix/<name>
```

CLAUDE.md supports nested files too — you can place a `CLAUDE.md` inside any subdirectory and Claude will read it when working in that directory.

---

## MCP Servers

MCP (Model Context Protocol) servers extend Claude's capabilities beyond the built-in tools. They run as background processes and expose additional tools that Claude can call — for AWS operations, Terraform, pricing lookups, and more.

MCP servers are configured in `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "awslabs.core-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.core-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "default",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.terraform-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.terraform-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.aws-pricing-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-pricing-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.eks-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.eks-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

> Replace `us-east-1` with your AWS region.

---

### awslabs.eks-mcp-server

**What it does:** Gives Claude direct access to your EKS clusters and Kubernetes resources without needing `kubectl` installed or configured separately.

**Key capabilities:**
- List and inspect pods, deployments, services, and events across namespaces
- Apply Kubernetes YAML manifests to a cluster
- Stream pod logs and CloudWatch metrics
- Describe EKS cluster config, node groups, and VPC networking
- Troubleshoot using the EKS troubleshooting guide
- Generate application manifests for a given container image

**Example use in this project:**

> "Why is the order-service pod crashing?"

Claude will use this server to check pod events, read logs, and inspect the deployment spec — without you running any kubectl commands manually.

**Setup requirement:** Your AWS credentials must have EKS read permissions. The IAM policy `AmazonEKSClusterPolicy` on your user or role is sufficient for read-only operations.

---

### awslabs.terraform-mcp-server

**What it does:** Gives Claude the ability to run Terraform commands and search provider documentation.

**Key capabilities:**
- Run `terraform init`, `plan`, `apply`, `validate`, and `destroy`
- Search AWS and AWSCC provider resource documentation
- Search AWS-IA Terraform modules (Bedrock, OpenSearch, SageMaker)
- Run Checkov security scans on Terraform code
- Analyse existing modules from the Terraform Registry

**Example use in this project:**

> "What Terraform resource do I need to create an EKS node group?"

Claude will search the AWSCC and AWS provider docs and return the correct resource schema and example usage.

> "Run terraform plan in the Infrastructure directory"

Claude will execute it and summarise what will be created, changed, or destroyed.

**Note:** This server is deprecated in favour of HashiCorp's official Terraform MCP server, but remains functional.

---

### awslabs.aws-pricing-mcp-server

**What it does:** Gives Claude access to live AWS pricing data so it can estimate costs for services before you provision them.

**Key capabilities:**
- Look up pricing for any AWS service (EC2, EKS, Bedrock, Lambda, RDS, etc.)
- Filter by region, instance type, and other attributes
- Generate structured cost analysis reports
- Estimate Bedrock inference costs including Knowledge Base OCU minimums
- Retrieve bulk pricing data for historical analysis

**Example use in this project:**

> "How much will this EKS setup cost per month?"

Claude will query the pricing API for the node instance type, data transfer, and EKS cluster fee, then return a cost breakdown.

> "What does it cost to run the Bedrock Agent daily?"

Claude will look up the Qwen model pricing and factor in the Lambda invocations from the action groups.

---

### awslabs.core-mcp-server

**What it does:** A proxy/orchestration layer that coordinates the other MCP servers. It allows Claude to route requests to the right server automatically.

**Note:** This server is deprecated. Modern Claude Code clients support multi-server configurations natively, so each server above is registered directly. It is kept here for backwards compatibility but will be removed in a future update. You can safely remove it from your config if all other servers are registered individually.

---

## Prerequisites

Install `uv` (the Python package runner used to launch MCP servers):

```bash
# macOS
brew install uv

# or via pip
pip install uv
```

Verify:
```bash
uvx --version
```

All MCP servers are fetched and run automatically by `uvx` — no separate install step needed.

---

## Verifying MCP Servers are Running

Start a Claude Code session and check which MCP servers are connected:

```
/mcp
```

You should see all four servers listed as `connected`. If any show as `failed`, check that:
- `uv` is installed and on your PATH
- Your AWS credentials are configured (`aws sts get-caller-identity`)
- The `AWS_REGION` in your settings.json matches your target region

---

## How Claude Uses These Tools in This Project

| Task | MCP Server Used |
|------|----------------|
| Check pod logs / health | `eks-mcp-server` |
| Apply k8s manifests | `eks-mcp-server` |
| Run terraform plan/apply | `terraform-mcp-server` |
| Search provider docs | `terraform-mcp-server` |
| Estimate infrastructure cost | `aws-pricing-mcp-server` |
| Bedrock agent cost analysis | `aws-pricing-mcp-server` |
| Cluster and node group info | `eks-mcp-server` |
