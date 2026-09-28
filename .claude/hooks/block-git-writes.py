#!/usr/bin/env python3
"""PreToolUse hook: block git and gh commands that write.

Hard rule for this repository: Claude never commits, pushes, merges, or otherwise
changes git state. The user runs those commands. This hook makes an accidental
attempt fail instead of succeed.

It scans the whole Bash command string, not just its start, so compound forms
(`cd x && git commit`, `git -C path push`, `bash -c "git add ."`) are caught too.
Read-only git and gh commands pass. If the hook cannot parse its input it blocks,
because a silent fail-open would defeat the point.

Exit 2 blocks the tool call and shows stderr to Claude. Exit 0 allows it.
"""

import json
import re
import sys

# A `git` word that is a command, not part of a path like .git/ or a word like digit.
GIT_HEAD = (
    r"(?:^|[^\w.\-])(?:\S*/)?git(?:\.exe)?"
    r"(?:\s+(?:-C\s+\S+|-c\s+\S+|--git-dir(?:=\S+|\s+\S+)|--work-tree(?:=\S+|\s+\S+)"
    r"|--namespace(?:=\S+|\s+\S+)|--exec-path(?:=\S+)?|--no-pager|--paginate|-p|-P|--bare"
    r"|--no-optional-locks|--literal-pathspecs|--glob-pathspecs|--noglob-pathspecs"
    r"|--icase-pathspecs|--no-replace-objects|--no-advice))*"
    r"\s+"
)

# Always a write, whatever the arguments.
GIT_ALWAYS_BLOCK = {
    "add", "am", "apply", "checkout", "cherry-pick", "clean", "commit", "filter-branch",
    "filter-repo", "gc", "init", "merge", "mv", "prune", "pull", "push", "rebase",
    "replace", "reset", "restore", "revert", "rm", "switch", "update-ref",
}

# A write unless the arguments are one of the read-only shapes checked below.
GIT_CONDITIONAL = {
    "branch", "config", "notes", "reflog", "remote", "stash", "submodule",
    "symbolic-ref", "tag", "worktree",
}

GIT_SUB = re.compile(
    GIT_HEAD
    + r"(?P<sub>" + "|".join(sorted(GIT_ALWAYS_BLOCK | GIT_CONDITIONAL, key=len, reverse=True)) + r")"
    + r"(?=\s|$|[;&|)`'\"])"
)

# Cut the argument list at the next shell separator or closing quote.
ARG_END = re.compile(r"\s*(?:;|&&|\|\||\||\n|\)|`|\$\(|'|\")")

GH_HEAD = r"(?:^|[^\w.\-])(?:\S*/)?gh(?:\.exe)?\s+"
GH_BLOCK = [
    re.compile(GH_HEAD + p) for p in (
        r"pr\s+(?:create|merge|close|reopen|edit|comment|review|ready|lock|unlock|checkout|update-branch|revert)\b",
        r"issue\s+(?:create|close|reopen|edit|comment|delete|lock|unlock|transfer|pin|unpin|develop)\b",
        r"release\s+(?:create|delete|delete-asset|edit|upload)\b",
        r"repo\s+(?:create|delete|edit|fork|rename|archive|unarchive|sync|set-default)\b",
        r"repo\s+(?:deploy-key|autolink)\s+(?:add|create|delete)\b",
        r"workflow\s+(?:run|enable|disable)\b",
        r"run\s+(?:cancel|rerun|delete)\b",
        r"gist\s+(?:create|delete|edit|rename)\b",
        r"label\s+(?:create|delete|edit|clone)\b",
        r"(?:secret|variable)\s+(?:set|delete|remove)\b",
        r"(?:ssh-key|gpg-key)\s+(?:add|delete)\b",
        r"auth\s+(?:login|logout|refresh|setup-git|switch)\b",
        r"config\s+set\b",
        r"alias\s+(?:set|delete|import)\b",
        r"(?:extension|ext)\s+(?:install|remove|upgrade|create)\b",
        r"cache\s+delete\b",
        r"(?:codespace|cs)\s+(?:create|delete|edit|rebuild|stop|ssh|cp|jupyter|code)\b",
        r"project\s+(?:create|delete|edit|close|copy|link|unlink|mark-template|item-add|item-create|item-edit|item-delete|item-archive|field-create|field-delete)\b",
        r"api\b[^\n;&|]*(?:(?:-X|--method)[\s=]+(?:POST|PUT|PATCH|DELETE)\b|\s-f\s|\s-F\s|--field\b|--raw-field\b|--input\b)",
    )
]


