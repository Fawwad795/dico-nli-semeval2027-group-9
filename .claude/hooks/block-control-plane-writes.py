#!/usr/bin/env python3
"""PreToolUse hook: block Bash commands that write to control-plane files.

The control plane is the set of files that govern how Claude Code behaves in this
repository: CLAUDE.md, .mcp.json, .claude/settings*.json, .claude/hooks/, .claude/skills/,
.claude/reference/, .claude/scripts/, .github/workflows/. A change to them must go through
a reviewed edit (the Edit/Write tools, which prompt the user via permissions.ask), never
through a shell redirect, sed -i, or a Python heredoc that nobody looked at.

The check is target-aware: a write-ish construct blocks only when it acts ON a
control-plane path. Redirect targets, in-place editor arguments, file-command arguments
(mv, cp, rm, tee, mkdir, PowerShell cmdlets), and inline code or heredoc bodies that both
name a control-plane path and call a write are blocked. Reads pass: cat, grep, sed -n,
`cat CLAUDE.md >/dev/null`, `python -c "json.load(open('.claude/settings.json'))"`,
running a script under .claude/scripts/. Anything the parser cannot classify while a
control-plane path is present fails closed.

Exit 2 blocks the tool call and shows stderr to Claude. Exit 0 allows it.
"""

import json
import re
import sys

CONTROL_PLANE = re.compile(
    r"(?:CLAUDE\.md|\.mcp\.json|\.claude[\\/]settings(?:\.local)?\.json"
    r"|\.claude[\\/](?:hooks|skills|reference|scripts)\b|\.github[\\/]workflows\b)",
    re.IGNORECASE,
)

# Shell separators that end one simple command's argument list.
SEPARATOR = re.compile(r"\s*(?:;|&&|\|\||\||\n)")

REDIRECT = re.compile(r"(?:^|[^2&<])>>?\s*(\S+)")
INPLACE_EDITOR = re.compile(r"\bsed\s+(?:-[a-zA-Z]*i\b|--in-place)|\bperl\b[^\n]*?\s-[a-zA-Z]*i\b")
FILE_COMMAND = re.compile(
    r"\b(mv|cp|rm|rmdir|truncate|install|chmod|chown|ln|touch|mkdir|tee"
    r"|Set-Content|Out-File|Add-Content|New-Item|Remove-Item|Move-Item|Copy-Item|Rename-Item)\b",
    re.IGNORECASE,
)
INLINE_CODE = re.compile(r"\b(?:python[0-9.]*\s+-c|node\s+-e)\s+(['\"])(.*?)\1", re.DOTALL)
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n(.*?)^\1[ \t]*$", re.DOTALL | re.MULTILINE)

# Calls that write a file from inside Python, Node, or shell code.
WRITE_CALL = re.compile(
    r"open\([^)]*['\"][wax]\+?b?['\"]"          # open(..., 'w' | 'a' | 'x')
    r"|\.write(?:_text|_bytes|lines)?\("
    r"|writeFile|appendFile|createWriteStream"
    r"|\bunlink\b|os\.remove\(|\.rename\(|os\.rename\(|shutil\.|rmtree"
    r"|\bdump\(|\.mkdir\(|\.touch\(|\.truncate\(|os\.makedirs\(",
)


def segment_after(cmd, end):
    """Argument text from `end` to the next shell separator."""
    return SEPARATOR.split(cmd[end:], 1)[0]


def find_violation(cmd):
    if not CONTROL_PLANE.search(cmd):
        return None

    for m in REDIRECT.finditer(cmd):
        target = m.group(1)
        if not target.startswith("&") and CONTROL_PLANE.search(target):
            return f"redirect to {target}"

    for m in INPLACE_EDITOR.finditer(cmd):
        if CONTROL_PLANE.search(segment_after(cmd, m.start())):
            return "in-place edit of a control-plane file"

    for m in FILE_COMMAND.finditer(cmd):
        if CONTROL_PLANE.search(segment_after(cmd, m.end())):
            return f"{m.group(1)} on a control-plane path"

    for m in INLINE_CODE.finditer(cmd):
        code = m.group(2)
        if CONTROL_PLANE.search(code) and WRITE_CALL.search(code):
            return "inline code writing a control-plane file"

    heredoc_found = False
    for m in HEREDOC.finditer(cmd):
        heredoc_found = True
        body = m.group(2)
        if CONTROL_PLANE.search(body) and WRITE_CALL.search(body):
            return "heredoc writing a control-plane file"

    if "<<" in cmd and not heredoc_found:
        return "heredoc that could not be parsed while a control-plane path is present"

    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception as exc:  # fail closed
        sys.stderr.write(f"block-control-plane-writes: could not parse hook input ({exc}); blocking by default.\n")
        return 2
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    hit = find_violation(cmd)
    if not hit:
        return 0
    sys.stderr.write(
        "BLOCKED by .claude/hooks/block-control-plane-writes.py: Bash may not write to "
        f"control-plane files (matched: {hit}).\n"
        "Control-plane files change only through the Edit or Write tools, which prompt the "
        "user for review. Read them with the Read tool or a plain cat/grep. See the Trust "
        "boundaries section of CLAUDE.md.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
