"""
Kira write tools (#8): scale, restart, and roll back deployments in `boutique`.

Nothing here runs without an engineer clicking Approve in the UI (app.py).
Every action is checked against the allowlist in guardrails.py when proposed
and again right before it runs, and each step is logged as one JSON line to
stdout, which Fluent Bit ships to CloudWatch Logs.

Kubernetes access uses the pod's service account (Role in
gitops/k8s/aiops-assistant/rbac.yml), or ~/.kube/config when run locally.
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone

from guardrails import ActionNotAllowed, check_action

NAMESPACE = "boutique"
ROLLOUT_TIMEOUT_SECONDS = 90
ROLLOUT_POLL_SECONDS = 3
REVISION_ANNOTATION = "deployment.kubernetes.io/revision"
RESTARTED_AT_ANNOTATION = "kubectl.kubernetes.io/restartedAt"

_REASON = {"type": "string", "description": "Why this action fixes the problem, citing the evidence. Shown to the engineer who approves it."}
_DEPLOYMENT = {"type": "string", "description": "Deployment name in the boutique namespace, e.g. orders"}

TOOL_SPECS = [
    {"toolSpec": {
        "name": "scale_deployment",
        "description": "Set a deployment's replica count (1-5). Requires engineer approval before it runs.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "deployment": _DEPLOYMENT,
            "replicas": {"type": "integer", "description": "New replica count, 1-5"},
            "reason": _REASON,
        }, "required": ["deployment", "replicas", "reason"]}},
    }},
    {"toolSpec": {
        "name": "restart_deployment",
        "description": "Rolling restart of a deployment's pods (like kubectl rollout restart). Requires engineer approval before it runs.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "deployment": _DEPLOYMENT,
            "reason": _REASON,
        }, "required": ["deployment", "reason"]}},
    }},
    {"toolSpec": {
        "name": "rollback_deployment",
        "description": "Roll a deployment back to its previous revision (like kubectl rollout undo). Requires engineer approval before it runs.",
        "inputSchema": {"json": {"type": "object", "properties": {
            "deployment": _DEPLOYMENT,
            "reason": _REASON,
        }, "required": ["deployment", "reason"]}},
    }},
]
WRITE_TOOLS = {spec["toolSpec"]["name"] for spec in TOOL_SPECS}

ARGO_WARNING = {
    "scale_deployment": "Temporary: the next Argo CD sync resets replicas to the value in git. Commit the new count to make it permanent.",
    "restart_deployment": None,
    "rollback_deployment": "Argo CD self-heal reverts this to the image in git within seconds when enabled. Revert the bad commit in git to make it stick.",
}

log = logging.getLogger("kira.actions")
if not log.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(_handler)
    log.setLevel(logging.INFO)
    log.propagate = False


def log_action(event, name, tool_input, session_id=None, **extra):
    """One JSON line per step: proposed, blocked, approved, rejected, executed, failed."""
    log.info(json.dumps({
        "kira_action": event,
        "time": datetime.now(timezone.utc).isoformat(),
        "session": session_id,
        "action": name,
        "namespace": NAMESPACE,
        "deployment": tool_input.get("deployment"),
        "replicas": tool_input.get("replicas"),
        "reason": tool_input.get("reason"),
        **extra,
    }))


def normalize(name, tool_input):
    """Validate a proposed action against the allowlist; return the cleaned input."""
    clean = {"deployment": tool_input.get("deployment"), "reason": str(tool_input.get("reason", ""))}
    replicas = tool_input.get("replicas")
    if name == "scale_deployment":
        if isinstance(replicas, str) and replicas.strip().isdigit():
            replicas = int(replicas)
        clean["replicas"] = replicas
    check_action(name, NAMESPACE, clean["deployment"], replicas=clean.get("replicas"))
    return clean


def _apps_api():
    from kubernetes import client, config

    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.AppsV1Api()


def _images(template):
    return {c.name: c.image for c in template.spec.containers}


def _previous_replicaset(api, deployment):
    """The ReplicaSet of the revision before the current one, or None."""
    current = int(deployment.metadata.annotations.get(REVISION_ANNOTATION, "0"))
    selector = ",".join(f"{k}={v}" for k, v in deployment.spec.selector.match_labels.items())
    owned = [
        rs for rs in api.list_namespaced_replica_set(NAMESPACE, label_selector=selector).items
        if any(ref.uid == deployment.metadata.uid for ref in rs.metadata.owner_references or [])
    ]
    older = [rs for rs in owned if int((rs.metadata.annotations or {}).get(REVISION_ANNOTATION, "0")) < current]
    return max(older, key=lambda rs: int(rs.metadata.annotations[REVISION_ANNOTATION]), default=None)


def preview(name, tool_input, api=None):
    """Current state and what will change, for the approval card."""
    api = api or _apps_api()
    dep = api.read_namespaced_deployment(tool_input["deployment"], NAMESPACE)
    info = {
        "current_replicas": dep.spec.replicas,
        "available_replicas": dep.status.available_replicas or 0,
        "current_images": _images(dep.spec.template),
        "revision": dep.metadata.annotations.get(REVISION_ANNOTATION),
        "warning": ARGO_WARNING[name],
    }
    if name == "scale_deployment":
        info["change"] = f"replicas {dep.spec.replicas} → {tool_input['replicas']}"
    elif name == "restart_deployment":
        info["change"] = f"rolling restart of {dep.spec.replicas} pod(s)"
    else:
        prev = _previous_replicaset(api, dep)
        if prev is None:
            info["change"] = "no previous revision to roll back to"
        else:
            info["change"] = f"revision {info['revision']} → {prev.metadata.annotations[REVISION_ANNOTATION]}"
            info["rollback_images"] = _images(prev.spec.template)
    return info


def _wait_for_rollout(api, deployment_name):
    """Poll until the rollout finishes or times out; return the final status."""
    deadline = time.monotonic() + ROLLOUT_TIMEOUT_SECONDS
    while True:
        dep = api.read_namespaced_deployment_status(deployment_name, NAMESPACE)
        s = dep.status
        desired = dep.spec.replicas or 0
        done = (
            (s.observed_generation or 0) >= dep.metadata.generation
            and (s.updated_replicas or 0) == desired
            and (s.available_replicas or 0) == desired
            and (s.replicas or 0) == desired
        )
        if done or time.monotonic() >= deadline:
            return {
                "rollout_complete": done,
                "desired_replicas": desired,
                "available_replicas": s.available_replicas or 0,
                "updated_replicas": s.updated_replicas or 0,
            }
        time.sleep(ROLLOUT_POLL_SECONDS)


def execute(name, tool_input, session_id=None, api=None):
    """Run an approved action, wait for the rollout, and return the result for Kira."""
    try:
        clean = normalize(name, tool_input)  # re-check: never trust that the proposal was checked
    except ActionNotAllowed as e:
        log_action("blocked", name, tool_input, session_id, error=str(e))
        return {"status": "error", "message": f"Action not allowed: {e}"}

    deployment = clean["deployment"]
    try:
        api = api or _apps_api()
        if name == "scale_deployment":
            api.patch_namespaced_deployment_scale(deployment, NAMESPACE, {"spec": {"replicas": clean["replicas"]}})
        elif name == "restart_deployment":
            now = datetime.now(timezone.utc).isoformat()
            api.patch_namespaced_deployment(deployment, NAMESPACE, {
                "spec": {"template": {"metadata": {"annotations": {RESTARTED_AT_ANNOTATION: now}}}}})
        else:
            dep = api.read_namespaced_deployment(deployment, NAMESPACE)
            prev = _previous_replicaset(api, dep)
            if prev is None:
                log_action("failed", name, clean, session_id, error="no previous revision")
                return {"status": "error", "message": f"{deployment} has no previous revision to roll back to"}
            template = api.api_client.sanitize_for_serialization(prev.spec.template)
            template["metadata"].get("labels", {}).pop("pod-template-hash", None)
            api.patch_namespaced_deployment(deployment, NAMESPACE, [
                {"op": "replace", "path": "/spec/template", "value": template}])

        rollout = _wait_for_rollout(api, deployment)
    except Exception as e:
        log_action("failed", name, clean, session_id, error=f"{type(e).__name__}: {e}")
        return {"status": "error", "message": f"{type(e).__name__}: {e}"}

    log_action("executed", name, clean, session_id, **rollout)
    return {
        "status": "ok" if rollout["rollout_complete"] else "rollout_incomplete",
        "action": name,
        "deployment": deployment,
        **rollout,
        "note": ARGO_WARNING[name],
    }
