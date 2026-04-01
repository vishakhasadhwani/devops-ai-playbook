# Part 4 — AIOps Implementation

> Companion doc for the YouTube series: **DevOps Practice Guide** — Episode 4

---

## What is AIOps?

AIOps (Artificial Intelligence for IT Operations) applies machine learning and AI to automate and enhance operational tasks — anomaly detection, root cause analysis, predictive scaling, and intelligent alerting — on top of the observability stack you already have.

---

## AIOps Layers in This Project

```
┌────────────────────────────────────────────────┐
│              AI / LLM Layer                    │
│  (Claude API — analysis, summarisation, RCA)   │
├────────────────────────────────────────────────┤
│         Anomaly Detection Layer                │
│  (ML models on Prometheus metrics stream)      │
├────────────────────────────────────────────────┤
│           Observability Layer                  │
│  Prometheus │ Grafana │ Loki │ OpenTelemetry   │
├────────────────────────────────────────────────┤
│          Infrastructure Layer                  │
│  Kubernetes │ Terraform │ GitHub Actions       │
└────────────────────────────────────────────────┘
```

---

## Use Case 1 — Intelligent Alerting

**Problem**: Raw Prometheus alerts fire too often and lack context.

**Solution**: Wrap alerts with an AI layer that:
1. Receives the alert payload (Alertmanager webhook)
2. Queries recent metrics and logs for context
3. Calls the Claude API to generate a plain-English summary and suggested action
4. Posts the enriched alert to Slack / PagerDuty

### Example Flow

```
Prometheus Alert
      │
      ▼
Alertmanager Webhook
      │
      ▼
AIOps Service (Node.js / Python)
  ├── Fetch last 30 min of metrics from Prometheus
  ├── Fetch recent error logs from Loki
  └── Call Claude API →
        "Summarise this incident and suggest the most likely root cause"
      │
      ▼
Enriched Notification → Slack / PagerDuty
```

### Claude API Call (Node.js example)

```javascript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic(); // uses ANTHROPIC_API_KEY env var

async function enrichAlert(alertPayload, recentMetrics, recentLogs) {
  const message = await client.messages.create({
    model: "claude-opus-4-6",
    max_tokens: 512,
    messages: [
      {
        role: "user",
        content: `
You are an on-call SRE assistant. Analyse this alert and provide:
1. A plain-English summary (2 sentences max)
2. Most likely root cause
3. Recommended immediate action

Alert: ${JSON.stringify(alertPayload)}
Recent metrics: ${recentMetrics}
Recent logs: ${recentLogs}
        `,
      },
    ],
  });
  return message.content[0].text;
}
```

---

## Use Case 2 — Anomaly Detection on Metrics

**Problem**: Simple threshold alerts miss gradual degradation.

**Solution**: Run a lightweight anomaly detector against the Prometheus metrics stream.

### Approach: Z-score on sliding window

```python
import requests, numpy as np

PROMETHEUS = "http://localhost:9090"

def fetch_metric(query, duration="30m"):
    r = requests.get(f"{PROMETHEUS}/api/v1/query_range", params={
        "query": query,
        "start": f"now-{duration}",
        "end": "now",
        "step": "60s",
    })
    values = [float(v[1]) for v in r.json()["data"]["result"][0]["values"]]
    return values

def is_anomalous(values, threshold=3.0):
    arr = np.array(values)
    z_scores = (arr - arr.mean()) / arr.std()
    return bool(abs(z_scores[-1]) > threshold)

# Example: detect anomaly in HTTP error rate
errors = fetch_metric('rate(http_requests_total{status=~"5.."}[5m])')
if is_anomalous(errors):
    print("Anomaly detected in error rate — investigate!")
```

---

## Use Case 3 — AI-Powered Root Cause Analysis (RCA)

When an incident occurs, automatically correlate signals across metrics, logs, and traces, then generate an RCA report.

### Pipeline

```
Incident Detected
      │
      ▼
Collect correlated signals
  ├── Prometheus: which metrics spiked?
  ├── Loki: which services logged errors?
  └── Jaeger: which traces show latency?
      │
      ▼
Claude API → Generate RCA report
      │
      ▼
Post to incident Slack channel + attach to PagerDuty incident
```

### Prompt Template

```
You are an expert SRE performing a root cause analysis.

Timeline of events:
{timeline}

Metrics that changed significantly:
{metrics_summary}

Relevant error logs:
{log_summary}

Slow traces:
{trace_summary}

Write a concise RCA with:
- What happened
- Why it happened (root cause)
- Impact
- Immediate fix applied
- Long-term recommendation
```

---

## Use Case 4 — Predictive Autoscaling

Instead of reactive HPA (Horizontal Pod Autoscaler), train a simple time-series model on historical traffic to pre-scale before load arrives.

```
Historical Prometheus data
        │
        ▼
Train Prophet / ARIMA model
        │
        ▼
Forecast next 30-min load
        │
        ▼
kubectl scale deployment backend --replicas=<predicted>
```

---

## Setting Up the AIOps Service

### Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...
PROMETHEUS_URL=http://prometheus:9090
LOKI_URL=http://loki:3100
ALERTMANAGER_WEBHOOK_PORT=5001
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### Minimal Service Structure

```
aiops/
├── main.py               # Webhook receiver + orchestrator
├── alert_enricher.py     # Claude API integration
├── anomaly_detector.py   # Z-score / ML detection
├── rca_generator.py      # RCA prompt + Claude API call
├── scaler.py             # Predictive autoscaling
├── requirements.txt
└── Dockerfile
```

### Deploy to Kubernetes

```yaml
# aiops-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiops-service
  namespace: monitoring
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: aiops
          image: ghcr.io/<org>/aiops-service:latest
          envFrom:
            - secretRef:
                name: aiops-secrets
```

---

## Security Considerations

- Store `ANTHROPIC_API_KEY` in a Kubernetes Secret, never in code or ConfigMaps
- Limit the AIOps service's RBAC to read-only on pods/metrics; write-only on scaling
- Rate-limit Claude API calls to avoid runaway costs during alert storms

---

## Summary: What AIOps Adds to Your Stack

| Feature | Before AIOps | After AIOps |
|---------|-------------|------------|
| Alerts | Raw threshold triggers | Enriched, human-readable summaries |
| Anomaly detection | Static thresholds | ML-based dynamic detection |
| Root cause analysis | Manual investigation | AI-generated RCA in minutes |
| Scaling | Reactive HPA | Predictive pre-scaling |

---

## References

- [Anthropic Claude API docs](https://docs.anthropic.com)
- [Prometheus query API](https://prometheus.io/docs/prometheus/latest/querying/api/)
- [Kubernetes HPA docs](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Part 3 — Project Demo](./part3-demo.md)
