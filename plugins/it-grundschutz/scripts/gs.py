#!/usr/bin/env python3
"""Lookup-CLI fuer den lokalen Grundschutz-OSCAL-Korpus.

Zwei Ebenen (gleiche ID GC.1.1): 'anwender' = konkrete Anforderung,
'methodik' = Vorgehensweise/das Warum dahinter.

Kommandos:
  status            Korpus-Status (Ebenen, Anzahl Anforderungen)
  groups            Schichten/Gruppen-Baum (Anwenderkatalog)
  list <GRUPPE>     Anforderungen einer Schicht/Gruppe (z.B. GC, GC.1)
  get <ID>          Anforderung volltext, zitierfaehig — inkl. Methodik-Ebene, falls vorhanden
  search <BEGRIFF>  Volltextsuche in Titel/statement/guidance (Anwenderkatalog)
  prozess           Vorgehensweise als Schrittfolge (Methodik-Ebene, GC->STM->UMS->PERF->VRB)
  json <ID>         rohes OSCAL-Control (fuer crosswalk/debug)
"""
import json
import os
import re
import sys

PARAM_RE = re.compile(r"\{\{\s*insert:\s*param,\s*([^}\s,]+)\s*\}\}")

CORPUS = os.environ.get("GS_CORPUS_DIR", os.path.expanduser("~/.local/share/it-grundschutz/corpus"))
PP = os.path.join(CORPUS, "grundschutz-pp")
CATALOG = os.path.join(PP, "catalog.json")           # Anwenderkatalog
METHODIK = os.path.join(PP, "methodik-catalog.json")  # Methodik-Quellkatalog
MANIFEST = os.path.join(PP, "manifest.json")


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def load_catalog():
    if not os.path.exists(CATALOG):
        die(f"Kein Korpus unter {CATALOG}.\nErst laden:  nix run .#ingest")
    with open(CATALOG, encoding="utf-8") as f:
        return json.load(f)["catalog"]


def load_methodik():
    if not os.path.exists(METHODIK):
        return None
    try:
        with open(METHODIK, encoding="utf-8") as f:
            return json.load(f)["catalog"]
    except Exception:
        return None


