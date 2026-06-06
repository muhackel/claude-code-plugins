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
  coverage --targets <...>  Abdeckungs-Modellierung über mehrere Assets: Vereinigungs-Soll + Querschnitt.
                    Grundschutz++: Zielobjektkategorien, querschnittlich = STM.5.4. Edition 2023: generische
                    Asset-Typen über die plugin-eigene Baustein-Hinttabelle (heuristisch), übergreifend = immer.
  crosswalk <ID> [--top N]  Heuristischer Crosswalk: Quell-ID (jeweils ANDERE Edition) → Top-Kandidaten
                    der aktiven Edition per Token-Überlappung (kein offizielles BSI-Mapping)
  json <ID>         rohes OSCAL-Control (für crosswalk/debug)

Beispiele:
  gs.py status
  gs.py targets
  gs.py list --target Hostsysteme --inherit    # Anforderungen für Server (inkl. vererbt von IT-Systeme)
  gs.py coverage --targets "Hostsysteme,Netze,Administrierende"   # Soll über mehrere Assets + STM.5.4-Lücke
  gs.py crosswalk SYS.1.1.A5    # Edition-2023-ID → passende Grundschutz++-Anforderungen (heuristisch)
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


HINTS_2023 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data",
                          "edition-2023-baustein-komponenten.csv")


def load_baustein_hints():
    """Plugin-eigene Komponente->Baustein-Hinttabelle (Edition 2023, MIT, heuristisch — NICHT Korpus).
    Pfad: Env GS_HINTS_FILE (vom flake gesetzt) oder skriptrelativ ../data/...
    Liefert {by_id, components} oder None, wenn die CSV fehlt."""
    path = os.environ.get("GS_HINTS_FILE") or HINTS_2023
    if not os.path.exists(path):
        return None
    by_id, components = {}, set()
    try:
        with open(path, encoding="utf-8", newline="") as f:
            rows = (ln for ln in f if not ln.lstrip().startswith("#"))
            for r in csv.DictReader(rows):
                bid = (r.get("baustein_id") or "").strip()
                if not bid:
                    continue
                komp = [k.strip() for k in (r.get("komponenten") or "").split(";") if k.strip()]
                bindung = (r.get("bindung") or "").strip()
                by_id[bid] = {"titel": (r.get("titel") or "").strip(),
                              "komponenten": set(komp), "bindung": bindung}
                if bindung != "übergreifend":
                    components.update(komp)
    except Exception:
        return None
    return {"by_id": by_id, "components": components}


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


# --- Token-Scorer: gemeinsame Heuristik für search und crosswalk ---
_WORD_RE = re.compile(r"[a-zäöüß0-9]+")

# Funktionswörter + normative Modalverben — tragen keine Trennschärfe.
STOPWORDS = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "eines",
    "einem", "einen", "und", "oder", "aber", "sondern", "auch", "sowie", "bzw",
    "für", "mit", "von", "bei", "aus", "auf", "durch", "über", "unter", "nach",
    "vor", "zwischen", "ohne", "gegen", "samt", "per", "via",
    "in", "im", "an", "am", "zu", "zur", "zum", "als", "wie", "ist", "sind",
    "war", "wird", "werden", "wurde", "wurden", "sein", "seine", "seinen",
    "muss", "müssen", "soll", "sollte", "sollten", "sollen", "kann", "können",
    "darf", "dürfen", "nicht", "nur", "alle", "aller", "allen", "allem",
    "jede", "jeder", "jedes", "jeden", "diese", "dieser", "dieses", "diesem",
    "dass", "damit", "sodass", "wenn", "dann", "beim", "haben", "hat", "hatte",
    "ihre", "ihren", "ihrer", "dabei", "hierzu", "hierfür", "entsprechend",
    "jeweils", "etc", "ggf", "sowohl", "dessen", "deren", "welche", "welcher",
    "welches", "einschließlich", "gemäß", "weitere", "weiteren", "sind",
}


def _tokenize(text):
    """Text → Menge trennscharfer Tokens (lowercase, Stopwörter/Kurzwörter/reine Zahlen raus)."""
    out = set()
    for w in _WORD_RE.findall((text or "").lower()):
        if len(w) >= 3 and not w.isdigit() and w not in STOPWORDS:
            out.add(w)
    return out


def _token_match(qt, dtokens):
    """Gewicht eines Query-Tokens gegen die Doc-Tokens: exakt=2, Teilstring (Komposita)=1, sonst 0."""
    if qt in dtokens:
        return 2
    if len(qt) >= 4:
        for dt in dtokens:
            if len(dt) >= 4 and (qt in dt or dt in qt):
                return 1
    return 0


