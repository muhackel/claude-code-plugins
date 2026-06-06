#!/usr/bin/env python3
"""Lookup-CLI für den lokalen Grundschutz-OSCAL-Korpus.

Multi-Edition: --edition <grundschutz-pp|edition-2023> (oder Env GS_EDITION),
Default 'grundschutz-pp'. Der Schalter wählt den Korpus-Unterordner.

Grundschutz++ hat zwei Ebenen (gleiche ID GC.1.1): 'anwender' = konkrete
Anforderung, 'methodik' = Vorgehensweise/das Warum dahinter. Edition 2023 hat
nur eine Ebene (klassische Schichten ISMS/ORP/.../INF + Bausteine).

Kommandos:
  status            Korpus-Status (Ebenen, Anzahl Anforderungen)
  groups            Schichten/Gruppen-Baum (Anwenderkatalog)
  targets           Zielobjektkategorien + Häufigkeiten (nur Grundschutz++, aus dem Namespace)
  list <GRP...>     Anforderungen einer/mehrerer Schichten/Gruppen oder exakter IDs (z.B. GC, KONF.2, KONF.8.1)
                    optional gefiltert:  --target <Kategorie> [--inherit]  (Vererbung gemäß STM.5.2)
  get <ID>          Anforderung volltext, zitierfähig — inkl. Methodik-Ebene, falls vorhanden
  search <BEGRIFF>  Volltextsuche in Titel/statement/guidance (Anwenderkatalog)
  prozess           Vorgehensweise als Schrittfolge (Methodik-Ebene, GC->STM->UMS->PERF->VRB)
  checklist <GRP...> leere Soll-Ist-Check-Vorlage; nimmt ebenfalls --target/--inherit
  coverage --targets <Kat,Kat,...>  Abdeckungs-Modellierung über mehrere Zielobjekte (nur Grundschutz++):
                    Vereinigungs-Soll + Ausweis der querschnittlichen Anf. ohne Zielobjekt (STM.5.4)
  json <ID>         rohes OSCAL-Control (für crosswalk/debug)

Beispiele:
  gs.py status
  gs.py targets
  gs.py list --target Hostsysteme --inherit    # Anforderungen für Server (inkl. vererbt von IT-Systeme)
  gs.py coverage --targets "Hostsysteme,Netze,Administrierende"   # Soll über mehrere Assets + STM.5.4-Lücke
  gs.py --edition edition-2023 get SYS.1.1.A5
"""
import csv
import difflib
import json
import os
import re
import sys
from collections import Counter

PARAM_RE = re.compile(r"\{\{\s*insert:\s*param,\s*([^}\s,]+)\s*\}\}")

EDITIONS = ("grundschutz-pp", "edition-2023")
DEFAULT_EDITION = os.environ.get("GS_EDITION", "grundschutz-pp")

CORPUS = os.environ.get("GS_CORPUS_DIR", os.path.expanduser("~/.local/share/it-grundschutz/corpus"))

# Modul-Globals; werden in main() je nach Edition gesetzt (set_edition).
EDITION = DEFAULT_EDITION
PP = os.path.join(CORPUS, DEFAULT_EDITION)
CATALOG = os.path.join(PP, "catalog.json")            # Anwenderkatalog
METHODIK = os.path.join(PP, "methodik-catalog.json")  # Methodik-Quellkatalog (nur Grundschutz++)
MANIFEST = os.path.join(PP, "manifest.json")
CATEGORIES = os.path.join(PP, "target_object_categories.csv")  # Zielobjekt-Namespace (nur Grundschutz++)


def set_edition(edition):
    global EDITION, PP, CATALOG, METHODIK, MANIFEST, CATEGORIES
    EDITION = edition
    PP = os.path.join(CORPUS, edition)
    CATALOG = os.path.join(PP, "catalog.json")
    METHODIK = os.path.join(PP, "methodik-catalog.json")
    MANIFEST = os.path.join(PP, "manifest.json")
    CATEGORIES = os.path.join(PP, "target_object_categories.csv")


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def load_catalog():
    if not os.path.exists(CATALOG):
        ingest = "nix run .#ingest-2023" if EDITION == "edition-2023" else "nix run .#ingest"
        die(f"Kein Korpus unter {CATALOG}.\nErst laden:  {ingest}")
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


