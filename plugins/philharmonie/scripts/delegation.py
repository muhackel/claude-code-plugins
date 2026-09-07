import json
from pathlib import Path
import subprocess

from common import Error, atomic, write_json

PACKAGE = Path(__file__).resolve().parents[1]
DESCRIPTIONS = {
    "light": "Begrenzte Suche, Textvergleich und einfache Aufgaben mit eindeutigen Kriterien.",
    "standard": "Einzelne Module, Tests und lokale Fehleranalyse.",
    "advanced": "Änderungen über mehrere Module, schwierige Fehleranalyse, Refactoring und Integration.",
    "strong": "Architekturentscheidungen, widersprüchliche Anforderungen und hohes Fehlerrisiko.",
}


def prepare(adapter, directory, profile):
    directory = Path(directory)
    policy = (PACKAGE / "references/delegation.md").read_text()
    models = {"light": "haiku", "standard": "sonnet", "advanced": "opus", "strong": "inherit"}
    if adapter["target"] == "codex":
        process = subprocess.run([adapter["executable"], "debug", "models", "--bundled"],
                                 capture_output=True, text=True, timeout=15)
        if process.returncode:
            raise Error("Modellkatalog für Subagents nicht verfügbar.")
        try:
            catalog = json.loads(process.stdout)["models"]
            visible = {m["slug"]: m for m in catalog if m.get("visibility") == "list"}
            strongest = min(visible.values(), key=lambda m: m["priority"])["slug"]
        except (ValueError, KeyError, TypeError) as exc:
            raise Error("Ungültiger Modellkatalog für Subagents.") from exc
        models = {"light": "gpt-5.6-luna", "standard": "gpt-5.6-terra",
                  "advanced": "gpt-5.6-sol", "strong": strongest}
        for tier, model in models.items():
            effort = "medium" if tier == "light" else "high"
            if model not in visible or effort not in {item["effort"] for item in visible[model]["supported_reasoning_levels"]}:
                raise Error(f"Subagent-Modell oder Effort nicht im CLI-Katalog: {model}/{effort}")
    roles = {}
    for tier, model in models.items():
        name = "philharmonie-" + tier
        instructions = (DESCRIPTIONS[tier] + "\n" + policy +
                        "\nDu bist ein Subagent. Bearbeite nur deinen abgegrenzten Auftrag. "
                        "Starte selbst keine weiteren Agents. Keine Änderungen an Git- oder Missionsmetadaten.")
        if profile != "edit":
            instructions += "\nNur recherchieren und Quellen belegen; keine Projektdateien ändern."
        roles[name] = {"description": DESCRIPTIONS[tier], "model": model,
                       "effort": "medium" if tier == "light" else "high", "prompt": instructions}
        if adapter["target"] == "codex":
            config = directory / f"{name}.toml"
            atomic(config, f'model = {json.dumps(model)}\n'
                   f'model_reasoning_effort = {json.dumps(roles[name]["effort"])}\n'
                   f'developer_instructions = {json.dumps(instructions, ensure_ascii=False)}\n')
            roles[name]["config_file"] = str(config)
        else:
            roles[name]["tools"] = ["Read", "Glob", "Grep", "Bash"] + (["Edit", "Write"] if profile == "edit" else [])
            roles[name]["maxTurns"] = 20
            roles[name]["permissionMode"] = "dontAsk"
            if tier == "light":
                roles[name].pop("effort")
    result = {"target": adapter["target"], "max_agents": 3, "profile": profile, "roles": roles}
    write_json(directory / "delegation.json", result)
    return result


def events(stdout):
    result = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        item = event.get("item", {})
        if isinstance(item, dict) and item.get("type") == "collab_tool_call":
            result.append(event)
        message = event.get("message", {})
        if isinstance(message, dict):
            for block in message.get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") in ("Agent", "Task"):
                    result.append(event)
                    break
    return result


def observed_models(scratch, stdout):
    result = []
    for path in (Path(scratch) / "runtime/.codex/sessions").rglob("*.jsonl"):
        for line in path.read_text(errors="replace").splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict) and item.get("type") == "turn_context" and item.get("payload", {}).get("model"):
                result.append({"source": str(path.relative_to(scratch)),
                               "model": item["payload"]["model"], "timestamp": item.get("timestamp")})
    for line in stdout.splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict) and item.get("parent_tool_use_id") and item.get("message", {}).get("model"):
            result.append({"source": "claude-subagent-message", "agent_call": item["parent_tool_use_id"],
                           "model": item["message"]["model"]})
    return result
