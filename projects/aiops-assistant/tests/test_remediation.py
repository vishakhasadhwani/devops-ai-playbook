"""
Tests for Kira's write tools and approval flow (#8).

    cd projects/aiops-assistant && python -m unittest discover tests
"""

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

from kubernetes import client

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import agent  # noqa: E402
import remediation  # noqa: E402

from test_guardrails import final_answer, make_agent, tool_use  # noqa: E402


def two_tool_uses(first, second):
    return {
        "stopReason": "tool_use",
        "usage": {"inputTokens": 100, "outputTokens": 10},
        "output": {"message": {"role": "assistant", "content": [
            {"toolUse": {"toolUseId": "a", "name": first[0], "input": first[1]}},
            {"toolUse": {"toolUseId": "b", "name": second[0], "input": second[1]}},
        ]}},
    }


SCALE_ORDERS = {"deployment": "orders", "replicas": 1, "reason": "orders has 0 replicas; gateway 503s"}


def tool_results(message):
    return {b["toolResult"]["toolUseId"]: b["toolResult"] for b in message["content"]}


class ApprovalFlowTest(unittest.TestCase):
    def setUp(self):
        self.history = [{"role": "user", "content": [{"text": "why 503s?"}]}]
        self.execute = mock.patch.object(remediation, "execute", return_value={"status": "ok", "rollout_complete": True}).start()
        self.addCleanup(mock.patch.stopall)

    def test_write_tool_pauses_without_running(self):
        kira = make_agent([tool_use("scale_deployment", SCALE_ORDERS)])
        result = kira.chat(self.history)

        self.assertIsNone(result.text)
        self.assertEqual(result.pending.name, "scale_deployment")
        self.assertEqual(result.pending.input, SCALE_ORDERS)
        self.execute.assert_not_called()
        self.assertIn("toolUse", self.history[-1]["content"][0])  # waiting for the tool result

    def test_approve_runs_action_and_continues(self):
        kira = make_agent([tool_use("scale_deployment", SCALE_ORDERS), final_answer("orders is healthy again")])
        pending = kira.chat(self.history).pending

        result = kira.resume(self.history, pending, approved=True)

        self.execute.assert_called_once_with("scale_deployment", SCALE_ORDERS, None)
        self.assertEqual(result.text, "orders is healthy again")
        sent = tool_results(self.history[-2])["t1"]
        self.assertEqual(sent["content"][0]["json"]["untrusted_tool_output"]["data"]["status"], "ok")

    def test_reject_does_not_run_action(self):
        kira = make_agent([tool_use("scale_deployment", SCALE_ORDERS), final_answer("ok, not scaling")])
        pending = kira.chat(self.history).pending

        result = kira.resume(self.history, pending, approved=False)

        self.execute.assert_not_called()
        self.assertEqual(result.text, "ok, not scaling")
        data = tool_results(self.history[-2])["t1"]["content"][0]["json"]["untrusted_tool_output"]["data"]
        self.assertEqual(data["status"], "rejected")

    def test_action_off_allowlist_is_blocked_before_approval(self):
        kira = make_agent([
            tool_use("restart_deployment", {"deployment": "aiops-assistant", "reason": "x"}),
            final_answer("I can't restart myself"),
        ])
        result = kira.chat(self.history)

        self.assertIsNone(result.pending)
        self.execute.assert_not_called()
        blocked = tool_results(self.history[-2])["t1"]
        self.assertEqual(blocked["status"], "error")
        self.assertIn("not allowed", json.dumps(blocked))

    def test_read_results_from_same_turn_are_kept_until_resume(self):
        kira = make_agent([
            two_tool_uses(("fetch_service_health", {}), ("scale_deployment", SCALE_ORDERS)),
            final_answer("done"),
        ], tool_result={"status": "success"})
        pending = kira.chat(self.history).pending
        self.assertEqual(len(pending.results), 1)

        kira.resume(self.history, pending, approved=True)

        # Converse needs every toolUse of a turn answered in the next message
        self.assertEqual(set(tool_results(self.history[-2])), {"a", "b"})

    def test_only_one_write_action_per_turn(self):
        kira = make_agent([two_tool_uses(
            ("scale_deployment", SCALE_ORDERS),
            ("restart_deployment", {"deployment": "gateway", "reason": "y"}),
        )])
        pending = kira.chat(self.history).pending

        self.assertEqual(pending.tool_use_id, "a")
        second = tool_results({"content": pending.results})["b"]
        self.assertIn("one write action at a time", json.dumps(second))

    def test_string_replica_count_is_accepted(self):
        kira = make_agent([tool_use("scale_deployment", {**SCALE_ORDERS, "replicas": "2"})])
        self.assertEqual(kira.chat(self.history).pending.input["replicas"], 2)

    def test_every_step_is_logged(self):
        kira = make_agent([tool_use("scale_deployment", SCALE_ORDERS), final_answer("done")])
        with self.assertLogs("kira.actions") as logs:
            pending = kira.chat(self.history, session_id="s1").pending
            kira.resume(self.history, pending, approved=True, session_id="s1")
        events = [json.loads(line.split(":", 2)[2]) for line in logs.output]
        self.assertEqual([e["kira_action"] for e in events], ["proposed", "approved"])
        self.assertEqual(events[0]["session"], "s1")
        self.assertEqual(events[0]["reason"], SCALE_ORDERS["reason"])