def _overlap(qset, dtokens):
    return sum(_token_match(q, dtokens) for q in qset)


def _overlap_exact(qset, dtokens):
    """Nur exakte Token-Treffer (weight 1) — für den rauschanfälligen Statement↔Statement-Kanal."""
    return sum(1 for q in qset if q in dtokens)


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


def _search_substring(cat, term):
    """Roher Teilstring-Fallback (für Anfragen, die nur aus Stop-/Kurzwörtern bestehen)."""
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


def cmd_search(cat, term):
    qset = _tokenize(term)
    if not qset:  # nur Stop-/Kurzwörter — kein trennscharfes Token, roh suchen
        return _search_substring(cat, term)
    scored = []
    for c, path in walk_controls(cat):
        ttok = _tokenize(c.get("title", ""))
        btok = ttok | _tokenize(part_text(c, "statement")) | _tokenize(part_text(c, "guidance"))
        s = _overlap(qset, btok) + _overlap(qset, ttok)  # Titel-Treffer zusätzlich gewichtet
        if s > 0:
            top = next((gid for gid, _ in path if gid), "")
            scored.append((s, c.get("id"), c.get("title", ""), top))
    if not scored:
        die(f'Kein Treffer für "{term}".')
    scored.sort(key=lambda x: (-x[0], x[1] or ""))
    cap = 40
    shown = scored[:cap]
    for s, cid, title, top in shown:
        print(f'{s:>3}  {cid:<12} [{top:<5}] {title}')
    extra = len(scored) - len(shown)
    note = f' ({extra} schwächere nach Score gekürzt — Begriff schärfen)' if extra else ''
    print(f'\n{len(scored)} Treffer{note} — Score = gewichtete Token-Treffer; volltext:  gs.py get <ID>')


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


def _resolve_component(token, hints):
    """Asset-Typ-Eingabe (case-insensitiv, exakt) auf einen kanonischen Komponenten-Namen abbilden."""
    tl = (token or "").strip().lower()
    if not tl:
        return None
    for c in hints["components"]:
        if c.lower() == tl:
            return c
    return None


def cmd_coverage_2023(cat, args, hints):
    """Abdeckungs-Modellierung für Edition 2023 über die plugin-eigene Komponente->Baustein-Hinttabelle
    (heuristisch, KEIN BSI-Mapping): Vereinigungs-Soll der zutreffenden Bausteine + Ausweis der
    übergreifenden Bausteine, die unabhängig von den Assets immer zu modellieren sind."""
    if hints is None:
        die("Hinttabelle fehlt (data/edition-2023-baustein-komponenten.csv) — Plugin unvollständig?")
    raw, _ = _parse_coverage_opts(args)
    comps_all = sorted(hints["components"])
    if not raw:
        die('coverage (Edition 2023) braucht Asset-Typen:\n'
            '  gs.py --edition edition-2023 coverage --targets "Server,Webanwendung,Netz"\n'
            'Verfügbare Asset-Typen: ' + ", ".join(comps_all))

    resolved, wanted = [], set()
    for t in raw:
        canon = _resolve_component(t, hints)
        resolved.append((t, canon))
        if canon:
            wanted.add(canon)

    by_id = hints["by_id"]
    # Korpus-Bausteine + Titel (autoritativ; 'G 0' Elementare Gefährdungen via Leerzeichen ausschließen)
    corpus = {}
    for c, path in walk_controls(cat):
        if not path:
            continue
        bid, btitel = path[-1]
        if bid and " " not in bid:
            corpus.setdefault(bid, btitel)

    present = [(bid, rec) for bid, rec in by_id.items() if bid in corpus]
    gebunden = [(bid, rec) for bid, rec in present if rec["bindung"] != "übergreifend"]
    cross = [(bid, rec) for bid, rec in present if rec["bindung"] == "übergreifend"]
    union = [(bid, rec) for bid, rec in gebunden if rec["komponenten"] & wanted]

    def titel(bid, rec):
        return corpus.get(bid) or rec["titel"]

    print(f'Abdeckungs-Modellierung (Edition 2023, heuristisch) — {src_line()}')
    print(f'Asset-Typen: {len(resolved)} · Bausteine im Korpus: {len(corpus)}\n')

    print('## Assets (Eingabe → Asset-Typ)')
    print('| Eingabe | aufgelöst auf | Bausteine |')
    print('|---|---|---|')
    for t, canon in resolved:
        if canon:
            n = sum(1 for _, rec in gebunden if canon in rec["komponenten"])
            print(f'| {t} | {canon} | {n} |')
        else:
            sugg = _suggest(t, comps_all)
            tipp = f' (meintest du: {", ".join(sugg)}?)' if sugg else ''
            print(f'| {t} | **unbekannt**{tipp} | 0 |')

    print(f'\n## Vereinigungs-Soll — {len(union)} komponentengebundene Bausteine')
    for bid, rec in union:
        print(f'{bid:<12} {titel(bid, rec)}  [{", ".join(sorted(rec["komponenten"]))}]')

    print(f'\n## Übergreifend / immer zu modellieren — {len(cross)} Bausteine')
    print('Prozessual/organisatorisch — treffen unabhängig von den Assets praktisch immer zu '
          '(Pendant zur querschnittlichen Modellierung STM.5.4 in Grundschutz++).')
    print(", ".join(bid for bid, _ in cross))

    comp_count = Counter()
    for _, rec in gebunden:
        for k in rec["komponenten"]:
            comp_count[k] += 1
    nicht = [(k, comp_count[k]) for k in comps_all if k not in wanted]

    print('\n## Bilanz')
    pct = round(100 * len(union) / len(gebunden)) if gebunden else 0
    print(f'- Vereinigungs-Soll: {len(union)} von {len(gebunden)} komponentengebundenen Bausteinen ({pct}%)')
    print(f'- Übergreifend (immer): {len(cross)} — unabhängig von der Asset-Liste zu modellieren')
    if nicht:
        print('- Nicht modellierte Asset-Typen (Vollständigkeits-Check — fehlt ein Asset?): '
              + ", ".join(f'{k} ({n})' for k, n in nicht))
    missing = sorted(set(corpus) - set(by_id))
    stale = sorted(set(by_id) - set(corpus))
    if missing:
        print(f'- [!] Korpus-Bausteine ohne Hint-Zuordnung ({len(missing)}): '
              + ", ".join(missing) + ' — Hinttabelle nachpflegen.')
    if stale:
        print(f'- [!] Hint-Einträge ohne Korpus-Baustein ({len(stale)}): ' + ", ".join(stale))
    print('\n_Heuristische Modellierungshilfe (kein offizielles BSI-Mapping). Bausteine zitierfähig via '
          'gs.py --edition edition-2023 list <baustein> / checklist. Die finale Relevanz je Baustein '
          'entscheidet der Mensch._')


