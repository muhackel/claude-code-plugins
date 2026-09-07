import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import participants


def lines(*records):
    return "\n".join(json.dumps(record) for record in records)


class ParticipantsCase(unittest.TestCase):
    def test_claude_main_and_started_agent_are_linked_by_tool_id(self):
        stdout = lines(
            {"type": "assistant", "session_id": "claude-main", "message": {
                "role": "assistant", "model": "claude-opus-observed", "content": [{
                    "type": "tool_use", "id": "tool-agent-1", "name": "Agent", "input": {
                        "subagent_type": "philharmonie-light", "description": "Dateien vergleichen",
                        "prompt": "Vergleiche a.txt mit b.txt."}}]}},
            {"type": "assistant", "parent_tool_use_id": "tool-agent-1", "message": {
                "role": "assistant", "model": "claude-haiku-observed",
                "content": [{"type": "text", "text": "Beide Dateien sind gleich."}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result",
                "tool_use_id": "tool-agent-1", "content": "Vergleich abgeschlossen.", "is_error": False}]}},
            {"type": "result", "modelUsage": {"anderes-aggregiertes-modell": {"inputTokens": 1}},
             "structured_output": {"answer": "Fertig"}})
        with tempfile.TemporaryDirectory() as directory:
            result = participants.collect({"target": "claude", "model": "fable"}, directory,
                                          stdout, "Gesamtauftrag", "execute", {"answer": "Fertig"})
        self.assertEqual(result[0], {"agent_id": "claude-main", "role": "execute",
            "task": "Gesamtauftrag", "model": "claude-opus-observed",
            "model_evidence": "observed", "outcome": "Fertig", "status": "completed",
            "source": "claude-stream"})
        self.assertEqual(result[1]["agent_id"], "tool-agent-1")
        self.assertEqual(result[1]["role"], "philharmonie-light")
        self.assertEqual(result[1]["task"], "Vergleiche a.txt mit b.txt.")
        self.assertEqual(result[1]["task_summary"], "Dateien vergleichen")
        self.assertEqual(result[1]["model"], "claude-haiku-observed")
        self.assertEqual(result[1]["outcome"], "Nativer Selbstbericht: Vergleich abgeschlossen.")
        self.assertEqual(result[1]["status"], "completed")

    def test_claude_configured_fallback_error_and_missing_completion(self):
        stdout = lines(
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "bad",
                "name": "Task", "input": {"subagent_type": "philharmonie-standard",
                                             "description": "Prüfung"}},
                {"type": "tool_use", "id": "open", "name": "Agent",
                 "input": {"subagent_type": "unbekannte-rolle", "prompt": "Noch offen"}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "bad",
                "content": [{"type": "text", "text": "Werkzeugfehler"}], "is_error": True}]}})
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            agents = base / "agents"
            agents.mkdir()
            (agents / "delegation.json").write_text(json.dumps({"roles": {
                "philharmonie-standard": {"model": "sonnet-configured"}}}))
            rows = participants.collect({"target": "claude", "model": "fable"}, base / "scratch",
                stdout, "Frage", "ask", {"summary": "Fehler: Exit 1"}, "failed")
        self.assertEqual(rows[0]["model_evidence"], "configured")
        self.assertEqual(rows[0]["status"], "failed")
        self.assertEqual(rows[0]["outcome"], "Fehler: Exit 1")
        self.assertEqual((rows[1]["model"], rows[1]["model_evidence"], rows[1]["status"]),
                         ("sonnet-configured", "configured", "failed"))
        self.assertEqual((rows[2]["model"], rows[2]["model_evidence"], rows[2]["status"]),
                         ("unbekannt", "unknown", "unknown"))
        self.assertNotIn("task_summary", rows[2])
        self.assertIn("Kein Abschlussbeleg", rows[2]["outcome"])

    def test_claude_single_model_usage_is_observed_but_ambiguous_usage_is_not(self):
        with tempfile.TemporaryDirectory() as directory:
            one = participants.collect({"target": "claude", "model": "fable"}, directory,
                json.dumps({"type": "result", "modelUsage": {"claude-sonnet": {}}}),
                "Aufgabe", "ask", {"answer": "Antwort"})
            many = participants.collect({"target": "claude", "model": "fable"}, directory,
                json.dumps({"type": "result", "modelUsage": {"claude-sonnet": {}, "claude-haiku": {}}}),
                "Aufgabe", "ask", {"answer": "Antwort"})
            child_only = participants.collect({"target": "claude", "model": "fable"}, directory,
                json.dumps({"type": "result", "parent_tool_use_id": "agent-1",
                            "modelUsage": {"claude-haiku": {}}}),
                "Aufgabe", "ask", {"answer": "Antwort"})
        self.assertEqual((one[0]["model"], one[0]["model_evidence"]), ("claude-sonnet", "observed"))
        self.assertEqual((many[0]["model"], many[0]["model_evidence"]), ("fable", "configured"))
        self.assertEqual((child_only[0]["model"], child_only[0]["model_evidence"]),
                         ("fable", "configured"))

    def test_codex_uses_explicit_receiver_and_rollout_parent_links(self):
        stdout = lines(
            {"type": "thread.started", "thread_id": "root-thread"},
            {"type": "item.started", "item": {"id": "spawn-1", "type": "collab_tool_call",
                "tool": "spawn_agent", "arguments": {"agent_type": "philharmonie-light",
                "message": "Suche die Fundstelle.", "description": "Fundstelle suchen"}}},
            {"type": "item.completed", "item": {"id": "spawn-1", "type": "collab_tool_call",
                "tool": "spawn_agent", "receiver_thread_ids": ["child-thread"]}},
            {"type": "item.completed", "item": {"id": "wait-1", "type": "collab_tool_call",
                "tool": "wait", "agents_states": [{"thread_id": "child-thread", "status": "completed",
                                                       "message": "Fundstelle 42 geprüft."}]}})
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            sessions = base / "scratch/runtime/.codex/sessions/2026/01/01"
            sessions.mkdir(parents=True)
            (base / "agents").mkdir()
            (base / "agents/delegation.json").write_text(json.dumps({"roles": {
                "philharmonie-light": {"model": "configured-child"},
                "nur-konfiguriert": {"model": "darf-nicht-erscheinen"}}}))
            self._rollout(sessions / "root.jsonl", "root-thread", None, "gpt-root")
            self._rollout(sessions / "child.jsonl", "child-thread", "root-thread", "gpt-child",
                          role="philharmonie-light", report="Eigener Schlussbericht")
            self._rollout(sessions / "foreign.jsonl", "foreign-thread", "other-root", "gpt-foreign",
                          role="philharmonie-standard")
            rows = participants.collect({"target": "codex", "model": "configured-root"}, base / "scratch",
                stdout, "Gesamtauftrag", "generator", {"summary": "Geändert", "verdict": "PASS"})
        self.assertEqual([row["agent_id"] for row in rows], ["root-thread", "child-thread"])
        self.assertEqual((rows[0]["model"], rows[0]["model_evidence"]), ("gpt-root", "observed"))
        self.assertEqual(rows[0]["outcome"], "Urteil: PASS | Geändert")
        self.assertEqual(rows[1]["task"], "Suche die Fundstelle.")
        self.assertEqual(rows[1]["task_summary"], "Fundstelle suchen")
        self.assertEqual((rows[1]["model"], rows[1]["model_evidence"]), ("gpt-child", "observed"))
        self.assertEqual(rows[1]["outcome"], "Nativer Selbstbericht: Fundstelle 42 geprüft.")
        self.assertTrue(rows[1]["source"].endswith("child.jsonl"))

    def test_codex_does_not_invent_order_mapping_or_count_failed_spawn(self):
        stdout = lines(
            {"type": "thread.started", "thread_id": "root"},
            {"type": "item.completed", "item": {"id": "failed-spawn", "type": "collab_tool_call",
                "tool": "spawn_agent", "arguments": {"agent_type": "philharmonie-light",
                "message": "Nicht gestartet"}, "status": "failed"}},
            {"type": "item.completed", "item": {"id": "spawn", "type": "collab_tool_call",
                "tool": "spawn_agent", "arguments": "{\"agent_type\":\"philharmonie-standard\","
                "\"message\":\"Prüfen\"}", "receiver_thread_ids": ["declared-child"]}})
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            sessions = base / "scratch/runtime/.codex/sessions"
            sessions.mkdir(parents=True)
            self._rollout(sessions / "wrong.jsonl", "declared-child", "other", "wrong-model",
                          role="philharmonie-standard")
            self._rollout(sessions / "unrelated.jsonl", "another-child", "other-root", "other-model",
                          role="philharmonie-light")
            rows = participants.collect({"target": "codex", "model": "configured-root"}, base / "scratch",
                stdout, "Auftrag", "generator", None, "failed")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["agent_id"], "root")
        self.assertEqual(rows[0]["model_evidence"], "configured")
        self.assertEqual(rows[0]["outcome"], "Kein Abschlussbeleg vorhanden.")

    def test_codex_receiver_without_rollout_is_kept_with_honest_unknowns(self):
        stdout = lines(
            {"type": "thread.started", "thread_id": "root"},
            {"type": "item.completed", "item": {"id": "spawn", "type": "collab_tool_call",
                "tool": "spawn_agent", "arguments": {"message": "Teilauftrag"},
                "receiver_thread_ids": ["child-without-rollout"]}})
        with tempfile.TemporaryDirectory() as directory:
            rows = participants.collect({"target": "codex", "model": "configured-root"}, directory,
                stdout, "Auftrag", "generator", {"summary": "Hauptlauf fertig"})
        self.assertEqual([row["agent_id"] for row in rows], ["root", "child-without-rollout"])
        self.assertEqual((rows[1]["model"], rows[1]["model_evidence"], rows[1]["status"]),
                         ("unbekannt", "unknown", "unknown"))
        self.assertNotIn("task_summary", rows[1])
        self.assertIn("Kein Abschlussbeleg", rows[1]["outcome"])

    def test_codex_rollout_thread_spawn_is_native_start_evidence(self):
        stdout = lines(
            {"type": "thread.started", "thread_id": "root-live"},
            {"type": "item.completed", "item": {"id": "wait", "type": "collab_tool_call",
                "tool": "wait", "receiver_thread_ids": [], "agents_states": {},
                "status": "completed"}})
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            sessions = base / "scratch/runtime/.codex/sessions"
            sessions.mkdir(parents=True)
            self._rollout(sessions / "root.jsonl", "root-live", None, "gpt-astra",
                          spawn={"call_id": "spawn-call", "task_name": "copy_check",
                                 "role": "philharmonie-advanced",
                                 "message": "gAAAA" + "x" * 200})
            self._rollout(sessions / "child.jsonl", "child-live", "root-live", "gpt-sol",
                          role="philharmonie-advanced", report="checked.txt wurde geprüft",
                          agent_path="/root/copy_check")
            rows = participants.collect({"target": "codex", "model": "configured-root"},
                base / "scratch", stdout, "checked.txt durch Agent prüfen", "execute",
                {"answer": "Erfolgreich"})
        self.assertEqual([row["agent_id"] for row in rows], ["root-live", "child-live"])
        self.assertEqual([(row["model"], row["model_evidence"]) for row in rows],
                         [("gpt-astra", "observed"), ("gpt-sol", "observed")])
        self.assertEqual(rows[1]["role"], "philharmonie-advanced")
        self.assertEqual(rows[1]["status"], "completed")
        self.assertIn("Aufgabentext im Rollout nicht lesbar", rows[1]["task"])
        self.assertNotIn("gAAAA", rows[1]["task"])
        self.assertIn("checked.txt", rows[1]["outcome"])

    def test_codex_uses_only_exact_readable_native_new_task(self):
        stdout = json.dumps({"type": "thread.started", "thread_id": "root"})
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            sessions = base / "scratch/runtime/.codex/sessions"
            sessions.mkdir(parents=True)
            self._rollout(sessions / "root.jsonl", "root", None, "gpt-root")
            self._rollout(sessions / "child.jsonl", "child", "root", "gpt-child",
                          role="philharmonie-light", agent_path="/root/check",
                          new_task="Lies checked.txt und prüfe den Inhalt.")
            rows = participants.collect({"target": "codex", "model": "configured"},
                base / "scratch", stdout, "Hauptauftrag", "execute", {"answer": "Fertig"})
        self.assertEqual(rows[1]["task"], "Lies checked.txt und prüfe den Inhalt.")

    def test_score_and_blockers_are_part_of_main_outcome(self):
        result = {"summary": "Spec geprüft", "scores": {
            "coverage": {"points": 20}, "verification": {"points": 21},
            "scope": {"points": 17}, "evidence": {"points": 12}, "risks": {"points": 10}},
            "blockers": [{"id": "B-1", "description": "Entscheidung fehlt"}]}
        with tempfile.TemporaryDirectory() as directory:
            row = participants.collect({"target": "codex", "model": "gpt-config"}, directory,
                                       "", "Review", "spec_reviewer", result)[0]
        self.assertEqual(row["outcome"], "Score: 80/100 | Blocker: Entscheidung fehlt | Spec geprüft")

    def test_ambiguous_root_rollouts_do_not_become_children(self):
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            sessions = scratch / "runtime/.codex/sessions"
            sessions.mkdir(parents=True)
            self._rollout(sessions / "one.jsonl", "one", None, "model-one")
            self._rollout(sessions / "two.jsonl", "two", None, "model-two")
            rows = participants.collect({"target": "codex", "model": "configured"},
                                        scratch, "", "Auftrag", "execute", status="failed")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["model_evidence"], "configured")

    @staticmethod
    def _rollout(path, thread_id, parent, model, role=None, report=None, spawn=None,
                 agent_path="/root/test", new_task=None):
        source = "cli" if parent is None else {"subagent": {"thread_spawn": {
            "parent_thread_id": parent, "depth": 1, "agent_path": agent_path,
            "agent_role": role}}}
        records = [
            {"type": "session_meta", "payload": {"id": thread_id,
                "parent_thread_id": parent, "source": source}},
            {"type": "turn_context", "payload": {"model": model}}]
        if spawn:
            arguments = {"task_name": spawn["task_name"], "agent_type": spawn["role"],
                         "message": spawn["message"]}
            records.extend([
                {"type": "response_item", "payload": {"type": "function_call",
                    "name": "spawn_agent", "namespace": "collaboration",
                    "arguments": json.dumps(arguments), "call_id": spawn["call_id"]}},
                {"type": "response_item", "payload": {"type": "function_call_output",
                    "call_id": spawn["call_id"],
                    "output": json.dumps({"task_name": "/root/" + spawn["task_name"]})}}])
        if new_task:
            records.append({"type": "response_item", "payload": {"type": "agent_message",
                "author": "/root", "recipient": agent_path, "content": [{"type": "input_text",
                    "text": "Message Type: NEW_TASK\nTask name: " + agent_path
                            + "\nSender: /root\nPayload:\n" + new_task}]}})
        if report:
            records.append({"type": "response_item", "payload": {"type": "message",
                "role": "assistant", "content": [{"type": "output_text", "text": report}]}})
        records.append({"type": "event_msg", "payload": {"type": "task_complete"}})
        path.write_text(lines(*records))


if __name__ == "__main__":
    unittest.main()
