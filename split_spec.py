#!/usr/bin/env python3
"""
Split the Aegis master blueprint into one file per Part so an AI agent can load only what a
phase needs (keeps the context window small and focused).

Usage:  python3 split_spec.py Aegis_Browser_MASTER_Blueprint_A-to-Z.md docs/spec
Creates docs/spec/part-01-....md ... plus docs/spec/INDEX.md
"""
import re, sys, pathlib

src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
text = src.read_text(encoding="utf-8")

# Part headings look like: "# Part 7. Protection services"
matches = list(re.finditer(r"^# Part (\d+)\. (.+)$", text, flags=re.M))
head = text[: matches[0].start()].rstrip() + "\n"
(out / "part-00-front-matter.md").write_text(head, encoding="utf-8")
index = ["# Spec index\n", "| File | Title |", "|---|---|", "| part-00-front-matter.md | Title, status, contents |"]

for i, m in enumerate(matches):
    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
    body = text[m.start():end].rstrip()
    body = re.sub(r"\n---\s*$", "", body).rstrip() + "\n"       # drop trailing separator
    slug = re.sub(r"[^a-z0-9]+", "-", m.group(2).lower()).strip("-")[:48]
    name = f"part-{int(m.group(1)):02d}-{slug}.md"
    (out / name).write_text(body, encoding="utf-8")
    index.append(f"| {name} | Part {m.group(1)}: {m.group(2)} ({len(body.splitlines())} lines) |")

(out / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
print(f"wrote {len(matches) + 1} files to {out}")