def manifest():
    try:
        with open(MANIFEST, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _last_modified(name):
    for d in manifest().get("dateien", []) or []:
        if d.get("name") == name:
            return d.get("last_modified")
    return "?"


def src_line(ebene="anwender"):
    return (f'Grundschutz++ ({ebene}, BSI Stand-der-Technik-Bibliothek, '
            f'Stand {_last_modified(ebene)}) — Lizenz CC BY-SA 4.0')


def walk_controls(node, path=()):
    here = path + (((node.get("id"), node.get("title")),)) if node.get("id") else path
    for c in node.get("controls", []) or []:
        yield c, here
    for g in node.get("groups", []) or []:
        yield from walk_controls(g, here)


def prop(c, name, default=None):
    for p in c.get("props", []) or []:
        if p.get("name") == name:
            return p.get("value")
    return default


def _collect_prose(part, acc):
    if part.get("prose"):
        acc.append(part["prose"])
    for sp in part.get("parts", []) or []:
        _collect_prose(sp, acc)


def _param_map(c):
    m = {}
    for p in c.get("params", []) or []:
        vals = p.get("values")
        if vals:
            m[p["id"]] = " / ".join(vals)
        elif p.get("label"):
            m[p["id"]] = p["label"]
    return m


def _resolve_params(text, pmap):
    return PARAM_RE.sub(lambda mo: pmap.get(mo.group(1), mo.group(0)), text)


def part_text(c, name):
    acc = []

    def find(parts):
        for p in parts or []:
            if p.get("name") == name:
                _collect_prose(p, acc)
            else:
                find(p.get("parts"))
    find(c.get("parts"))
    return _resolve_params("\n\n".join(acc).strip(), _param_map(c))


def find_control(cat, cid):
    if not cat:
        return None, None
    cid = cid.strip().lower()
    for c, path in walk_controls(cat):
        if (c.get("id") or "").lower() == cid:
            return c, path
    return None, None


def fmt_control(c, path, ebene="anwender"):
    out = [f'### {c.get("id")} — {c.get("title", "")}']
    crumbs = " → ".join(f'{gid} {gt}'.strip() for gid, gt in path if gid)
    if crumbs:
        out.append(f'Pfad: {crumbs}')
    meta = []
    for n in ("sec_level", "effort_level", "alt-identifier"):
        v = prop(c, n)
        if v is not None:
            meta.append(f'{n}={v}')
    if meta:
        out.append("Metadaten: " + ", ".join(meta))
    st = part_text(c, "statement")
    if st:
        out.append("\nAnforderung:\n" + st)
    gd = part_text(c, "guidance")
    if gd:
        out.append("\nHinweise:\n" + gd)
    out.append(f'\nQuelle: {src_line(ebene)}')
    return "\n".join(out)


def cmd_status(cat, methodik):
    m = manifest()
    print(f'Edition:    {m.get("edition", "grundschutz++")}')
    print(f'Abgerufen:  {m.get("abgerufen_am", "?")}')
    print(f'Lizenz:     {m.get("lizenz", "CC BY-SA 4.0")}')
    print(f'OSCAL:      {cat.get("metadata", {}).get("oscal-version", "?")}')
    print(f'Korpus:     {PP}')
    print("\nEbenen:")
    dateien = m.get("dateien")
    if dateien:
        for d in dateien:
            extra = f' — {d["anzahl_anforderungen"]} Anf.' if d.get("anzahl_anforderungen") else ""
            print(f'  {d["name"]:<9} {d.get("titel") or d["datei"]}{extra}  (Stand {d.get("last_modified", "?")})')
    else:
        print(f'  anwender  {cat.get("metadata", {}).get("title", "?")} — {sum(1 for _ in walk_controls(cat))} Anf.')
        if methodik:
            print(f'  methodik  {methodik.get("metadata", {}).get("title", "?")} — {sum(1 for _ in walk_controls(methodik))} Anf.')


def cmd_groups(cat):
    def rec(node, depth):
        gid, gt = node.get("id"), node.get("title")
        if gid:
            nctrl = len(node.get("controls", []) or [])
            tag = f' ({nctrl} Anf.)' if nctrl else ''
            print(f'{"  " * depth}{gid} — {gt}{tag}')
        for g in node.get("groups", []) or []:
            rec(g, depth + 1 if gid else depth)
    for g in cat.get("groups", []) or []:
        rec(g, 0)


def cmd_list(cat, grp):
    grp_l = grp.strip().lower()
    rows = []
    for c, path in walk_controls(cat):
        gids = [gid for gid, _ in path if gid]
        if any(g.lower() == grp_l or g.lower().startswith(grp_l + ".") for g in gids) \
           or (c.get("id") or "").lower().startswith(grp_l + "."):
            rows.append(c)
    if not rows:
        die(f'Keine Anforderungen unter "{grp}". Tipp:  gs.py groups')
    for c in rows:
        sl = prop(c, "sec_level", "")
        print(f'{c.get("id"):<12} {c.get("title", "")}  [{sl}]')
    print(f'\n{len(rows)} Anforderungen — {src_line()}')


def cmd_get(cat, cid, methodik=None):
    c, path = find_control(cat, cid)
    if not c:
        die(f'Anforderung "{cid}" nicht gefunden. Tipp:  gs.py search <begriff>')
    print(fmt_control(c, path, "anwender"))
    mc, mp = find_control(methodik, cid)
    if mc:
        same = (part_text(mc, "statement") == part_text(c, "statement")
                and part_text(mc, "guidance") == part_text(c, "guidance"))
        if same:
            print(f'\n(Methodik-Ebene {mc.get("id")} vorhanden — Text identisch; '
                  f'die Anforderung stammt 1:1 aus der Methodik-Vorgabe.)')
        else:
            print("\n--- Methodik-Ebene (Vorgehen / das Warum) ---")
            print(fmt_control(mc, mp, "methodik"))


def cmd_search(cat, term):
    t = term.lower()
    hits = []
    for c, path in walk_controls(cat):
        hay = " ".join([
            c.get("title", ""), part_text(c, "statement"), part_text(c, "guidance"),
        ]).lower()
        if t in hay:
            top = next((gid for gid, _ in path if gid), "")
            hits.append((c.get("id"), c.get("title", ""), top))
    if not hits:
        die(f'Kein Treffer fuer "{term}".')
    for cid, title, top in hits:
        print(f'{cid:<12} [{top:<5}] {title}')
    print(f'\n{len(hits)} Treffer — danach volltext:  gs.py get <ID>')


def cmd_prozess(methodik):
    if not methodik:
        die("Keine Methodik-Ebene im Korpus. Erst aktualisieren:  nix run .#ingest")
    print(f'Vorgehensweise Grundschutz++ (Methodik-Ebene) — {src_line("methodik")}\n')
    for g in methodik.get("groups", []) or []:
        print(f'{g.get("id")} — {g.get("title")}')
        for c, _ in walk_controls(g):
            print(f'    {c.get("id"):<10} {c.get("title", "")}')
        print()


def cmd_json(cat, cid, methodik=None):
    c, _ = find_control(cat, cid)
    if not c:
        c, _ = find_control(methodik, cid)
    if not c:
        die(f'Anforderung "{cid}" nicht gefunden.')
    print(json.dumps(c, ensure_ascii=False, indent=2))


def main():
    args = sys.argv[1:]
    if not args:
        die(__doc__)
    cmd, rest = args[0], args[1:]
    cat = load_catalog()
    methodik = load_methodik()
    if cmd == "status":
        cmd_status(cat, methodik)
    elif cmd == "groups":
        cmd_groups(cat)
    elif cmd == "list" and rest:
        cmd_list(cat, rest[0])
    elif cmd == "get" and rest:
        cmd_get(cat, rest[0], methodik)
    elif cmd == "search" and rest:
        cmd_search(cat, " ".join(rest))
    elif cmd == "prozess":
        cmd_prozess(methodik)
    elif cmd == "json" and rest:
        cmd_json(cat, rest[0], methodik)
    else:
        die(__doc__)


if __name__ == "__main__":
    main()