def load_categories():
    """Zielobjekt-Namespace target_object_categories.csv laden (nur Grundschutz++).
    Liefert {by_name, by_uuid, syn} oder None, wenn die CSV fehlt."""
    if not os.path.exists(CATEGORIES):
        return None
    by_name, by_uuid, syn = {}, {}, {}
    try:
        with open(CATEGORIES, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                name = (r.get("Zielobjektkategorie") or "").strip()
                if not name:
                    continue
                syns = [s.strip() for s in (r.get("Synonyme") or "").split(",") if s.strip()]
                rec = {"name": name, "typ": (r.get("Typ") or "").strip(),
                       "definition": (r.get("Definition") or "").strip(), "synonyme": syns,
                       "uuid": (r.get("UUID") or "").strip(),
                       "child_of": (r.get("ChildOfUUID") or "").strip()}
                by_name[name] = rec
                by_uuid[rec["uuid"]] = name
                syn.setdefault(name.lower(), name)
                for s in syns:
                    syn.setdefault(s.lower(), name)
    except Exception:
        return None
    return {"by_name": by_name, "by_uuid": by_uuid, "syn": syn}


def resolve_category(token, cats):
    """Eingabe (Name oder Synonym, case-insensitiv) auf den kanonischen Kategorienamen abbilden."""
    if not cats or not token:
        return None
    return cats["syn"].get(token.strip().lower())


def category_chain(name, cats):
    """Kategorie + alle Vorfahren (ChildOfUUID-Kette, zyklensicher)."""
    out, seen = [], set()
    cur = name
    while cur and cur not in seen:
        seen.add(cur)
        out.append(cur)
        rec = cats["by_name"].get(cur)
        if not rec or not rec["child_of"]:
            break
        cur = cats["by_uuid"].get(rec["child_of"])
    return out


def _suggest(token, candidates, limit=3):
    """Ähnliche Kandidaten zu token finden (Substring beidseitig, dann Fuzzy)."""
    if not token:
        return []
    tl = token.strip().lower()
    lc = {}
    for c in candidates:
        lc.setdefault(c.lower(), c)
    out = []
    for cl, disp in lc.items():
        if (tl in cl or cl in tl) and disp not in out:
            out.append(disp)
    for cl in difflib.get_close_matches(tl, list(lc.keys()), n=limit * 2, cutoff=0.6):
        if lc[cl] not in out:
            out.append(lc[cl])
    return out[:limit]


def _suggest_categories(token, cats, limit=3):
    """Ähnliche Zielobjektkategorien über Namen + Synonyme, kanonisch zurückgegeben."""
    if not cats or not token:
        return []
    tl = token.strip().lower()
    syn = cats["syn"]
    out = []
    for key, canon in syn.items():
        if (tl in key or key in tl) and canon not in out:
            out.append(canon)
    for key in difflib.get_close_matches(tl, list(syn.keys()), n=limit * 3, cutoff=0.6):
        if syn[key] not in out:
            out.append(syn[key])
    return out[:limit]


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
    if EDITION == "edition-2023":
        stand = _last_modified("kompendium")
        if stand == "?":
            stand = "Edition 2023"
        return (f'IT-Grundschutz-Kompendium {stand} (BSI, DocBook-XML) '
                f'— Lizenz CC BY-SA 4.0')
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


def control_targets(c):
    """Zielobjektkategorien einer Anforderung (Prop am statement-/_stm-Part)."""
    vals = set()
    for part in c.get("parts", []) or []:
        if part.get("name") == "statement":
            for pr in part.get("props", []) or []:
                if pr.get("name") == "target_object_categories":
                    for v in (pr.get("value") or "").split(","):
                        v = v.strip()
                        if v:
                            vals.add(v)
    return vals


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
    geladen = [e for e in EDITIONS if os.path.exists(os.path.join(CORPUS, e, "catalog.json"))]
    disp = ", ".join((e + " (aktiv)" if e == EDITION else e) for e in geladen)
    print(f'Verfügbar:  {disp or "—"}')
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


def _group_ids(cat):
    """Alle Gruppen-/Schicht-IDs des Katalogs (für 'Meintest du'-Tipps)."""
    out = []

    def rec(node):
        if node.get("id"):
            out.append(node["id"])
        for g in node.get("groups", []) or []:
            rec(g)
    for g in cat.get("groups", []) or []:
        rec(g)
    return out


def _selector_miss_tip(cat, grps, base):
    """Tipp mit ähnlichen Gruppen-IDs, wenn die Selektoren selbst nichts trafen."""
    if base or not grps:
        return ''
    cand = _group_ids(cat)
    sugg = []
    for s in grps:
        for x in _suggest(s, cand):
            if x not in sugg:
                sugg.append(x)
    return f' Meintest du: {", ".join(sugg[:3])}?' if sugg else ''


def _inherit_extra(base, target, cats, direct_count):
    """Wie viele Anforderungen --inherit zusätzlich brächte (0, wenn nichts/unaufgelöst)."""
    if not target or not cats or not resolve_category(target, cats):
        return 0
    return max(0, len(_apply_target(base, target, True, cats)) - direct_count)


def _select(cat, selectors):
    """Controls für mehrere Selektoren sammeln. Ein Selektor ist eine Gruppen-/
    Schicht-ID (GC, KONF.2) oder eine exakte Anforderungs-ID (KONF.8.1).
    Dedupliziert nach ID, Reihenfolge: je Selektor in Katalogreihenfolge."""
    sels = [s.strip().lower() for s in selectors if s and s.strip()]
    seen, out = set(), []
    for sel in sels:
        for c, path in walk_controls(cat):
            cid = (c.get("id") or "").lower()
            gids = [gid.lower() for gid, _ in path if gid]
            match = (cid == sel
                     or any(g == sel or g.startswith(sel + ".") for g in gids)
                     or cid.startswith(sel + "."))
            if match and cid not in seen:
                seen.add(cid)
                out.append((c, path))
    return out


def _apply_target(rows, target, inherit, cats):
    """rows (Liste (control, path)) auf eine Zielobjektkategorie filtern.
    Mit Vererbung (--inherit) zählen auch Anforderungen an Vorfahren-Kategorien."""
    if not target:
        return rows
    resolved = resolve_category(target, cats) if cats else None
    if resolved:
        wanted = set(category_chain(resolved, cats)) if inherit else {resolved}
    else:
        if cats:
            sugg = _suggest_categories(target, cats)
            tip = f' Meintest du: {", ".join(sugg)}?' if sugg else ''
            print(f'[!] "{target}" nicht im Zielobjekt-Namespace — exakter String-Match.{tip} '
                  f'Tipp:  gs.py targets', file=sys.stderr)
        wanted = {target}
    return [(c, p) for c, p in rows if control_targets(c) & wanted]


def cmd_targets(cat, cats):
    cnt = Counter()
    for c, _ in walk_controls(cat):
        for t in control_targets(c):
            cnt[t] += 1
    if not cnt:
        if EDITION != "grundschutz-pp":
            die("'targets' gibt es nur in Grundschutz++ — Edition 2023 kennt keine Zielobjektkategorien.")
        die("Keine Zielobjektkategorien im Korpus. Erst laden/aktualisieren:  nix run .#ingest")
    print(f'Zielobjektkategorien — {src_line()}')
    if cats:
        print('Filter:  gs.py list --target <Kategorie> [--inherit]  (Synonyme werden aufgelöst)\n')
        print('| Kategorie | Anf. | Typ | Eltern (erbt von) | Synonyme |')
        print('|---|---|---|---|---|')
        for name, n in cnt.most_common():
            rec = cats["by_name"].get(name, {})
            parent = cats["by_uuid"].get(rec.get("child_of", ""), "")
            syn = ", ".join(rec.get("synonyme", []))
            print(f'| {name} | {n} | {rec.get("typ", "")} | {parent} | {syn} |')
    else:
        for name, n in cnt.most_common():
            print(f'{n:4}  {name}')
        print('\n(Namespace-CSV fehlt — nur Häufigkeiten. nix run .#ingest für Definitionen/Vererbung.)')
    print(f'\n{sum(cnt.values())} Zuordnungen über {len(cnt)} Kategorien — '
          f'Namespace target_object_categories.csv (CC BY-SA 4.0).')


def cmd_list(cat, grps, target=None, inherit=False, cats=None):
    if not grps and not target:
        die('list braucht eine Gruppe/ID oder --target <Kategorie>. Tipp:  gs.py groups | gs.py targets')
    base = _select(cat, grps) if grps else [(c, p) for c, p in walk_controls(cat)]
    rows = _apply_target(base, target, inherit, cats)
    if not rows:
        sel = (" ".join(grps) + (f' --target {target}' if target else "")).strip()
        die(f'Keine Anforderungen für "{sel}".{_selector_miss_tip(cat, grps, base)} '
            f'Tipp:  gs.py groups | gs.py targets')
    for c, _ in rows:
        sl = prop(c, "sec_level", "")
        print(f'{c.get("id"):<12} {c.get("title", "")}  [{sl}]')
    tinfo = f' · Ziel: {target}{" +Vererbung" if inherit else ""}' if target else ""
    extra = 0 if inherit else _inherit_extra(base, target, cats, len(rows))
    ehint = f' (+{extra} über Vererbung mit --inherit)' if extra else ''
    print(f'\n{len(rows)} Anforderungen{tinfo}{ehint} — {src_line()}')


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
        die(f'Kein Treffer für "{term}".')
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


def cmd_checklist(cat, grps, target=None, inherit=False, cats=None):
    if not grps and not target:
        die('checklist braucht eine Gruppe/ID oder --target <Kategorie>. Tipp:  gs.py groups | gs.py targets')
    base = _select(cat, grps) if grps else [(c, p) for c, p in walk_controls(cat)]
    rows = _apply_target(base, target, inherit, cats)
    if not rows:
        sel = (" ".join(grps) + (f' --target {target}' if target else "")).strip()
        die(f'Keine Anforderungen für "{sel}".{_selector_miss_tip(cat, grps, base)} '
            f'Tipp:  gs.py groups | gs.py targets')

    def esc(s):
        return (s or "").replace("|", "\\|").replace("\n", " ").strip()

    hinweis = ("Grundschutz++ Umsetzung formal binär ja/nein, siehe UMS.1.1"
               if EDITION == "grundschutz-pp"
               else "klassischer IT-Grundschutz-Check, Edition 2023 / BSI-Standard 200-2")
    label = (", ".join(g.upper() for g in grps) or "alle")
    if target:
        label += f' (Ziel: {target}{" +Vererbung" if inherit else ""})'
    print(f'# Soll-Ist-Check (leere Vorlage) — {label}')
    print(f'# {src_line()}')
    print(f'# Status je Anforderung: entbehrlich | ja | teilweise | nein ({hinweis})')
    print()
    print('| ID | Titel | sec_level | Status | Begründung | Verantwortlich | Termin |')
    print('|---|---|---|---|---|---|---|')
    for c, _ in rows:
        status = "entfallen" if prop(c, "status") == "entfallen" else ""
        print(f'| {esc(c.get("id"))} | {esc(c.get("title"))} | {esc(prop(c, "sec_level", ""))} '
              f'| {status} |  |  |  |')
    print(f'\n_{len(rows)} Anforderungen. Status/Begründung/Verantwortlich/Termin sind '
          f'Erhebungsergebnis (firmenspezifisch, hier leer) — die Norm-Spalten stammen aus dem Korpus._')
    extra = 0 if inherit else _inherit_extra(base, target, cats, len(rows))
    if extra:
        print(f'\n> Hinweis: +{extra} Anforderungen über Vererbung der Oberkategorien — '
              f'erneut mit `--inherit` ziehen.')


def _parse_coverage_opts(args):
    """coverage-Argumente lösen: --targets <csv> (mehrfach/kommagetrennt), --inherit/--no-inherit.
    Freie Positionsargumente werden ebenfalls als (kommagetrennte) Kategorien gewertet.
    Vererbung ist bei coverage standardmäßig AN (Modellierungs-Vollständigkeit)."""
    raw, inherit = [], True
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--targets", "--target"):
            if i + 1 >= len(args):
                die("--targets braucht eine Kategorienliste (kommagetrennt). Tipp:  gs.py targets")
            raw += args[i + 1].split(",")
            i += 2
            continue
        if a.startswith("--targets=") or a.startswith("--target="):
            raw += a.split("=", 1)[1].split(",")
            i += 1
            continue
        if a == "--inherit":
            inherit = True
            i += 1
            continue
        if a == "--no-inherit":
            inherit = False
            i += 1
            continue
        raw += a.split(",")
        i += 1
    return [t.strip() for t in raw if t.strip()], inherit


def cmd_coverage(cat, args, cats):
    """Abdeckungs-Modellierung über mehrere Zielobjektkategorien (nur Grundschutz++):
    Vereinigungs-Soll + Ausweis der querschnittlichen Anforderungen ohne Zielobjekt (STM.5.4)."""
    if EDITION != "grundschutz-pp":
        die("'coverage' gibt es nur in Grundschutz++ — Edition 2023 modelliert über Bausteine "
            "(nutze list/checklist).")
    if not cats:
        die("Zielobjekt-Namespace fehlt. Erst laden/aktualisieren:  nix run .#ingest")
    raw, inherit = _parse_coverage_opts(args)
    if not raw:
        die('coverage braucht Zielobjektkategorien:  '
            'gs.py coverage --targets "Hostsysteme,Netze,Administrierende"  (Liste:  gs.py targets)')

    resolved, wanted = [], set()
    for t in raw:
        canon = resolve_category(t, cats)
        chain = (category_chain(canon, cats) if inherit else [canon]) if canon else []
        resolved.append((t, canon, chain))
        wanted.update(chain)

    all_rows = list(walk_controls(cat))
    union = [(c, p) for c, p in all_rows if control_targets(c) & wanted]
    bound = [(c, p) for c, p in all_rows if control_targets(c)]
    crosscut = [(c, p) for c, p in all_rows if not control_targets(c)]

    print(f'Abdeckungs-Modellierung (Grundschutz++) — {src_line()}')
    print(f'Zielobjekte: {len(resolved)} · Vererbung: {"an" if inherit else "aus"}\n')

    print('## Zielobjekte (Asset → Kategorie)')
    print('| Eingabe | aufgelöst auf | Anf. |')
    print('|---|---|---|')
    for t, canon, chain in resolved:
        if canon:
            n = sum(1 for c, _ in all_rows if control_targets(c) & set(chain))
            kette = canon if (not inherit or len(chain) == 1) else " ← ".join(chain)
            print(f'| {t} | {kette} | {n} |')
        else:
            sugg = _suggest_categories(t, cats)
            tipp = f' (meintest du: {", ".join(sugg)}?)' if sugg else ''
            print(f'| {t} | **unbekannt**{tipp} | 0 |')

    print(f'\n## Vereinigungs-Soll — {len(union)} zielobjektgebundene Anforderungen')
    for c, _ in union:
        print(f'{c.get("id"):<12} {c.get("title", "")}  [{prop(c, "sec_level", "")}]')

    layer = Counter()
    for c, p in crosscut:
        layer[next((gid for gid, _ in p if gid), "?")] += 1
    print(f'\n## Querschnittlich ohne Zielobjekt — STM.5.4 ({len(crosscut)} Anforderungen)')
    print('Hängen an KEINER Zielobjektkategorie, über --target NICHT erreichbar — über die '
          'Prozess-/Management-Schichten modellieren (GC/STM/UMS/VRB/PERF/RISK + organisatorisch).')
    print('Verteilung je Schicht: ' + ", ".join(f'{g}={n}' for g, n in layer.most_common()))

    cnt = Counter()
    for c, _ in all_rows:
        for tt in control_targets(c):
            cnt[tt] += 1
    nicht = [(name, n) for name, n in cnt.most_common() if name not in wanted]

    print('\n## Bilanz')
    pct = round(100 * len(union) / len(bound)) if bound else 0
    print(f'- Vereinigungs-Soll: {len(union)} von {len(bound)} zielobjektgebundenen Anforderungen ({pct}%)')
    print(f'- Querschnittlich (STM.5.4): {len(crosscut)} — separat über die Prozessschichten modellieren')
    if nicht:
        print('- Nicht modellierte Kategorien (Vollständigkeits-Check — fehlt ein Asset?): '
              + ", ".join(f'{name} ({n})' for name, n in nicht))
    print('\n_Soll-Liste übernehmbar (zitierfähig via gs.py get/checklist). Die finale '
          'Relevanzentscheidung je Anforderung trifft der Mensch (STM.5.4)._')


def cmd_json(cat, cid, methodik=None):
    c, _ = find_control(cat, cid)
    if not c:
        c, _ = find_control(methodik, cid)
    if not c:
        die(f'Anforderung "{cid}" nicht gefunden.')
    print(json.dumps(c, ensure_ascii=False, indent=2))


def _parse_edition(args):
    out = []
    edition = DEFAULT_EDITION
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--edition":
            if i + 1 >= len(args):
                die("--edition braucht ein Argument: " + " | ".join(EDITIONS))
            edition = args[i + 1]
            i += 2
            continue
        if a.startswith("--edition="):
            edition = a.split("=", 1)[1]
            i += 1
            continue
        out.append(a)
        i += 1
    if edition not in EDITIONS:
        die(f'Unbekannte Edition "{edition}". Erlaubt: ' + " | ".join(EDITIONS))
    return edition, out


def _split_target_opts(args):
    """--target <Kategorie> und --inherit aus den Argumenten lösen; Rest = Selektoren."""
    pos, target, inherit = [], None, False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--target":
            if i + 1 >= len(args):
                die("--target braucht eine Kategorie. Tipp:  gs.py targets")
            target = args[i + 1]
            i += 2
            continue
        if a.startswith("--target="):
            target = a.split("=", 1)[1]
            i += 1
            continue
        if a == "--inherit":
            inherit = True
            i += 1
            continue
        pos.append(a)
        i += 1
    return pos, target, inherit


def main():
    edition, args = _parse_edition(sys.argv[1:])
    set_edition(edition)
    if not args:
        die(__doc__)
    cmd, rest = args[0], args[1:]
    cat = load_catalog()
    methodik = load_methodik()
    if cmd == "status":
        cmd_status(cat, methodik)
    elif cmd == "groups":
        cmd_groups(cat)
    elif cmd == "targets":
        cmd_targets(cat, load_categories())
    elif cmd == "list" and rest:
        pos, target, inherit = _split_target_opts(rest)
        cmd_list(cat, pos, target, inherit, load_categories())
    elif cmd == "get" and rest:
        cmd_get(cat, rest[0], methodik)
    elif cmd == "search" and rest:
        cmd_search(cat, " ".join(rest))
    elif cmd == "prozess":
        cmd_prozess(methodik)
    elif cmd == "checklist" and rest:
        pos, target, inherit = _split_target_opts(rest)
        cmd_checklist(cat, pos, target, inherit, load_categories())
    elif cmd == "coverage":
        cmd_coverage(cat, rest, load_categories())
    elif cmd == "json" and rest:
        cmd_json(cat, rest[0], methodik)
    else:
        die(__doc__)


if __name__ == "__main__":
    main()
