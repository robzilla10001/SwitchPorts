import os, re, sys

FILE = "README.md"  # change to the file holding your tables
body = os.environ["ISSUE_BODY"].replace("\r\n", "\n")

# Each form field arrives as "### <label>\n\n<answer>".
fields = {}
for m in re.finditer(r"^### (.+?)\n\n(.*?)(?=\n### |\Z)", body, re.S | re.M):
    fields[m.group(1).strip()] = m.group(2).strip()

def field(*names):
    for n in names:
        if n in fields:
            return fields[n]
    sys.exit(f"Missing form field {names[0]!r}. Fields found: {list(fields)}")

section = field("System")

# The game dropdown is labelled "<System> - which game?" (or "- which title?").
game_key = next((k for k in fields if k.startswith(f"{section} - which ")), None)
if game_key is None:
    sys.exit(f"No game dropdown found for '{section}'. Fields found: {list(fields)}")
game = fields[game_key]
if not game or game == "_No response_":
    sys.exit(f"'{game_key}' was left empty -- pick the game for {section}.")
game = game.replace("🟢", "").strip()

status = field("Status?", "Status").split(" = ")[0].strip()  # "🟩 = Completable" -> "🟩"

def clean(s):
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)   # links -> text
    s = re.sub(r"<[^>]+>|[*_`~]", "", s)              # HTML, bold/italic/code
    return s.replace("🟢", "").replace("️", "").strip().lower()

HEADING_RE = re.compile(r"^#{1,6}\s")

lines = open(FILE, encoding="utf-8").read().split("\n")

# Find where the section starts: the <a id="..."> anchor from the generator's
# CATEGORIES list if there is one, otherwise a "### <System>" heading.
start = None
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from generate_status_template import CATEGORIES, find_anchor_line
    anchor = next((c["anchor"] for c in CATEGORIES if c["label"] == section), None)
    if anchor:
        start = find_anchor_line(lines, anchor)
except ImportError:
    pass
if start is None:
    start = next((i for i, l in enumerate(lines) if l.strip() == f"### {section}"), None)
if start is None:
    sys.exit(f"Couldn't find the '{section}' section in {FILE}")

done = False
headings_seen = 1 if HEADING_RE.match(lines[start]) else 0
for i in range(start + 1, len(lines)):
    line = lines[i]
    if HEADING_RE.match(line):
        headings_seen += 1
        if headings_seen > 1:          # reached the next section
            break
        continue
    if line.strip().startswith("|"):
        parts = re.split(r"(?<!\\)\|", line.strip())  # ignore escaped \|
        cells = parts[1:-1]
        if cells and clean(cells[0]) == clean(game):
            cells[-1] = f" {status} "
            lines[i] = "|" + "|".join(cells) + "|"
            done = True
            break

if not done:
    sys.exit(f"Couldn't find '{game}' under '{section}'")
open(FILE, "w", encoding="utf-8").write("\n".join(lines))
print(f"Set {section} / {game} -> {status}")
