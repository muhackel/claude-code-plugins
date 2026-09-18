import re, sys
src, dst = sys.argv[1], sys.argv[2]
out, drop, dropped = [], False, []
hdr = re.compile(r'^\s*\[([^\[\]]+)\]\s*(#.*)?$')
for line in open(src, encoding="utf-8"):
    m = hdr.match(line)
    if m:
        name = m.group(1).strip()
        drop = name == "marketplaces.muhackel-plugins" or bool(re.fullmatch(r'plugins\."[^"]+@muhackel-plugins"', name))
        if drop:
            dropped.append(name)
    if not drop:
        out.append(line)
while out and out[-1].strip() == "":
    out.pop()
open(dst, "w", encoding="utf-8").write("".join(out) + "\n")
print("entfernt:", *dropped, sep="\n  ")
