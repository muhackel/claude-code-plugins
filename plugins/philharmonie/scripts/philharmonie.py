import argparse
import json
import sys
from pathlib import Path

from common import Error, read_json
from state import Store
from runner import Runner
import activity


def parser():
    cli = argparse.ArgumentParser(description="Philharmonie: planen, umsetzen und unabhängig prüfen.")
    cli.add_argument("-C", "--directory", default=".", help="Wurzel des Git-Checkouts")
    sub = cli.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="Mission anlegen")
    new.add_argument("mission")
    new.add_argument("--goal", required=True)
    new.add_argument("--previous")
    new.add_argument("--planner", choices=["claude", "codex"],
                     help="Planer der Hauptsitzung; Standard aus CLAUDECODE abgeleitet")
    status = sub.add_parser("status", help="Projekt- oder Missionszustand lesen")
    status.add_argument("mission", nargs="?")
    status.add_argument("--full", action="store_true")
    sub.add_parser("doctor", help="CLI-Verträge und Sandbox prüfen")
    for name in ("spec", "approve", "run", "resume", "pause", "cancel", "accept", "replan",
                 "feedback", "reevaluate", "review-spec"):
        command = sub.add_parser(name)
        command.add_argument("mission")
        command.add_argument("--revision", required=True, type=int,
                             help="Revision aus dem zuletzt gelesenen status")
        if name == "spec":
            command.add_argument("--file", required=True)
            command.add_argument("--contract", required=True)
        if name == "review-spec":
            command.add_argument("--planner", choices=["claude", "codex"],
                                 help="Planer für eine Altmission ohne gespeicherte Zuordnung")
        if name in ("approve", "accept"):
            command.add_argument("--authorization", required=True,
                                 help="Vorhandene Nutzeranweisung im Wortlaut")
        if name == "approve":
            command.add_argument("--include-dirty", action="append", default=[])
        if name in ("run", "resume"):
            command.add_argument("--once", action="store_true")
        if name == "resume":
            command.add_argument("--resolution", help="Beleg für beseitigtes Hindernis")
            command.add_argument("--extra-rounds", type=int, default=0)
        if name in ("replan", "feedback"):
            command.add_argument("--reason", required=True)
    for name in ("ask", "execute"):
        command = sub.add_parser(name, help="Einzelauftrag ohne Mission")
        command.add_argument("--handover", help="Handover-Datei; sonst stdin")
        command.add_argument("--target", choices=["auto", "claude", "codex"], default="auto")
        command.add_argument("--model")
        command.add_argument("--effort", default="high")
        command.add_argument("--timeout", type=int, default=1800)
        command.add_argument("--dry-run", action="store_true")
        command.add_argument("--allow", action="append", default=[])
        command.add_argument("--include-dirty", action="append", default=[])
    return cli


def show(state, full=False):
    if not full:
        source = state
        state = {key: source[key] for key in ("mission_id", "phase", "activity", "revision", "round",
                                             "blocker", "stop_requested")}
        state["last_run"] = ({key: value for key, value in source["runs"][-1].items()
                              if key in ("id", "role", "status", "report", "error", "adapter", "model_activity")}
                             if source["runs"] else None)
        state["planner_cli"] = source.get("planner_cli")
        review = source.get("spec_review")
        state["spec_review"] = ({key: review[key] for key in
                                 ("score", "maximum", "reviewer_cli", "blockers", "questions", "report")}
                                if review else None)
        if source.get("planner_cli_inferred"):
            state["planner_cli_inferred"] = True
        actions = {"planning": "Spec entwerfen", "awaiting_spec": "Spec und Nutzerautorisierung prüfen",
                   "implementing": "run", "evaluating": "run", "awaiting_acceptance": "Review Briefing und Nutzerabnahme",
                   "completed": "Abgeschlossen", "cancelled": "Abgebrochen; bei neuem Auftrag Folgemission"}
        state["next_action"] = ("Prozess beobachten" if source["activity"] == "running" else
                                "Hindernis beheben und resume" if source["activity"] == "blocked" else
                                "Auf Fortsetzungsauftrag warten" if source["activity"] == "paused" else
                                actions[source["phase"]])
        if source["phase"] == "awaiting_spec" and source["activity"] == "idle":
            state["next_action"] = ("review-spec" if not review else "Spec-Blocker klären" if review["blockers"]
                                    else "Spec-Gegenreview und Nutzerautorisierung prüfen")
    print(json.dumps({**state, "invocation_models": activity.current()}, ensure_ascii=False, indent=2))


def main(argv=None):
    args = parser().parse_args(argv)
    with activity.Reporting() as report:
        report.exit_code = dispatch(args)
        return report.exit_code


def dispatch(args):
    try:
        if args.command in ("ask", "execute"):
            from single import single
            return single(args)
        if args.command == "doctor":
            import transport
            transport.check_sandbox()
            print(json.dumps({"sandbox": "verified", "adapters": [transport.resolve("codex"),
                               transport.resolve("claude")]}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "status" and not args.mission:
            directory = Path(args.directory).resolve() / ".philharmonie/local"
            for file in sorted(directory.glob("*/state.json")):
                show(Store(args.directory, file.parent.name).load(), args.full)
            return 0
        store = Store(args.directory, args.mission)
        runner = Runner(store)
        if args.command == "new":
            state = store.create(args.goal, args.previous, args.planner)
        elif args.command == "status":
            state = store.load()
        elif args.command == "spec":
            state = store.set_spec(Path(args.file).read_text(), read_json(args.contract), args.revision)
        elif args.command == "review-spec":
            from spec_review import review_spec
            if not store.load().get("planner_cli"):
                from state import current_cli
                print(f"Philharmonie: Planer der Altmission wird als {args.planner or current_cli()} gebunden.", file=sys.stderr)
            state = review_spec(store, args.revision, args.planner)
        elif args.command == "approve":
            state = store.approve(args.authorization, args.revision, args.include_dirty)
        elif args.command == "run":
            state = runner.run(args.revision, args.once)
        elif args.command == "resume":
            state = runner.resume(args.revision, args.resolution, args.extra_rounds)
            if state["phase"] != "cancelled":
                state = runner.run(state["revision"], args.once)
        elif args.command in ("pause", "cancel"):
            state = runner.stop(args.command, args.revision)
        elif args.command == "accept":
            state = store.accept(args.authorization, args.revision)
        elif args.command == "replan":
            state = store.replan(args.reason, args.revision)
        elif args.command == "feedback":
            state = store.feedback(args.reason, args.revision)
        elif args.command == "reevaluate":
            state = runner.reevaluate(args.revision)
        show(state, getattr(args, "full", False))
        return 0
    except (Error, OSError, ValueError) as exc:
        print(f"Philharmonie: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