def args_after(cmd, end):
    """Tokens between the subcommand and the next shell separator."""
    rest = ARG_END.split(cmd[end:], 1)[0]
    return rest.split()


def positionals(toks):
    return [t for t in toks if not t.startswith("-")]


def git_conditional_is_write(sub, toks):
    """Return True when a conditional subcommand is being used to write."""
    first = toks[0] if toks else ""
    if sub == "branch":
        write_flags = {"-d", "-D", "-m", "-M", "-c", "-C", "-f", "-u", "--delete", "--move",
                       "--copy", "--force", "--unset-upstream", "--edit-description",
                       "--track", "--no-track"}
        if any(t in write_flags or t.startswith("--set-upstream-to") for t in toks):
            return True
        list_flags = {"-l", "--list", "--contains", "--no-contains", "--merged",
                      "--no-merged", "--points-at", "--show-current"}
        return bool(positionals(toks)) and not any(t in list_flags for t in toks)
    if sub == "tag":
        write_flags = {"-a", "-d", "-f", "-m", "-F", "-s", "-u", "-e", "--delete", "--force",
                       "--annotate", "--sign", "--message", "--file", "--edit"}
        if any(t in write_flags for t in toks):
            return True
        list_flags = {"-l", "--list", "--contains", "--no-contains", "--merged",
                      "--no-merged", "--points-at"}
        return bool(positionals(toks)) and not any(t in list_flags for t in toks)
    if sub == "stash":
        return first not in {"list", "show"}
    if sub == "remote":
        return first not in {"", "-v", "--verbose", "show", "get-url"}
    if sub == "worktree":
        return first != "list"
    if sub == "reflog":
        return first in {"expire", "delete"}
    if sub == "submodule":
        return first not in {"", "status", "summary"}
    if sub == "notes":
        return first not in {"list", "show"}
    if sub == "symbolic-ref":
        return len(positionals(toks)) >= 2 or "-d" in toks or "--delete" in toks
    if sub == "config":
        write_flags = {"--unset", "--unset-all", "--add", "--replace-all", "--edit", "-e",
                       "--remove-section", "--rename-section"}
        if any(t in write_flags for t in toks):
            return True
        return len(positionals(toks)) >= 2
    return True


def find_violation(cmd):
    # Join shell line continuations so a split command is scanned as one.
    cmd = cmd.replace("\\\n", " ")
    for m in GIT_SUB.finditer(cmd):
        sub = m.group("sub")
        if sub in GIT_ALWAYS_BLOCK:
            return f"git {sub}"
        if git_conditional_is_write(sub, args_after(cmd, m.end())):
            return f"git {sub} (write form)"
    for pat in GH_BLOCK:
        m = pat.search(cmd)
        if m:
            return m.group(0).strip()
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception as exc:  # fail closed
        sys.stderr.write(f"block-git-writes: could not parse hook input ({exc}); blocking by default.\n")
        return 2
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    hit = find_violation(cmd)
    if not hit:
        return 0
    sys.stderr.write(
        "BLOCKED by .claude/hooks/block-git-writes.py: this repository forbids Claude from "
        f"running git or gh write commands (matched: {hit}).\n"
        "Do not retry or work around it. Finish the task, then give the user the exact "
        "commands to run themselves, per the Git section of CLAUDE.md.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
