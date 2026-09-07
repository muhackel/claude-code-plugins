import json
from pathlib import Path


UNKNOWN = "unbekannt"


def _records(text):
    result = []
    for line in text.splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            result.append(item)
    if not result:
        try:
            item = json.loads(text)
        except ValueError:
            item = None
        if isinstance(item, dict):
            result.append(item)
    return result


def _plain(value):
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, list):
        parts = [_plain(item) for item in value]
        return "\n".join(item for item in parts if item)
    if isinstance(value, dict):
        for key in ("text", "content", "message", "result", "summary", "answer", "output",
                    "description", "reason"):
            text = _plain(value.get(key))
            if text:
                return text
    return ""


def _score(result):
    for key in ("Score", "score"):
        value = result.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
    scores = result.get("scores")
    if not isinstance(scores, dict):
        return None
    points = []
    for value in scores.values():
        if isinstance(value, dict):
            value = value.get("points")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None
        points.append(value)
    return sum(points) if points else None


def _outcome(result, status):
    if not isinstance(result, dict):
        return "Kein Abschlussbeleg vorhanden."
    parts = []
    summary = _plain(result.get("summary"))
    answer = _plain(result.get("answer"))
    verdict = _plain(result.get("verdict"))
    if verdict:
        parts.append("Urteil: " + verdict)
    score = _score(result)
    if score is not None:
        parts.append(f"Score: {score:g}/100")
    blockers = result.get("blockers")
    if isinstance(blockers, list) and blockers:
        texts = [_plain(item) for item in blockers]
        texts = [text for text in texts if text]
        if texts:
            parts.append("Blocker: " + "; ".join(texts))
    if summary:
        parts.append(summary)
    elif answer:
        parts.append(answer)
    elif status == "failed":
        parts.append("Aufruf fehlgeschlagen.")
    return " | ".join(parts) if parts else "Kein Abschlussbeleg vorhanden."


def _configured_roles(scratch):
    path = Path(scratch).parent / "agents/delegation.json"
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    roles = value.get("roles") if isinstance(value, dict) else None
    return roles if isinstance(roles, dict) else {}


def _model(models, configured=None, inherited=None):
    observed = {value for value in models if isinstance(value, str) and value.strip()}
    if len(observed) == 1:
        return observed.pop(), "observed"
    if isinstance(configured, str) and configured and configured != "inherit":
        return configured, "configured"
    if configured == "inherit" and isinstance(inherited, str) and inherited != UNKNOWN:
        return inherited, "configured"
    return UNKNOWN, "unknown"


def _participant(agent_id, role, task, model, evidence, outcome, status, source,
                 task_summary=None):
    result = {"agent_id": str(agent_id), "role": role or UNKNOWN, "task": task or UNKNOWN,
              "model": model, "model_evidence": evidence, "outcome": outcome,
              "status": status, "source": source}
    if isinstance(task_summary, str) and task_summary.strip():
        result["task_summary"] = task_summary.strip()
    return result


def _claude_model_usage(records):
    models = set()
    for record in records:
        if record.get("parent_tool_use_id"):
            continue
        usage = record.get("modelUsage")
        if not isinstance(usage, dict):
            continue
        for key, value in usage.items():
            if isinstance(key, str) and key:
                models.add(key)
            elif isinstance(value, dict) and isinstance(value.get("model"), str):
                models.add(value["model"])
    return models


