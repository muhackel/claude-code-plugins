#!/usr/bin/env python3
"""Lookup-CLI fuer den lokalen Grundschutz-OSCAL-Korpus.

Kommandos:
  status            Korpus-Status (Version, Anzahl Schichten/Anforderungen)
  groups            Schichten/Gruppen-Baum
  list <GRUPPE>     Anforderungen einer Schicht/Gruppe (z.B. GC, GC.1)
  get <ID>          eine Anforderung volltext, zitierfaehig (z.B. GC.1.1)
  search <BEGRIFF>  Volltextsuche in Titel/statement/guidance
  json <ID>         rohes OSCAL-Control (fuer crosswalk/debug)
"""
import json
import os
import re
import sys

PARAM_RE = re.compile(r"\{\{\s*insert:\s*param,\s*([^}\s,]+)\s*\}\}")

CORPUS = os.environ.get("GS_CORPUS_DIR", os.path.expanduser("~/.local/share/it-grundschutz/corpus"))
CATALOG = os.path.join(CORPUS, "grundschutz-pp", "catalog.json")
MANIFEST = os.path.join(CORPUS, "grundschutz-pp", "manifest.json")


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def load_catalog():
    if not os.path.exists(CATALOG):
        die(f"Kein Korpus unter {CATALOG}.\nErst laden:  nix run .#ingest")
    with open(CATALOG, encoding="utf-8") as f:
        return json.load(f)["catalog"]


def manifest():
    try:
        with open(MANIFEST, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def src_line():
    return f'Grundschutz++ (BSI Stand-der-Technik-Bibliothek, Stand {manifest().get("last_modified", "?")}) — Lizenz CC BY-SA 4.0'


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
    cid = cid.strip().lower()
    for c, path in walk_controls(cat):
        if (c.get("id") or "").lower() == cid:
            return c, path
    return None, None


def fmt_control(c, path):
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
    out.append(f'\nQuelle: {src_line()}')
    return "\n".join(out)


def cmd_status(cat):
    m = manifest()
    n_groups = len(cat.get("groups", []) or [])
    n_ctrl = sum(1 for _ in walk_controls(cat))
    print(f'Titel:        {cat.get("metadata", {}).get("title", "?")}')
    print(f'Edition:      {m.get("edition", "grundschutz++")}')
    print(f'Stand:        {m.get("last_modified", cat.get("metadata", {}).get("last-modified", "?"))}')
    print(f'Abgerufen:    {m.get("abgerufen_am", "?")}')
    print(f'OSCAL:        {cat.get("metadata", {}).get("oscal-version", "?")}')
    print(f'Schichten:    {n_groups}')
    print(f'Anforderungen:{n_ctrl:>4}')
    print(f'Korpus:       {CATALOG}')


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


def cmd_get(cat, cid):
    c, path = find_control(cat, cid)
    if not c:
        die(f'Anforderung "{cid}" nicht gefunden. Tipp:  gs.py search <begriff>')
    print(fmt_control(c, path))


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


def cmd_json(cat, cid):
    c, _ = find_control(cat, cid)
    if not c:
        die(f'Anforderung "{cid}" nicht gefunden.')
    print(json.dumps(c, ensure_ascii=False, indent=2))


def main():
    args = sys.argv[1:]
    if not args:
        die(__doc__)
    cmd, rest = args[0], args[1:]
    cat = load_catalog()
    if cmd == "status":
        cmd_status(cat)
    elif cmd == "groups":
        cmd_groups(cat)
    elif cmd == "list" and rest:
        cmd_list(cat, rest[0])
    elif cmd == "get" and rest:
        cmd_get(cat, rest[0])
    elif cmd == "search" and rest:
        cmd_search(cat, " ".join(rest))
    elif cmd == "json" and rest:
        cmd_json(cat, rest[0])
    else:
        die(__doc__)


if __name__ == "__main__":
    main()
