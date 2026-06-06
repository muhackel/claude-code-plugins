#!/usr/bin/env python3
"""Adapter: IT-Grundschutz-Kompendium Edition 2023 (DocBook-XML) -> OSCAL-Katalog.

Normalisiert das vom BSI als DocBook 5.0 bereitgestellte XML
(`XML_Kompendium_2023.xml`) in das kanonische interne Schema dieses Plugins
(OSCAL-Katalog, strukturgleich zum Grundschutz++-Anwenderkatalog), damit
Lookup (gs.py) und Crosswalk editionsübergreifend einheitlich dagegen laufen.

Quelle: bsi.bund.de — Lizenz CC BY-SA 4.0. Der erzeugte Korpus wird bewusst
NICHT ins Plugin-Git eingecheckt, sondern ins lokale Datenverzeichnis gelegt.

Struktur des DocBook (verifiziert gegen Edition 2023, v4):
  book
    chapter "SYS IT-Systeme"          -> Schicht (group id=SYS)
      section "SYS.1.1 Allgemeiner Server"  -> Baustein (group id=SYS.1.1)
        section "Beschreibung"              -> group.parts name=overview
        section "Gefährdungslage"          -> group.parts name=guidance (Prosa)
        section "Anforderungen"
          section "Basis-Anforderungen"
            section "SYS.1.1.A1 ... (B) [Rolle]" -> control
          section "Standard-Anforderungen"  (S)
          section "Anforderungen bei erhöhtem Schutzbedarf" (H)
        section "Weiterführende Informationen"
    chapter "Elementare Gefährdungen"  -> group id="G 0" mit je control "G 0.x"

Qualifizierungsstufe steht im Anforderungstitel als (B)/(S)/(H) und ist die
maßgebliche Quelle für sec_level (Kreuzgeprüft gegen die Quali-Abschnitte:
0 Abweichungen bei 2124 Anforderungen).
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

DB = "http://docbook.org/ns/docbook"
XMLID = "{http://www.w3.org/XML/1998/namespace}id"
NS = {"db": DB}

DEFAULT_URL = ("https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Grundschutz/"
               "IT-GS-Kompendium/XML_Kompendium_2023.xml?__blob=publicationFile&v=4")
LICENSE_ID = "CC BY-SA 4.0"
OSCAL_VERSION = "1.1.3"
SEC_LEVEL_NS = ("https://www.bsi.bund.de/DE/Themen/Unternehmen-und-Organisationen/"
                "Standards-und-Zertifizierung/IT-Grundschutz/it-grundschutz_node.html")

LAYER_CODES = ("ISMS", "ORP", "CON", "OPS", "DER", "APP", "SYS", "IND", "NET", "INF")
LAYER_RE = re.compile(r"^(%s)\s+(.*)$" % "|".join(LAYER_CODES))
BAUSTEIN_RE = re.compile(r"^([A-Z]{2,4}(?:\.\d+)+)\s+(.*)$")
THREAT_RE = re.compile(r"^(G\s+0\.\d+)\s+(.*)$")
GEF_CHAPTER = "Elementare Gefährdungen"
QUALI_TITLES = {
    "Basis-Anforderungen", "Basis-Anforderung",
    "Standard-Anforderungen",
    "Anforderungen bei erhöhtem Schutzbedarf",
}
MARKER_TO_LEVEL = {"B": "Basis", "S": "Standard", "H": "erhöht"}
# Anforderungs-ID, Titel, Marker (B|S|H), optionale Rolle in [..]
REQ_TITLE_RE = re.compile(
    r"^([A-Z]{2,4}(?:\.\d+)*\.?A\d+)\s+(.*?)\s*\(([BSH])\)(?:\s*\[([^\]]+)\])?\s*$"
)


def log_info(msg):
    sys.stderr.write(f"\033[34m[*]\033[0m {msg}\n")


def log_ok(msg):
    sys.stderr.write(f"\033[32m[+]\033[0m {msg}\n")


def log_warn(msg):
    sys.stderr.write(f"\033[33m[!]\033[0m {msg}\n")


def log_err(msg):
    sys.stderr.write(f"\033[31m[x]\033[0m {msg}\n")


def die(msg, code=1):
    log_err(msg)
    sys.exit(code)


def _local(tag):
    return tag.split("}")[-1]


def title_of(node):
    t = node.find("db:title", NS)
    return (t.text or "").strip() if t is not None else ""


def subsections(node):
    return node.findall("db:section", NS)


def find_subsection(node, predicate):
    for sec in subsections(node):
        if predicate(title_of(sec)):
            return sec
    return None


def render_prose(node, skip_first_title=True):
    """DocBook-Blockinhalt eines Abschnitts in Markdown-ähnliche Prosa.

    Berücksichtigt para/simpara (Absätze), itemizedlist (Spiegelstriche) und
    orderedlist (nummeriert). Verschachtelte Listen werden eingerückt.
    """
    blocks = []

    def text(el):
        return re.sub(r"\s+", " ", "".join(el.itertext())).strip()

    def render_list(lst, indent):
        ordered = _local(lst.tag) == "orderedlist"
        lines = []
        for i, li in enumerate(lst.findall("db:listitem", NS), 1):
            bullet = f"{i}." if ordered else "-"
            parts = []
            sublists = []
            for child in list(li):
                lt = _local(child.tag)
                if lt in ("para", "simpara"):
                    parts.append(text(child))
                elif lt in ("itemizedlist", "orderedlist"):
                    sublists.append(child)
            head = " ".join(p for p in parts if p) or text(li)
            lines.append(f"{'  ' * indent}{bullet} {head}".rstrip())
            for sl in sublists:
                lines.extend(render_list(sl, indent + 1))
        return lines

    for child in list(node):
        lt = _local(child.tag)
        if lt == "title" and skip_first_title and not blocks:
            continue
        if lt in ("para", "simpara"):
            t = text(child)
            if t:
                blocks.append(t)
        elif lt in ("itemizedlist", "orderedlist"):
            blocks.append("\n".join(render_list(child, 0)))
        elif lt == "section":
            # Unterabschnitt (z.B. Gefährdungslage-Szenarien): Titel + Prosa
            sub = render_prose(child, skip_first_title=True)
            st = title_of(child)
            if sub:
                blocks.append((f"{st}\n{sub}" if st else sub))
            elif st:
                blocks.append(st)
    return "\n\n".join(b for b in blocks if b).strip()


def normalize_req_id(raw_id):
    """Quell-Tippfehler abfangen: fehlender Punkt vor 'A' (z.B. OPS.2.3A22)."""
    m = re.match(r"^([A-Z]{2,4}(?:\.\d+)+)(A\d+)$", raw_id)
    if m:
        return f"{m.group(1)}.{m.group(2)}"
    return raw_id


def build_control(req_section, stats):
    raw = title_of(req_section)
    m = REQ_TITLE_RE.match(raw)
    if not m:
        log_warn(f"Anforderungstitel nicht parsebar, übersprungen: {raw!r}")
        stats["skipped"] += 1
        return None
    raw_id, name, marker, role = m.group(1), m.group(2).strip(), m.group(3), m.group(4)
    cid = normalize_req_id(raw_id)
    if cid != raw_id:
        log_warn(f"ID normalisiert (Quell-Tippfehler): {raw_id} -> {cid}")
        stats["id_fixed"] += 1

    props = [
        {"name": "alt-identifier", "value": cid},
        {"name": "sec_level", "ns": SEC_LEVEL_NS, "value": MARKER_TO_LEVEL[marker]},
    ]
    if role:
        props.append({"name": "role", "value": role.strip()})

    statement = render_prose(req_section, skip_first_title=True)
    is_entfallen = "ENTFALLEN" in name.upper() or statement.strip() == "Diese Anforderung ist entfallen."
    if is_entfallen:
        props.append({"name": "status", "value": "entfallen"})
        stats["entfallen"] += 1

    control = {
        "id": cid,
        "class": "IT-Grundschutz-Kompendium-2023",
        "title": name,
        "props": props,
        "parts": [{
            "id": f"{cid}_stm",
            "name": "statement",
            "prose": statement,
        }],
    }
    stats["controls"] += 1
    stats["by_level"][marker] += 1
    return control


def build_baustein_group(b_section, stats):
    raw = title_of(b_section)
    m = BAUSTEIN_RE.match(raw)
    if not m:
        return None
    bid, bname = m.group(1), m.group(2).strip()

    parts = []
    besch = find_subsection(b_section, lambda t: t == "Beschreibung")
    if besch is not None:
        prose = render_prose(besch, skip_first_title=True)
        if prose:
            parts.append({"id": f"{bid}_overview", "name": "overview", "prose": prose})
    gef = find_subsection(b_section, lambda t: t == "Gefährdungslage")
    if gef is not None:
        prose = render_prose(gef, skip_first_title=True)
        if prose:
            parts.append({"id": f"{bid}_guidance", "name": "guidance", "prose": prose})

    controls = []
    anf = find_subsection(b_section, lambda t: t == "Anforderungen")
    if anf is None:
        log_warn(f"Baustein {bid} ohne 'Anforderungen'-Abschnitt.")
    else:
        for quali in subsections(anf):
            qt = title_of(quali)
            if qt not in QUALI_TITLES:
                log_warn(f"Unerwarteter Quali-Abschnitt in {bid}: {qt!r}")
            for req in subsections(quali):
                c = build_control(req, stats)
                if c is not None:
                    controls.append(c)

    group = {"id": bid, "class": "baustein", "title": bname}
    if parts:
        group["parts"] = parts
    group["controls"] = controls
    stats["bausteine"] += 1
    return group


def build_layer_group(chapter, stats):
    raw = title_of(chapter)
    m = LAYER_RE.match(raw)
    if not m:
        return None
    code, name = m.group(1), m.group(2).strip()
    groups = []
    for b in subsections(chapter):
        bg = build_baustein_group(b, stats)
        if bg is not None:
            groups.append(bg)
    stats["layers"] += 1
    return {"id": code, "class": "schicht", "title": name, "groups": groups}


def build_threats_group(chapter, stats):
    controls = []
    for sec in subsections(chapter):
        raw = title_of(sec)
        m = THREAT_RE.match(raw)
        if not m:
            log_warn(f"Gefährdungstitel nicht parsebar: {raw!r}")
            continue
        tid = re.sub(r"\s+", " ", m.group(1)).strip()
        tname = m.group(2).strip()
        prose = render_prose(sec, skip_first_title=True)
        controls.append({
            "id": tid,
            "class": "elementare-gefaehrdung",
            "title": tname,
            "props": [{"name": "alt-identifier", "value": tid}],
            "parts": [{"id": f"{tid.replace(' ', '_')}_stm", "name": "statement", "prose": prose}],
        })
        stats["threats"] += 1
    return {
        "id": "G 0",
        "class": "elementare-gefaehrdungen",
        "title": "Elementare Gefährdungen",
        "controls": controls,
    }


def build_catalog(root, source_url, src_sha256):
    stats = {
        "layers": 0, "bausteine": 0, "controls": 0, "threats": 0,
        "entfallen": 0, "skipped": 0, "id_fixed": 0,
        "by_level": {"B": 0, "S": 0, "H": 0},
    }
    groups = []
    threats_group = None
    for chapter in root.findall("db:chapter", NS):
        ct = title_of(chapter)
        if ct == GEF_CHAPTER:
            threats_group = build_threats_group(chapter, stats)
        elif LAYER_RE.match(ct):
            lg = build_layer_group(chapter, stats)
            if lg is not None:
                groups.append(lg)
    if threats_group is not None:
        groups.append(threats_group)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    catalog = {
        "catalog": {
            "uuid": str(_stable_uuid(src_sha256)),
            "metadata": {
                "title": "IT-Grundschutz-Kompendium Edition 2023",
                "last-modified": now,
                "version": "Edition 2023",
                "oscal-version": OSCAL_VERSION,
                "props": [
                    {"name": "keywords", "value": "IT-Grundschutz, BSI, Edition 2023"},
                ],
                "links": [
                    {"href": source_url, "rel": "canonical",
                     "text": "BSI IT-Grundschutz-Kompendium Edition 2023 (DocBook-XML)"},
                ],
                "parties": [{
                    "uuid": "9c1fd645-6673-459e-b26e-70d28cdc0bc3",
                    "type": "organization",
                    "name": "Bundesamt für Sicherheit in der Informationstechnik",
                    "email-addresses": ["service-center@bsi.bund.de"],
                }],
                "remarks": ("Adaptiert aus der DocBook-XML-Fassung des "
                            "IT-Grundschutz-Kompendiums Edition 2023 (BSI). "
                            "Lizenz CC BY-SA 4.0."),
            },
            "groups": groups,
            "back-matter": {
                "resources": [{
                    "uuid": str(_stable_uuid(source_url)),
                    "title": "BSI IT-Grundschutz-Kompendium Edition 2023 (DocBook-XML)",
                    "rlinks": [{
                        "href": source_url,
                        "hashes": [{"algorithm": "SHA-256", "value": src_sha256}],
                    }],
                }],
            },
        }
    }
    return catalog, stats


def _stable_uuid(seed):
    import uuid
    return uuid.uuid5(uuid.NAMESPACE_URL, f"it-grundschutz-2023:{seed}")


def load_xml(file_path, url):
    if file_path:
        if not os.path.exists(file_path):
            die(f"Datei nicht gefunden: {file_path}")
        log_info(f"Lese lokale XML: {file_path}")
        with open(file_path, "rb") as f:
            raw = f.read()
    else:
        log_info(f"Lade XML von: {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read()
        except Exception as exc:  # noqa: BLE001
            die(f"Download fehlgeschlagen: {exc}")
    sha = hashlib.sha256(raw).hexdigest()
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        die(f"XML nicht parsebar: {exc}")
    if _local(root.tag) != "book":
        die(f"Unerwartetes Wurzelelement: {_local(root.tag)} (erwartet: book)")
    return root, raw, sha


def write_manifest(dest_dir, catalog, stats, source_url, src_sha256, catalog_sha256):
    manifest = {
        "edition": "edition-2023",
        "quelle_url": source_url,
        "lizenz": LICENSE_ID,
        "abgerufen_am": datetime.datetime.now(datetime.timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dateien": [{
            "name": "kompendium",
            "datei": "catalog.json",
            "typ": "catalog",
            "raw_url": source_url,
            "quelle_sha256": src_sha256,
            "sha256": catalog_sha256,
            "titel": catalog["catalog"]["metadata"]["title"],
            "last_modified": "Edition 2023",
            "anzahl_anforderungen": stats["controls"],
            "anzahl_bausteine": stats["bausteine"],
            "anzahl_schichten": stats["layers"],
            "anzahl_gefaehrdungen": stats["threats"],
        }],
    }
    path = os.path.join(dest_dir, "manifest.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", help="lokale XML-Datei statt Download")
    ap.add_argument("--url", default=DEFAULT_URL, help="Download-URL (Default: BSI)")
    ap.add_argument("--corpus-dir",
                    default=os.environ.get("GS_CORPUS_DIR",
                                           os.path.expanduser("~/.local/share/it-grundschutz/corpus")),
                    help="Korpus-Wurzel (Default: $GS_CORPUS_DIR)")
    args = ap.parse_args()

    root, _raw, src_sha = load_xml(args.file, args.url)
    source_url = args.file if args.file else args.url

    catalog, stats = build_catalog(root, source_url, src_sha)

    dest_dir = os.path.join(args.corpus_dir, "edition-2023")
    os.makedirs(dest_dir, exist_ok=True)
    catalog_path = os.path.join(dest_dir, "catalog.json")
    payload = json.dumps(catalog, ensure_ascii=False, indent=2)
    with open(catalog_path, "w", encoding="utf-8") as f:
        f.write(payload)
    catalog_sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    manifest_path = write_manifest(dest_dir, catalog, stats, source_url, src_sha, catalog_sha)

    log_ok(f"Katalog geschrieben: {catalog_path}")
    log_ok(f"Manifest geschrieben: {manifest_path}")
    log_info(f"Schichten:       {stats['layers']}")
    log_info(f"Bausteine:       {stats['bausteine']}")
    log_info(f"Anforderungen:   {stats['controls']}  "
             f"(Basis={stats['by_level']['B']}, "
             f"Standard={stats['by_level']['S']}, "
             f"erhöht={stats['by_level']['H']})")
    log_info(f"davon entfallen: {stats['entfallen']}")
    log_info(f"Elementare Gefährdungen: {stats['threats']}")
    if stats["id_fixed"]:
        log_warn(f"normalisierte IDs (Quell-Tippfehler): {stats['id_fixed']}")
    if stats["skipped"]:
        log_warn(f"übersprungene (nicht parsebare) Anforderungen: {stats['skipped']}")
    log_info("Hinweis: Der formale Baustein<->Gefährdung-Kreuzbezug "
             "(Kreuzreferenztabellen) ist NICHT Teil des Kompendium-XML und "
             "daher bewusst ausgelassen — siehe SKILL/README.")


if __name__ == "__main__":
    main()