def _claude(adapter, scratch, records, task, role, result, status):
    main_models = []
    session_ids = []
    calls = []
    for record in records:
        if isinstance(record.get("session_id"), str) and not record.get("parent_tool_use_id"):
            session_ids.append(record["session_id"])
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        if not record.get("parent_tool_use_id") and isinstance(message.get("model"), str):
            main_models.append(message["model"])
        if record.get("parent_tool_use_id"):
            continue
        for block in message.get("content", []):
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") not in ("Agent", "Task"):
                continue
            inputs = block.get("input") if isinstance(block.get("input"), dict) else {}
            calls.append({"id": block.get("id") or f"claude-agent-{len(calls) + 1}",
                          "role": inputs.get("subagent_type") or inputs.get("agent") or "subagent",
                          "task": inputs.get("prompt") or inputs.get("description") or UNKNOWN,
                          "task_summary": inputs.get("description"),
                          "models": [], "reports": [], "tool_results": [], "error": False})
    if not main_models:
        usage = _claude_model_usage(records)
        if len(usage) == 1:
            main_models.extend(usage)
    main_model, main_evidence = _model(main_models, adapter.get("model"))
    main_source = "claude-stream" if main_evidence == "observed" else "adapter"
    main_id = session_ids[-1] if session_ids else "main"
    participants = [_participant(main_id, role, task, main_model, main_evidence,
                                 _outcome(result, status), status, main_source)]
    by_id = {call["id"]: call for call in calls}
    for record in records:
        parent = record.get("parent_tool_use_id")
        if parent in by_id:
            message = record.get("message")
            if isinstance(message, dict):
                if isinstance(message.get("model"), str):
                    by_id[parent]["models"].append(message["model"])
                if message.get("role") in (None, "assistant"):
                    text = _plain(message.get("content"))
                    if text:
                        by_id[parent]["reports"].append(text)
            if record.get("type") == "result":
                text = _plain(record.get("result") or record.get("structured_output"))
                if text:
                    by_id[parent]["tool_results"].append(text)
                by_id[parent]["error"] = bool(record.get("is_error"))
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        for block in message.get("content", []):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            target = by_id.get(block.get("tool_use_id"))
            if not target:
                continue
            text = _plain(block.get("content"))
            if text:
                target["tool_results"].append(text)
            target["error"] = target["error"] or bool(block.get("is_error"))
    configured = _configured_roles(scratch)
    for call in calls:
        role_config = configured.get(call["role"], {})
        configured_model = role_config.get("model") if isinstance(role_config, dict) else None
        model, evidence = _model(call["models"], configured_model, main_model)
        reports = call["tool_results"] or call["reports"]
        outcome = ("Nativer Selbstbericht: " + reports[-1] if reports else
                   "Kein Abschlussbeleg des nativen Subagents vorhanden.")
        child_status = "failed" if call["error"] else "completed" if call["tool_results"] else "unknown"
        participants.append(_participant(call["id"], call["role"], call["task"], model,
                                         evidence, outcome, child_status, "claude-agent",
                                         call["task_summary"]))
    return participants


def _arguments(value):
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    try:
        result = json.loads(value)
    except ValueError:
        return {}
    return result if isinstance(result, dict) else {}


def _collab_items(records):
    for record in records:
        item = record.get("item")
        if not isinstance(item, dict):
            item = record.get("payload")
        if isinstance(item, dict) and item.get("type") == "collab_tool_call":
            yield item


