#!/usr/bin/env python3
"""
Regenerate .github/ISSUE_TEMPLATE/update-status.yml from the tables in README.md.

For each category below, the script finds the README section with that
anchor (e.g. #emu), reads the first table after it, takes every value in
the given column, and turns them into a dropdown in update status form.

Run from the repo root:  python3 .github/scripts/generate_status_template.py
"""
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# EDIT THIS: one entry per category in your README.
#   label  = text shown in the first dropdown
#   anchor = the #anchor used in your README links (without the #)
#   column = the table column to pull names from
# ---------------------------------------------------------------------------
CATEGORIES = [
    {"label": "Emulators", "anchor": "emu", "column": "Title"},
    {"label": "Android 32bit", "anchor": "and32", "column": "Game"},
    {"label": "Android 64bit", "anchor": "and64", "column": "Game"},
    {"label": "Arcade", "anchor": "arc", "column": "Game"},
    {"label": "Microsoft Xbox", "anchor": "xbox", "column": "Game"},
    {"label": "Microsoft Xbox 360", "anchor": "x360", "column": "Game"},
    {"label": "NEC PC Engine (TurboGrafx-16)", "anchor": "pce", "column": "Game"},
    {"label": "Nintendo DS", "anchor": "nds", "column": "Game"},
    {"label": "Nintendo 3DS", "anchor": "3ds", "column": "Game"},
    {"label": "Nintendo 64", "anchor": "n64", "column": "Game"},
    {"label": "Nintendo Gameboy", "anchor": "gb", "column": "Game"},
    {"label": "Nintendo Gameboy Advance", "anchor": "gba", "column": "Game"},
    {"label": "Nintendo Gameboy Color", "anchor": "gbc", "column": "Game"},
    {"label": "Nintendo GameCube", "anchor": "ngc", "column": "Game"},
    {"label": "Super Nintendo Entertainment System", "anchor": "snes", "column": "Game"},
    {"label": "Nintendo Wii", "anchor": "wii", "column": "Game"},
    {"label": "Nintendo Wii U", "anchor": "wiiu", "column": "Game"},
    {"label": "PC", "anchor": "pc", "column": "Game"},
    {"label": "Sega Dreamcast", "anchor": "dc", "column": "Game"},
    {"label": "Sega Genesis (32x contained here also)", "anchor": "gen", "column": "Game"},
    {"label": "Sony Playstation", "anchor": "psx", "column": "Game"},
    {"label": "Sony Playstation 2", "anchor": "ps2", "column": "Game"},
    {"label": "Sony Playstation 4", "anchor": "ps4", "column": "Game"},
    {"label": "Sony Playstation Portable", "anchor": "psp", "column": "Game"},
    {"label": "Sony Playstation Vita", "anchor": "psv", "column": "Game"},
]

README = Path("README.md")
OUTPUT = Path(".github/ISSUE_TEMPLATE/update-status.yml")

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def github_slug(text: str) -> str:
    """Approximate the anchor GitHub generates for a heading."""
    text = re.sub(r"<[^>]+>", "", text)              # drop inline HTML
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links -> text
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)             # drop punctuation
    return text.replace(" ", "-")


def find_anchor_line(lines, anchor):
    """Line index of an explicit <a id/name="anchor"> or a heading with that slug."""
    explicit = re.compile(r"""(?:id|name)\s*=\s*["']%s["']""" % re.escape(anchor))
    for i, line in enumerate(lines):
        if explicit.search(line):
            return i
        m = HEADING_RE.match(line)
        if m and github_slug(m.group(2)) == anchor:
            return i
    return None


def split_row(line):
    """Split a markdown table row on unescaped pipes."""
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)]


# Markers to remove from the start of a name (add more if needed).
STRIP_PREFIXES = ["🟢"]


def clean_cell(cell):
    """Strip markdown formatting so only the plain name is left."""
    cell = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", cell)        # images
    cell = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cell)    # links
    cell = re.sub(r"<[^>]+>", "", cell)                     # HTML tags
    cell = re.sub(r"[*_`~]", "", cell)                      # bold/italic/code
    cell = re.sub(r"\s+", " ", cell).strip()
    stripped = True
    while stripped:                                         # leading markers
        stripped = False
        for p in STRIP_PREFIXES:
            if cell.startswith(p):
                cell = cell[len(p):].lstrip("\ufe0f ").strip()
                stripped = True
    return cell


