import os, re, sys

FILE = "README.md"  # change to the file holding your tables
body = os.environ["ISSUE_BODY"].replace("\r\n", "\n")

fields = {}
for m in re.finditer(r"^### (.+?)\n\n(.*?)(?=\n### |\Z)", body, re.S | re.M):
    fields[m.group(1).strip()] = m.group(2).strip()

section = fields["System"]
game = fields["Game"].replace("🟢", "").strip()
status = fields["Status"].split(" = ")[0].strip()  # "🟩 = Completable" -> "🟩"

def clean(s):
    return s.replace("🟢", "").strip().lower()

lines = open(FILE, encoding="utf-8").read().split("\n")
in_section, done = False, False
for i, line in enumerate(lines):
    if line.strip() == f"### {section}":
        in_section = True
        continue
    if in_section and line.startswith("#"):
        break
    if in_section and line.strip().startswith("|"):
        parts = re.split(r"(?<!\\)\|", line.strip())  # ignore escaped \|
        cells = parts[1:-1]
        if cells and clean(cells[0]) == clean(game):
            cells[-1] = f" {status} "
            lines[i] = "|" + "|".join(cells) + "|"
            done = True
            break

if not done:
    sys.exit(f"Couldn't find '{game}' under '### {section}'")
open(FILE, "w", encoding="utf-8").write("\n".join(lines))