def cmd_json(cat, cid, methodik=None):
    c, _ = find_control(cat, cid)
    if not c:
        c, _ = find_control(methodik, cid)
    if not c:
        die(f'Anforderung "{cid}" nicht gefunden.')
    print(json.dumps(c, ensure_ascii=False, indent=2))


def _other_edition(ed):
    return "edition-2023" if ed == "grundschutz-pp" else "grundschutz-pp"


def load_edition_catalog(edition):
    """Katalog einer beliebigen Edition laden, ohne die aktiven Globals zu verändern."""
    p = os.path.join(CORPUS, edition, "catalog.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)["catalog"]
    except Exception:
        return None


def _int_or_die(s):
    try:
        n = int(s)
    except ValueError:
        die(f'--top erwartet eine Zahl, nicht "{s}".')
    if n < 1:
        die("--top muss >= 1 sein.")
    return n


def _parse_crosswalk_opts(args):
    cid, topn = None, 8
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--top":
            if i + 1 >= len(args):
                die("--top braucht eine Zahl.")
            topn = _int_or_die(args[i + 1])
            i += 2
            continue
        if a.startswith("--top="):
            topn = _int_or_die(a.split("=", 1)[1])
            i += 1
            continue
        if cid is None:
            cid = a
        i += 1
    return cid, topn


def cmd_crosswalk(target_cat, args):
    """Heuristischer Crosswalk: Quell-ID (jeweils ANDERE Edition) → Top-Kandidaten der aktiven
    Edition per Token-Überlappung. KEINE gemeinsame Kennung, KEIN offizielles BSI-Mapping."""
    cid, topn = _parse_crosswalk_opts(args)
    if not cid:
        die('crosswalk braucht eine Quell-ID:  gs.py crosswalk NET.3.3  '
            '(ID aus der jeweils ANDEREN Edition; Ziel ist die aktive Edition).')
    target_ed = EDITION
    source_ed = _other_edition(target_ed)
    source_cat = load_edition_catalog(source_ed)
    if source_cat is None:
        ing = "nix run .#ingest-2023" if source_ed == "edition-2023" else "nix run .#ingest"
        die(f'Quell-Edition "{source_ed}" nicht geladen — der Crosswalk braucht BEIDE Editionen.\n'
            f'Erst laden:  {ing}')
    c, _ = find_control(source_cat, cid)
    if not c:
        tc, _ = find_control(target_cat, cid)
        hint = (f'\n("{cid}" liegt in der AKTIVEN Edition "{target_ed}" — crosswalk erwartet eine '
                f'ID aus "{source_ed}". Ziel-Edition ggf. mit --edition umstellen.)' if tc else '')
        die(f'"{cid}" nicht in Quell-Edition "{source_ed}" gefunden.{hint}\n'
            f'Tipp:  gs.py --edition {source_ed} search <begriff>')

    if prop(c, "status") == "entfallen" or (c.get("title", "").strip().upper() == "ENTFALLEN"):
        print(f'Crosswalk (heuristisch) — Quelle: {source_ed} → Ziel: {target_ed}')
        print(f'Quell-Anforderung: {c.get("id")} — {c.get("title", "")}')
        print(f'\nQuell-Anforderung ist in {source_ed} ENTFALLEN — ein inhaltliches Mapping ist '
              f'gegenstandslos. (In der Ziel-Edition ggf. ersatzlos aufgegangen oder über die '
              f'Zielobjektlogik abgedeckt; via gs.py groups/list gegenprüfen.)')
        return

    title = c.get("title", "")
    statement = part_text(c, "statement")
    qt_title = _tokenize(title)
    qt_stmt = _tokenize(statement) - qt_title

    # Titel ist beim Cross-Edition-Crosswalk das kuratierte Semantik-Label → Titel↔Titel dominiert.
    # Der Statement↔Statement-Kanal nur exakt (kein Komposita-Substring), sonst flutet langer Prosa-Text.
    scored = []
    for tc, _ in walk_controls(target_cat):
        tt = _tokenize(tc.get("title", ""))
        ts = _tokenize(part_text(tc, "statement"))
        s = (4 * _overlap(qt_title, tt)        # Titel ↔ Titel (stärkstes Signal)
             + _overlap(qt_title, ts)          # Quell-Titel im Ziel-Statement
             + _overlap(qt_stmt, tt)           # Quell-Statement im Ziel-Titel
             + _overlap_exact(qt_stmt, ts))    # Statement ↔ Statement, nur exakt (entrauscht)
        if s > 0:
            scored.append((s, tc))
    scored.sort(key=lambda x: (-x[0], x[1].get("id") or ""))
    top = scored[:topn]

    old = EDITION
    set_edition(source_ed)
    src_quelle = src_line("anwender")
    set_edition(old)
    tgt_quelle = src_line("anwender")

    print(f'Crosswalk (heuristisch) — Quelle: {source_ed} → Ziel: {target_ed}')
    print(f'Quell-Anforderung: {c.get("id")} — {title}')
    excerpt = " ".join(statement.split())
    if excerpt:
        print(f'  "{excerpt[:200]}{"…" if len(excerpt) > 200 else ""}"')
    print()
    if not top:
        die('Keine inhaltliche Überlappung gefunden — der Wortlaut der Quell-Anforderung findet in der '
            f'Ziel-Edition "{target_ed}" kein Echo. Manuell über gs.py search/groups gegenprüfen.')
    print(f'Top-{len(top)} Kandidaten in {target_ed} (Token-Überlappung — KEIN offizielles BSI-Mapping):')
    print('| Score | ID | Titel | Zielobjektkategorie | sec_level |')
    print('|---|---|---|---|---|')
    for s, tc in top:
        cats_str = ", ".join(sorted(control_targets(tc))) or "—"
        print(f'| {s} | {tc.get("id")} | {tc.get("title", "")} | {cats_str} | {prop(tc, "sec_level", "")} |')
    print(f'\n> Heuristischer Inhaltsvergleich (Wortlaut-Überlappung) — KEINE gemeinsame Kennung und '
          f'kein offizielles BSI-Mapping. Score = gewichtete Token-Treffer (Titel↔Titel am stärksten). '
          f'Kandidaten per `gs.py get <ID>` prüfen; die Zuordnung verantwortet der Mensch (ISB).')
    print(f'Quelle Quell-ID: {src_quelle}')
    print(f'Quelle Ziel:     {tgt_quelle}')


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
        if EDITION == "edition-2023":
            cmd_coverage_2023(cat, rest, load_baustein_hints())
        else:
            cmd_coverage(cat, rest, load_categories())
    elif cmd == "crosswalk":
        cmd_crosswalk(cat, rest)
    elif cmd == "json" and rest:
        cmd_json(cat, rest[0], methodik)
    else:
        die(__doc__)


if __name__ == "__main__":
    main()