# The |---|---| row under a table's headers (dashes, colons, pipes, spaces).
SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-*:?\s*)*\|?\s*$")

# Invisible characters that sometimes sneak into copied/pasted markdown.
INVISIBLE = {ord(c): None for c in "\ufeff\u200b\u200c\u200d\u2060"}
INVISIBLE[0x00A0] = " "   # non-breaking space -> normal space


def read_column(lines, anchor, column):
    lines = [l.translate(INVISIBLE) for l in lines]
    start = find_anchor_line(lines, anchor)
    if start is None:
        sys.exit(f"ERROR: could not find #{anchor} in {README}")

    # Walk forward to the first table's |---| separator row, giving up if we
    # reach another section. The header row is the line just above it.
    i = start + 1
    headings_seen = 0 if HEADING_RE.match(lines[start]) else -1
    while i < len(lines) and not (
        SEPARATOR_RE.match(lines[i]) and "|" in lines[i] + lines[i - 1]
    ):
        if HEADING_RE.match(lines[i]):
            headings_seen += 1
            if headings_seen > 0:
                sys.exit(f"ERROR: no table found under #{anchor}")
        i += 1
    if i >= len(lines):
        sys.exit(f"ERROR: no table found under #{anchor}")

    header = [clean_cell(c) for c in split_row(lines[i - 1])]
    try:
        col = [h.lower() for h in header].index(column.lower())
    except ValueError:
        sys.exit(f"ERROR: table under #{anchor} has no '{column}' column "
                 f"(columns: {', '.join(header)})")

    values, seen = [], set()
    for line in lines[i + 1:]:               # rows after the |---| line
        if not line.strip() or "|" not in line or HEADING_RE.match(line):
            break
        cells = split_row(line)
        if col < len(cells):
            value = clean_cell(cells[col])
            if value and value not in seen:
                seen.add(value)
                values.append(value)
    if not values:
        sys.exit(f"ERROR: '{column}' column under #{anchor} is empty")
    return values

def q(s):
    """Quote a string safely for YAML (JSON strings are valid YAML)."""
    return json.dumps(s, ensure_ascii=False)


def build_yaml(sections):
    out = [
        "# AUTO-GENERATED from README.md by .github/scripts/generate_status_template.py",
        "# Do not edit by hand -- edit the script or the README instead.",
        'name: "⁉️ Status"',
        "description: Post an update to a game status",
        'title: "[Status]: "',
        'labels: ["Status Update"]',
        "body:",
        "  - type: markdown",
        "    attributes:",
        "      value: Thanks for reporting! Pick a system, then pick the game from that system's list.",
        "  - type: dropdown",
        "    id: system",
        "    attributes:",
        "      label: System",
        "      options:",
    ]
    out += [f"        - {q(c['label'])}" for c, _ in sections]
    out += ["    validations:", "      required: true"]

    for c, values in sections:
        safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", c["anchor"])
        out += [
            "  - type: dropdown",
            f"    id: item_{safe_id}",
            "    attributes:",
            f"      label: {q(c['label'] + ' - which ' + c['column'].lower() + '?')}",
            f"      description: {q('Only fill this in if you chose ' + c['label'] + ' above.')}",
            "      options:",
        ]
        out += [f"        - {q(v)}" for v in values]

    out += [
        "  - type: dropdown",
        "    id: status",
        "    attributes:",
        "      label: Status?",
        "      description: Project Progress",
        "      options:",
        f"        - {q('⬛️ = Does not boot')}",
        f"        - {q('🟥 = Game boots to title')}",
        f"        - {q('🟧 = Boots into game, unplayable')}",
        f"        - {q('🟨 = Playable')}",
        f"        - {q('🟩 = Completable')}",
        f"        - {q('✳️ = Feature complete; only sporadic bug fixes, enhancements and QOL improvements remain.')}",
        "    validations:",
        "      required: true",
    ]
    return "\n".join(out) + "\n"


def main():
    lines = README.read_text(encoding="utf-8").splitlines()
    sections = [(c, read_column(lines, c["anchor"], c["column"])) for c in CATEGORIES]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(build_yaml(sections), encoding="utf-8")
    for c, values in sections:
        print(f"#{c['anchor']}: {len(values)} items")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
