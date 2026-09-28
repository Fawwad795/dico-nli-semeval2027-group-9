#!/usr/bin/env python3
"""PreToolUse hook: work happens on a named branch, never on main.

Hard rule from CLAUDE.md: every distinct piece of work lives on its own branch named
<area>/<topic> and reaches main through a pull request that a teammate reviews. This hook
refuses Write, Edit, and Bash writes to repository files while the checkout is on main or
master, is in detached HEAD, or is on a branch whose name does not follow the pattern.

Scratch is exempt: .tmp/, .venv/, and anything outside the repository. Reads are never
checked, and a directory that is not a git repository is not checked either.

The branch is read from .git/HEAD directly (following a worktree's gitdir file when .git
is a file), so the hook spawns no subprocess.

Exit 2 blocks the tool call and shows stderr to Claude. Exit 0 allows it.
"""

import json
import os
import re
import sys

PROTECTED = {"main", "master"}
BRANCH_PATTERN = re.compile(r"^[a-z0-9]+/[a-z0-9][a-z0-9-]*$")
SUGGESTED_AREAS = "a1, a2, a3, harness, fix, docs, exp"
EXEMPT_PREFIXES = (".tmp/", ".venv/")
REDIRECT_TARGET = re.compile(r"(?:^|[^2&<])>>?\s*(\S+)")
FILE_COMMAND_ARGS = re.compile(r"\b(?:tee|cp|mv|install|rm|rmdir|mkdir|touch)\b([^;&|\n]*)")


def normalize(path, root):
    """Repo-relative forward-slash path; starts with '..' when outside root."""
    path = path.strip().strip("\"'")
    path = path.replace("${CLAUDE_PROJECT_DIR}", root).replace("$CLAUDE_PROJECT_DIR", root)
    path = re.sub(r"^/([A-Za-z])/", lambda m: m.group(1).upper() + ":/", path)  # Git Bash /d/...
    path = path.replace("\\", "/")
    if not (os.path.isabs(path) or re.match(r"^[A-Za-z]:/", path)):
        path = os.path.join(root, path)
    try:
        return os.path.relpath(os.path.abspath(path), os.path.abspath(root)).replace(os.sep, "/")
    except ValueError:  # different drive on Windows
        return "../" + path


def current_branch(root):
    """('branch', name) | ('detached', None) | ('no-repo', None)."""
    git = os.path.join(root, ".git")
    gitdir = git
    if os.path.isfile(git):
        try:
            text = open(git, encoding="utf-8").read().strip()
        except OSError:
            return ("no-repo", None)
        if text.startswith("gitdir:"):
            gitdir = text.split(":", 1)[1].strip()
            if not os.path.isabs(gitdir):
                gitdir = os.path.join(root, gitdir)
    try:
        head = open(os.path.join(gitdir, "HEAD"), encoding="utf-8").read().strip()
    except OSError:
        return ("no-repo", None)
    prefix = "ref: refs/heads/"
    if head.startswith(prefix):
        return ("branch", head[len(prefix):])
    return ("detached", None)


def repo_targets(tool_name, tool_input, root):
    """Repository paths this call would write, excluding scratch and out-of-tree paths."""
    if tool_name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        raw = [path] if path else []
    elif tool_name == "Bash":
        cmd = tool_input.get("command") or ""
        raw = [m.group(1) for m in REDIRECT_TARGET.finditer(cmd)]
        for m in FILE_COMMAND_ARGS.finditer(cmd):
            raw.extend(m.group(1).split())
        raw = [c for c in raw if c and not c.startswith(("&", "-"))]
    else:
        return []
    targets = []
    for candidate in raw:
        rel = normalize(candidate, root)
        if rel.startswith("..") or rel.startswith(EXEMPT_PREFIXES) or rel in (".tmp", ".venv"):
            continue
        targets.append(rel)
    return targets


def find_violation(tool_name, tool_input, root):
    if not repo_targets(tool_name, tool_input, root):
        return None
    kind, name = current_branch(root)
    if kind == "no-repo":
        return None
    if kind == "detached":
        return "a detached HEAD"
    if name in PROTECTED:
        return f"branch '{name}'"
    if not BRANCH_PATTERN.match(name):
        return f"branch '{name}', which does not follow <area>/<topic>"
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception as exc:  # fail closed
        sys.stderr.write(f"require-feature-branch: could not parse hook input ({exc}); blocking by default.\n")
        return 2
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    )
    hit = find_violation(data.get("tool_name", ""), data.get("tool_input") or {}, root)
    if not hit:
        return 0
    sys.stderr.write(
        f"BLOCKED by .claude/hooks/require-feature-branch.py: the checkout is on {hit}.\n"
        "Work happens on a branch named <area>/<topic> (areas: " + SUGGESTED_AREAS + "), one "
        "distinct part per branch, merged to main through a reviewed pull request. Ask the "
        "user to run:  git checkout -b <area>/<topic>   and retry. Scratch writes under .tmp/ "
        "are always allowed. See the Git section of CLAUDE.md.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
