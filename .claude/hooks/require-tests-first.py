#!/usr/bin/env python3
"""PreToolUse hook: a core module cannot land before its test.

Hard rule from CLAUDE.md: tests before core modules. This hook refuses to write a guarded
source module until a test file for it exists under tests/ and contains at least one test
function. Guarded: every .py file under src/dico_nli/, at any depth. Exempt: __init__.py
and conftest.py. Test files themselves are never guarded, so the only order that works is
the intended one: write the failing test, then the module.

Write and Edit are checked by file_path. Bash is checked for redirect, tee, cp, mv, and
install targets under the guarded paths ($CLAUDE_PROJECT_DIR and Git Bash /d/ paths are
resolved). A Python heredoc that opens a guarded path for writing is not caught; author
source through Write and Edit.

Matching: the module stem's underscore tokens must appear, in order, in the test file's
name. tokenizer.py is satisfied by tests/unit/test_tokenizer.py or
tests/integration/test_tokenizer_roundtrip.py; base.py is not satisfied by
tests/unit/test_database.py. The test file must contain `def test_`.

Exit 2 blocks the tool call and shows stderr to Claude. Exit 0 allows it.
"""

import glob
import json
import os
import re
import sys

GUARDED = re.compile(r"^src/dico_nli/.+\.py$")
EXEMPT = {"__init__.py", "conftest.py"}
REDIRECT_TARGET = re.compile(r"(?:^|[^2&<])>>?\s*(\S+)")
FILE_COMMAND_ARGS = re.compile(r"\b(?:tee|cp|mv|install)\b([^;&|\n]*)")
TEST_FUNCTION = re.compile(r"^\s*(?:async\s+)?def\s+test_\w+\s*\(", re.MULTILINE)


def normalize(path, root):
    """Repo-relative forward-slash path, or the input unchanged when it is outside root."""
    path = path.strip().strip("\"'")
    path = path.replace("${CLAUDE_PROJECT_DIR}", root).replace("$CLAUDE_PROJECT_DIR", root)
    path = re.sub(r"^/([A-Za-z])/", lambda m: m.group(1).upper() + ":/", path)  # Git Bash /d/...
    path = path.replace("\\", "/")
    if not (os.path.isabs(path) or re.match(r"^[A-Za-z]:/", path)):
        path = os.path.join(root, path)
    try:
        return os.path.relpath(os.path.abspath(path), os.path.abspath(root)).replace(os.sep, "/")
    except ValueError:  # different drive on Windows
        return path


def tokens(name):
    return [t for t in name.split("_") if t]


def contains_in_order(haystack, needle):
    n = len(needle)
    return any(haystack[i:i + n] == needle for i in range(len(haystack) - n + 1))


def tests_for(stem, root):
    want = tokens(stem)
    found = []
    for path in glob.glob(os.path.join(root, "tests", "**", "test_*.py"), recursive=True):
        if not contains_in_order(tokens(os.path.basename(path)[:-3]), want):
            continue
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if TEST_FUNCTION.search(text):
            found.append(os.path.relpath(path, root).replace(os.sep, "/"))
    return found


def targets(tool_name, tool_input, root):
    if tool_name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        return [normalize(path, root)] if path else []
    if tool_name == "Bash":
        cmd = tool_input.get("command") or ""
        candidates = [m.group(1) for m in REDIRECT_TARGET.finditer(cmd)]
        for m in FILE_COMMAND_ARGS.finditer(cmd):
            candidates.extend(m.group(1).split())
        return [normalize(c, root) for c in candidates if c and not c.startswith(("&", "-"))]
    return []


def find_violation(tool_name, tool_input, root):
    """Return (module, stem) for the first guarded target with no test, else None."""
    for rel in targets(tool_name, tool_input, root):
        if not GUARDED.match(rel):
            continue
        base = os.path.basename(rel)
        if base in EXEMPT:
            continue
        stem = base[:-3]
        if tests_for(stem, root):
            continue
        return rel, stem
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception as exc:  # fail closed
        sys.stderr.write(f"require-tests-first: could not parse hook input ({exc}); blocking by default.\n")
        return 2
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    )
    hit = find_violation(data.get("tool_name", ""), data.get("tool_input") or {}, root)
    if not hit:
        return 0
    rel, stem = hit
    sys.stderr.write(
        f"BLOCKED by .claude/hooks/require-tests-first.py: {rel} has no test yet.\n"
        "Tests come before core modules (CLAUDE.md). Create "
        f"tests/<unit|integration|regression>/test_{stem}.py with at least one test "
        "that fails against the behavior you are about to write, then write the module. "
        "Tiers and naming: .claude/reference/testing.md.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
