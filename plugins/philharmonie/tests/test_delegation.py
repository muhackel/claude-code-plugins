import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from test_state import FixtureMixin
from common import Error, fingerprint, write_json
import delegation
import snapshot
import transport


class DelegationCase(unittest.TestCase):
    def test_codex_catalogue_and_role_files(self):
        models = [{"slug": name, "priority": priority, "visibility": "list",
                   "supported_reasoning_levels": [{"effort": value} for value in ("medium", "high")]}
                  for priority, name in enumerate(("strong-fixture", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"))]
        result = subprocess.CompletedProcess([], 0, json.dumps({"models": models}), "")
        with tempfile.TemporaryDirectory() as directory, patch("delegation.subprocess.run", return_value=result):
            team = delegation.prepare({"target": "codex", "executable": "fixture"}, directory, "edit")
            for name, role in team["roles"].items():
                config = tomllib.loads(Path(role["config_file"]).read_text())
                self.assertEqual(config["model"], role["model"])
                self.assertIn("keine weiteren Agents", config["developer_instructions"])
            self.assertEqual(team["roles"]["philharmonie-strong"]["model"], "strong-fixture")
            advanced = team["roles"]["philharmonie-advanced"]
            self.assertEqual((advanced["model"], advanced["effort"]), ("gpt-5.6-sol", "high"))
            self.assertEqual(team["max_agents"], 3)
            schema = Path(directory) / "schema.json"
            schema.write_text('{"type":"object"}')
            argv = transport.command({"target": "codex", "executable": "fixture", "model": "strong-fixture",
                                      "effort": "high"}, Path(directory), schema, Path(directory) / "out", "edit", team)
            self.assertIn('agents.philharmonie-advanced.config_file=' + json.dumps(advanced["config_file"]), argv)
            for missing in ("gpt-5.6-luna", "gpt-5.6-sol"):
                result.stdout = json.dumps({"models": [model for model in models if model["slug"] != missing]})
                with self.subTest(missing=missing), self.assertRaisesRegex(Error, "nicht im CLI-Katalog"):
                    delegation.prepare({"target": "codex", "executable": "fixture"}, directory, "edit")

    def test_claude_agent_definitions_survive_customization_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            schema = base / "schema.json"
            schema.write_text('{"type":"object"}')
            adapter = {"target": "claude", "executable": "claude", "model": "fable", "effort": "high"}
            team = delegation.prepare(adapter, base / "agents", "edit")
            argv = transport.command(adapter, base, schema, base / "result.json", "edit", team)
            self.assertNotIn("--safe-mode", argv)
            self.assertEqual(argv[argv.index("--setting-sources") + 1], "")
            self.assertEqual(argv[argv.index("--output-format") + 1], "stream-json")
            roles = json.loads(argv[argv.index("--agents") + 1])
            self.assertEqual(roles["philharmonie-light"]["model"], "haiku")
            self.assertEqual(roles["philharmonie-standard"]["model"], "sonnet")
            self.assertEqual(roles["philharmonie-advanced"]["model"], "opus")
            self.assertEqual(roles["philharmonie-advanced"]["effort"], "high")
            self.assertEqual(roles["philharmonie-strong"]["model"], "inherit")
            self.assertNotIn("effort", roles["philharmonie-light"])
            allowed = argv[argv.index("--allowedTools") + 1].split(",")
            self.assertIn("Agent(philharmonie-light)", allowed)
            self.assertIn("Agent(philharmonie-advanced)", allowed)
            self.assertNotIn("Agent", allowed)

    def test_native_events_and_effective_models_are_distinct_from_self_reports(self):
        stream = "\n".join(json.dumps(record) for record in [
            {"type": "item.completed", "item": {"type": "agent_message", "text": "Keine Delegation"}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Agent"}]}},
            {"type": "assistant", "parent_tool_use_id": "child-1", "message": {"model": "claude-haiku-fixture"}},
            {"type": "result", "structured_output": {"answer": "Selbstbericht ohne native Beweiskraft"}}])
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(len(delegation.events(stream)), 1)
            models = delegation.observed_models(directory, stream)
            self.assertEqual(models[0]["model"], "claude-haiku-fixture")
            self.assertEqual(transport.decode({"target": "claude"}, stream, None)["answer"],
                             "Selbstbericht ohne native Beweiskraft")
            rollout = Path(directory) / "runtime/.codex/sessions/child.jsonl"
            rollout.parent.mkdir(parents=True)
            rollout.write_text(json.dumps({"type": "turn_context", "payload": {"model": "gpt-5.6-luna"}}))
            self.assertEqual(delegation.observed_models(directory, "")[0]["model"], "gpt-5.6-luna")


@unittest.skipUnless(os.environ.get("PHILHARMONIE_LIVE") == "1", "Expliziter Test nativer Agents erforderlich")
class LiveDelegationCase(FixtureMixin, unittest.TestCase):
    def test_claude_native_agents(self):
        self.native_agents("claude", ("haiku", "sonnet"))

    def test_codex_native_agents(self):
        self.native_agents("codex", ("gpt-5.6-luna", "gpt-5.6-terra"))

    def test_claude_advanced_agent(self):
        self.native_agents("claude", ("opus",), ("advanced",))

    def test_codex_advanced_agent(self):
        self.native_agents("codex", ("gpt-5.6-sol",), ("advanced",))

    def native_agents(self, target, expected, tiers=("light", "standard")):
        (self.root / "README.md").write_text("# Agenttest\n\napp.txt enthält die Eingabe für den Textvergleich.\n")
        baseline = fingerprint(self.root)
        base = self.store.local / ("native-" + target)
        work = snapshot.capture(self.root, base / "workspace", baseline)
        adapter = transport.resolve(target)
        team = delegation.prepare(adapter, base / "agents", "edit")
        schema = base / "schema.json"
        write_json(schema, {"type": "object", "required": ["answer"], "additionalProperties": False,
                            "properties": {"answer": {"type": "string"}}})
        scratch = base / "scratch"
        output = scratch / "result.json"
        argv = transport.command(adapter, work, schema, output, "edit", team)
        argv = transport.sandbox(work, scratch, argv, "edit", runtime_home=True)
        tasks = {"light": "app.txt lesen und light.txt mit dem gelesenen Inhalt schreiben.",
                 "standard": "README.md lesen und standard.txt mit einer kurzen Inhaltsangabe schreiben.",
                 "advanced": "app.txt und README.md lesen und advanced.txt mit einer gemeinsamen Inhaltsangabe schreiben."}
        assignments = {"philharmonie-" + tier: tasks[tier] for tier in tiers}
        prompt = ("Integrationstest der nativen Agent- und Modellzuordnung. Starte für jeden zugewiesenen Typ "
                  "ausdrücklich einen nativen Agent; mehrere Agents parallel, kein Kontext-Fork. Jeder Agent "
                  "bearbeitet ausschließlich seine eigene Ausgabedatei. Warte auf alle Ergebnisse. "
                  "Keine weiteren Agents, kein Git-Commit. Dieser Test verlangt die tatsächlichen Agent-Aufrufe. "
                  "Liefere danach das JSON mit Feld answer. Aufträge:\n" + json.dumps(assignments)
                  + "\nVerfügbare Definitionen:\n" + json.dumps(team))
        process = subprocess.run(argv, input=prompt, capture_output=True, text=True,
                                 env=transport.environment(), timeout=240)
        (base / "stdout.log").write_text(process.stdout)
        (base / "stderr.log").write_text(process.stderr)
        self.assertEqual(process.returncode, 0, process.stderr[-4000:] + process.stdout[-4000:])
        transport.decode(adapter, process.stdout, output)
        native = delegation.events(process.stdout)
        models = delegation.observed_models(scratch, process.stdout)
        write_json(base / "observed.json", {"events": native, "models": models})
        self.assertTrue(native, process.stdout[-6000:])
        for model in expected:
            self.assertTrue(any(model in entry["model"] for entry in models), str(models) + process.stdout[-6000:])
        for tier in tiers:
            self.assertTrue((work / f"{tier}.txt").is_file(), process.stdout[-4000:])
        self.assertEqual(fingerprint(self.root)["hash"], baseline["hash"])