def deployment(revision="3", replicas=1, available=1):
    return client.V1Deployment(
        metadata=client.V1ObjectMeta(name="orders", uid="dep-uid", generation=5,
                                     annotations={remediation.REVISION_ANNOTATION: revision}),
        spec=client.V1DeploymentSpec(
            replicas=replicas,
            selector=client.V1LabelSelector(match_labels={"app": "orders"}),
            template=pod_template("orders:v3")),
        status=client.V1DeploymentStatus(observed_generation=5, replicas=replicas,
                                         updated_replicas=replicas, available_replicas=available),
    )


def pod_template(image):
    return client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": "orders", "pod-template-hash": "abc"}),
        spec=client.V1PodSpec(containers=[client.V1Container(name="orders", image=image)]))


def replicaset(revision, image, owner="dep-uid"):
    return client.V1ReplicaSet(
        metadata=client.V1ObjectMeta(annotations={remediation.REVISION_ANNOTATION: str(revision)},
                                     owner_references=[client.V1OwnerReference(
                                         api_version="apps/v1", kind="Deployment", name="orders", uid=owner)]),
        spec=client.V1ReplicaSetSpec(selector=client.V1LabelSelector(), template=pod_template(image)))


def fake_api():
    api = mock.MagicMock()
    api.api_client = client.ApiClient()
    api.read_namespaced_deployment.return_value = deployment()
    api.read_namespaced_deployment_status.return_value = deployment()
    api.list_namespaced_replica_set.return_value = client.V1ReplicaSetList(items=[
        replicaset(1, "orders:v1"), replicaset(2, "orders:v2"), replicaset(3, "orders:v3"),
        replicaset(9, "other:v9", owner="someone-else"),
    ])
    return api


class ExecuteTest(unittest.TestCase):
    def test_scale(self):
        api = fake_api()
        result = remediation.execute("scale_deployment", SCALE_ORDERS, api=api)

        api.patch_namespaced_deployment_scale.assert_called_once_with("orders", "boutique", {"spec": {"replicas": 1}})
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["rollout_complete"])
        self.assertIn("commit", result["note"].lower())

    def test_restart_sets_restarted_at(self):
        api = fake_api()
        remediation.execute("restart_deployment", {"deployment": "gateway", "reason": "r"}, api=api)

        name, ns, body = api.patch_namespaced_deployment.call_args.args
        self.assertEqual((name, ns), ("gateway", "boutique"))
        self.assertIn(remediation.RESTARTED_AT_ANNOTATION, body["spec"]["template"]["metadata"]["annotations"])

    def test_rollback_uses_previous_owned_revision(self):
        api = fake_api()
        remediation.execute("rollback_deployment", {"deployment": "orders", "reason": "r"}, api=api)

        (patch,) = api.patch_namespaced_deployment.call_args.args[2]
        self.assertEqual((patch["op"], patch["path"]), ("replace", "/spec/template"))
        self.assertEqual(patch["value"]["spec"]["containers"][0]["image"], "orders:v2")
        self.assertNotIn("pod-template-hash", patch["value"]["metadata"]["labels"])

    def test_rollback_without_previous_revision(self):
        api = fake_api()
        api.read_namespaced_deployment.return_value = deployment(revision="1")
        result = remediation.execute("rollback_deployment", {"deployment": "orders", "reason": "r"}, api=api)

        self.assertEqual(result["status"], "error")
        api.patch_namespaced_deployment.assert_not_called()

    def test_execute_rechecks_allowlist(self):
        api = fake_api()
        result = remediation.execute("scale_deployment", {"deployment": "orders", "replicas": 40, "reason": "r"}, api=api)

        self.assertEqual(result["status"], "error")
        api.patch_namespaced_deployment_scale.assert_not_called()

    def test_reports_incomplete_rollout(self):
        api = fake_api()
        api.read_namespaced_deployment_status.return_value = deployment(available=0)
        with mock.patch.object(remediation, "ROLLOUT_TIMEOUT_SECONDS", 0):
            result = remediation.execute("scale_deployment", SCALE_ORDERS, api=api)

        self.assertEqual(result["status"], "rollout_incomplete")
        self.assertEqual(result["available_replicas"], 0)

    def test_preview_shows_change(self):
        info = remediation.preview("rollback_deployment", {"deployment": "orders"}, api=fake_api())
        self.assertEqual(info["change"], "revision 3 → 2")
        self.assertEqual(info["rollback_images"], {"orders": "orders:v2"})
        self.assertIn("self-heal", info["warning"])


if __name__ == "__main__":
    unittest.main()
