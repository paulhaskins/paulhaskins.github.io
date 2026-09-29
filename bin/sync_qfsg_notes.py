#!/usr/bin/env python3
"""Mirror t.pdf files from ~/tp/qfsg into the password-gated Notes page.

Run weekly via cron. Finds every file literally named t.pdf under
~/tp/qfsg, copies new/changed ones into assets/pdf/notes/qfsg/, regenerates
the auto-managed qfsg block in _pages/notes.md, and commits + pushes if
anything changed. No-ops (and pushes nothing) when there's nothing new.
"""

import filecmp
import os
import shutil
import subprocess
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.expanduser("~/tp/qfsg")
DEST = os.path.join(REPO, "assets", "pdf", "notes", "qfsg")
NOTES_PAGE = os.path.join(REPO, "_pages", "notes.md")
START_MARKER = "  <!-- QFSG_AUTO_START -->"
END_MARKER = "  <!-- QFSG_AUTO_END -->"


def find_t_pdfs(src):
    matches = []
    for dirpath, _dirnames, filenames in os.walk(src):
        for name in filenames:
            if name.lower() == "t.pdf":
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, src)
                matches.append(rel)
    return sorted(matches)


def sync_files(rels):
    changed = False
    for rel in rels:
        src_path = os.path.join(SRC, rel)
        dest_path = os.path.join(DEST, rel)
        if os.path.exists(dest_path) and filecmp.cmp(src_path, dest_path, shallow=False):
            continue
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(src_path, dest_path)
        changed = True
    return changed


def label_for(rel):
    # rel looks like "<subdir...>/t.pdf"; the "t" is uninformative, so the
    # containing directory is the label.
    parts = rel.split(os.sep)[:-1]
    return "/".join(parts) if parts else "qfsg"


def build_html(rels):
    labels = [label_for(rel) for rel in rels]
    counts = Counter(labels)
    seen = Counter()
    lines = [START_MARKER]
    if rels:
        lines.append('  <div class="notes-group">')
        lines.append("    <h2>qfsg/</h2>")
        lines.append('    <ul class="notes-list">')
        for rel, lbl in zip(rels, labels):
            if counts[lbl] > 1:
                seen[lbl] += 1
                lbl = f"{lbl} ({seen[lbl]})"
            href = "/assets/pdf/notes/qfsg/" + rel.replace(os.sep, "/")
            lines.append(
                f"      <li><a href=\"{{{{ '{href}' | relative_url }}}}\" "
                f'target="_blank" rel="noopener">{lbl}</a></li>'
            )
        lines.append("    </ul>")
        lines.append("  </div>")
    lines.append(END_MARKER)
    return "\n".join(lines)


def update_notes_page(new_block):
    with open(NOTES_PAGE) as f:
        content = f.read()
    start = content.index(START_MARKER)
    end = content.index(END_MARKER) + len(END_MARKER)
    updated = content[:start] + new_block + content[end:]
    if updated == content:
        return False
    with open(NOTES_PAGE, "w") as f:
        f.write(updated)
    return True


def run(cmd):
    subprocess.run(cmd, cwd=REPO, check=True)


def git_has_changes():
    result = subprocess.run(
        ["git", "status", "--porcelain", "assets/pdf/notes/qfsg", "_pages/notes.md"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(result.stdout.strip())


def main():
    if not os.path.isdir(SRC):
        print(f"qfsg source folder not found: {SRC}", file=sys.stderr)
        return 0

    rels = find_t_pdfs(SRC)
    sync_files(rels)
    update_notes_page(build_html(rels))

    if not git_has_changes():
        print("No new or changed t.pdf files under tp/qfsg; nothing to do.")
        return 0

    run(["git", "add", "assets/pdf/notes/qfsg", "_pages/notes.md"])
    run(
        [
            "git",
            "commit",
            "-m",
            "Sync qfsg t.pdf notes\n\nAutomated weekly sync from tp/qfsg (bin/sync_qfsg_notes.py).",
        ]
    )
    run(["git", "push"])
    print(f"Synced {len(rels)} file(s) from tp/qfsg and pushed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