def _thread_ids(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _agent_states(value):
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            thread_id = item.get("thread_id") or item.get("agent_id") or item.get("id")
            if isinstance(thread_id, str):
                yield thread_id, item
    elif isinstance(value, dict):
        for thread_id, item in value.items():
            if isinstance(item, dict):
                yield thread_id, item
            else:
                yield thread_id, {"status": item}


def _rollouts(scratch):
    sessions = Path(scratch) / "runtime/.codex/sessions"
    result = {}
    if not sessions.is_dir():
        return result
    for path in sorted(sessions.rglob("*.jsonl")):
        meta = None
        models = []
        reports = []
        spawns = []
        new_tasks = []
        calls = {}
        completed = False
        failed = False
        for record in _records(path.read_text(errors="replace")):
            payload = record.get("payload")
            if record.get("type") == "session_meta" and isinstance(payload, dict):
                meta = payload
            elif record.get("type") == "turn_context" and isinstance(payload, dict):
                if isinstance(payload.get("model"), str):
                    models.append(payload["model"])
            elif record.get("type") == "response_item" and isinstance(payload, dict):
                if payload.get("type") in ("message", "agent_message") and payload.get("role") == "assistant":
                    text = _plain(payload.get("content"))
                    if text:
                        reports.append(text)
                elif payload.get("type") == "agent_message":
                    text = _plain(payload.get("content"))
                    marker = "Message Type: NEW_TASK"
                    separator = "Payload:\n"
                    if marker in text and separator in text:
                        task_text = text.split(separator, 1)[1].strip()
                        if task_text:
                            new_tasks.append({"recipient": payload.get("recipient"),
                                              "task": task_text})
                elif (payload.get("type") == "function_call"
                      and payload.get("namespace") == "collaboration"
                      and payload.get("name") == "spawn_agent"):
                    args = _arguments(payload.get("arguments"))
                    message = args.get("message")
                    if (not isinstance(message, str) or
                            (message.startswith("gAAAA") and len(message) > 100 and not message.isspace())):
                        message = None
                    call = {"call_id": payload.get("call_id"),
                            "role": args.get("agent_type") or args.get("role") or "subagent",
                            "task": message, "task_summary": args.get("description"),
                            "task_name": args.get("task_name"), "agent_path": None}
                    spawns.append(call)
                    if isinstance(call["call_id"], str):
                        calls[call["call_id"]] = call
                elif payload.get("type") == "function_call_output" and payload.get("call_id") in calls:
                    output = _arguments(payload.get("output"))
                    agent_path = output.get("task_name") or output.get("agent_path")
                    if isinstance(agent_path, str):
                        calls[payload["call_id"]]["agent_path"] = agent_path
            elif record.get("type") == "event_msg" and isinstance(payload, dict):
                completed = completed or payload.get("type") == "task_complete"
                failed = failed or payload.get("type") in ("turn_aborted", "task_failed")
        if not isinstance(meta, dict):
            continue
        thread_id = meta.get("id") or meta.get("session_id")
        if isinstance(thread_id, str):
            result[thread_id] = {"meta": meta, "models": models, "reports": reports,
                                 "spawns": spawns, "new_tasks": new_tasks,
                                 "completed": completed, "failed": failed,
                                 "source": str(path.relative_to(scratch))}
    return result


def _spawn_source(meta):
    source = meta.get("source")
    if not isinstance(source, dict):
        source = meta.get("thread_source")
    if not isinstance(source, dict):
        return {}
    subagent = source.get("subagent")
    if not isinstance(subagent, dict):
        return {}
    spawn = subagent.get("thread_spawn")
    return spawn if isinstance(spawn, dict) else {}


def _normalize_status(value):
    if isinstance(value, dict):
        value = value.get("status") or value.get("state")
    if not isinstance(value, str):
        return "unknown"
    lowered = value.lower()
    if lowered in ("completed", "succeeded", "success", "done"):
        return "completed"
    if lowered in ("failed", "error", "errored"):
        return "failed"
    return lowered


def _codex(adapter, scratch, records, task, role, result, status):
    main_ids = []
    for record in records:
        if record.get("type") in ("thread.started", "thread_started"):
            thread_id = record.get("thread_id") or record.get("id")
            if isinstance(thread_id, str):
                main_ids.append(thread_id)
    rollouts = _rollouts(scratch)
    main_id = main_ids[-1] if main_ids else None
    if main_id is None:
        roots = [thread_id for thread_id, data in rollouts.items()
                 if not data["meta"].get("parent_thread_id") and not _spawn_source(data["meta"])]
        if len(roots) == 1:
            main_id = roots[0]
    main_data = rollouts.get(main_id, {})
    main_model, main_evidence = _model(main_data.get("models", []), adapter.get("model"))
    participants = [_participant(main_id or "main", role, task, main_model, main_evidence,
                                 _outcome(result, status), status,
                                 main_data.get("source", "adapter") if main_evidence == "observed" else "adapter")]
    spawns = {}
    order = []
    states = {}
    for item in _collab_items(records):
        tool = item.get("tool") or item.get("name")
        args = _arguments(item.get("arguments") or item.get("input"))
        receivers = _thread_ids(item.get("receiver_thread_ids") or item.get("receiver_thread_id"))
        if tool in ("spawn_agent", "spawn"):
            call_id = item.get("id") or item.get("call_id") or f"codex-spawn-{len(spawns) + 1}"
            spawn = spawns.setdefault(call_id, {"role": "subagent", "task": UNKNOWN,
                                                "task_summary": None, "receivers": []})
            spawn["role"] = (args.get("agent_type") or args.get("role") or args.get("task_name")
                             or item.get("agent_type") or spawn["role"])
            spawn["task"] = (args.get("message") or args.get("prompt") or args.get("task")
                             or item.get("prompt") or spawn["task"])
            description = args.get("description") or item.get("description")
            if isinstance(description, str) and description.strip():
                spawn["task_summary"] = description.strip()
            for thread_id in receivers:
                if thread_id not in spawn["receivers"]:
                    spawn["receivers"].append(thread_id)
                    order.append((call_id, thread_id))
        if tool in ("wait", "send_input", "send_message"):
            for thread_id, state in _agent_states(item.get("agents_states")):
                states[thread_id] = state
    configured = _configured_roles(scratch)
    seen = set()
    for call_id, thread_id in order:
        if thread_id in seen:
            continue
        seen.add(thread_id)
        spawn = spawns[call_id]
        data = rollouts.get(thread_id, {})
        meta = data.get("meta", {})
        link = _spawn_source(meta)
        parent = meta.get("parent_thread_id") or link.get("parent_thread_id")
        if main_id and data and parent is not None and parent != main_id:
            continue
        agent_role = link.get("agent_role") or spawn["role"]
        role_config = configured.get(agent_role, {})
        configured_model = role_config.get("model") if isinstance(role_config, dict) else None
        model, evidence = _model(data.get("models", []), configured_model, main_model)
        state = states.get(thread_id, {})
        child_status = _normalize_status(state)
        if child_status == "unknown":
            child_status = "failed" if data.get("failed") else "completed" if data.get("completed") else "unknown"
        report = _plain(state.get("message") or state.get("result") or state.get("output"))
        if not report and data.get("reports"):
            report = data["reports"][-1]
        outcome = ("Nativer Selbstbericht: " + report if report else
                   "Kein Abschlussbeleg des nativen Subagents vorhanden.")
        participants.append(_participant(thread_id, agent_role, spawn["task"], model, evidence,
                                         outcome, child_status, data.get("source", "codex-json"),
                                         spawn["task_summary"]))
    spawn_paths = {}
    for spawn in main_data.get("spawns", []):
        path = spawn.get("agent_path")
        if isinstance(path, str):
            spawn_paths[path] = spawn
    native_children = []
    for thread_id, data in rollouts.items():
        if thread_id in seen:
            continue
        link = _spawn_source(data.get("meta", {}))
        if main_id and link.get("parent_thread_id") == main_id:
            native_children.append((thread_id, data, link))
    for thread_id, data, link in sorted(native_children, key=lambda item: item[0]):
        agent_path = link.get("agent_path")
        spawn = spawn_paths.get(agent_path, {})
        agent_role = link.get("agent_role") or spawn.get("role") or "subagent"
        role_config = configured.get(agent_role, {})
        configured_model = role_config.get("model") if isinstance(role_config, dict) else None
        model, evidence = _model(data.get("models", []), configured_model, main_model)
        child_status = "failed" if data.get("failed") else "completed" if data.get("completed") else "unknown"
        report = data.get("reports", [])[-1] if data.get("reports") else ""
        outcome = ("Nativer Selbstbericht: " + report if report else
                   "Kein Abschlussbeleg des nativen Subagents vorhanden.")
        child_task = spawn.get("task")
        if not child_task:
            native_tasks = [item["task"] for item in data.get("new_tasks", [])
                            if item.get("recipient") == agent_path]
            if len(native_tasks) == 1:
                child_task = native_tasks[0]
        if not child_task:
            name = agent_path or thread_id
            child_task = f"Native Teilaufgabe {name}; Aufgabentext im Rollout nicht lesbar."
        participants.append(_participant(thread_id, agent_role, child_task, model, evidence,
                                         outcome, child_status, data["source"],
                                         spawn.get("task_summary")))
    return participants


def collect(adapter, scratch, stdout, task, role, result=None, status="completed"):
    """Return the main CLI and every provably started native subagent."""
    records = _records(stdout)
    if adapter.get("target") == "claude":
        return _claude(adapter, scratch, records, task, role, result, status)
    return _codex(adapter, scratch, records, task, role, result, status)
