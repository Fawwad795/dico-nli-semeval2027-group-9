#!/usr/bin/env python3
"""Regression tests for the four PreToolUse hooks.

Run: python .claude/scripts/test-hooks.py
Exit 0 when every case behaves as expected, 1 otherwise. Loads each hook's
find_violation() in-process, then checks the real entrypoints' exit codes with four
subprocess calls per hook. The tests-first hook runs against a temporary project root
with fixture test files. Keep the tables here; a Bash heredoc that quotes these commands
would be blocked by the very hooks it is testing.
"""

import importlib.util
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOOKS = os.path.join(ROOT, ".claude", "hooks")


def load(name):
    path = os.path.join(HOOKS, name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


def run_entrypoint(path, payload):
    if not isinstance(payload, str):
        payload = json.dumps(payload)
    return subprocess.run([sys.executable, path], input=payload, capture_output=True, text=True).returncode


GIT_BLOCK = [
    "git commit -m x", "git add .", "git push", "git push origin main", "git pull", "git merge main",
    "cd /d/repo && git commit -m x", "git -C /d/repo push", 'bash -c "git add -A"',
    "bash -c 'git commit'", 'sh -c "git push"', "eval 'git add .'", "pwsh -c 'git commit -m x'",
    "git --no-pager commit", "git checkout -- file", "git switch -c feat", "git restore .",
    "git reset --hard", "git rebase main", "git stash", "git stash pop", "git stash push -m x",
    "git branch feat", "git branch -d feat", "git branch -m old new", "git tag v1", "git tag -a v1 -m x",
    "git remote add up https://x", "git remote set-url origin x", "git worktree add ../w",
    "git config user.name Foo", "git config --unset x", "git cherry-pick abc", "git revert HEAD",
    "git rm file", "git mv a b", "git clean -fd", "git am patch", "git apply p.diff", "git gc",
    "git init", "git reflog expire --all", "git submodule update --init", "git notes add -m x",
    "git symbolic-ref HEAD refs/heads/x", "git update-ref refs/heads/x abc",
    "echo x | git commit -F -", "/usr/bin/git commit", "git.exe commit -m x",
    "gh pr create --title x", "gh pr merge 1 --squash", "gh pr close 1", "gh pr checkout 1",
    "gh issue create", "gh release create v1", "gh repo create x", "gh repo delete x",
    "gh workflow run ci.yml", "gh run cancel 1", "gh api repos/x/y -X POST", "gh api repos/x -f k=v",
    "gh api --method DELETE repos/x", "gh auth login", "gh secret set K",
    "git status; git commit -m x",
]
GIT_ALLOW = [
    "git status", "git status --short", "git log --oneline -5", "git diff", "git diff --stat HEAD",
    "git show HEAD:file", "git branch", "git branch -a", "git branch --show-current",
    "git branch --list 'feat*'", "git branch --contains abc", "git tag", "git tag -l 'v*'",
    "git tag --contains abc", "git stash list", "git stash show -p", "git remote -v",
    "git remote show origin", "git remote get-url origin", "git worktree list",
    "git config --get user.name", "git config --list", "git config user.name",
    "git reflog", "git reflog show", "git submodule status", "git notes list",
    "git symbolic-ref HEAD", "git rev-parse HEAD", "git ls-files", "git blame f",
    "git check-ignore -q x", "git fetch", "git fetch origin", "git clone https://x .tmp/x",
    "ls -la .git/hooks/pre-commit", "echo digit", "cat .gitignore",
    "node .claude/scripts/doctor.mjs", "gh pr view 1", "gh pr list", "gh pr checks 1",
    "gh pr diff 1", "gh run list", "gh run view 1", "gh run watch 1", "gh issue view 1",
    "gh repo view", "gh repo clone x", "gh api repos/x/y", "gh api repos/x --jq .name",
    "gh auth status", "gh browse", "gh pr view 1 --comments",
]

CP_BLOCK = [
    "echo x >> CLAUDE.md", "echo x > CLAUDE.md", "cat a > .claude/settings.json",
    "cd /d/repo && echo y > .claude\\settings.json",
    "sed -i 's/a/b/' CLAUDE.md", "sed -i.bak 's/a/b/' .claude/reference/pitfalls.md",
    "perl -pi -e 's/a/b/' CLAUDE.md", "perl -i.bak -pe 's/a/b/' .claude/settings.json",
    "tee .claude/skills/foo/SKILL.md", "tee -a .claude/reference/x.md",
    "mv a .claude/hooks/b.sh", "cp x .mcp.json", "cp x .github/workflows/ci.yml",
    "rm .claude/hooks/block-git-writes.py", "rm -rf .claude/skills/merge",
    "touch .claude/reference/new.md", "mkdir .claude/skills/evil",
    "python -c \"open('.claude/settings.json','w').write('{}')\"",
    "node -e \"require('fs').writeFileSync('CLAUDE.md','')\"",
    "python - <<'PY'\nimport io\np = '.claude/settings.json'\nio.open(p, 'w').write('x')\nPY",
    "python - <<'PY'\nfrom pathlib import Path\nPath('CLAUDE.md').write_text('x')\nPY",
    "cat <<'EOF' > .claude/hooks/x.sh\necho hi\nEOF",
    "Set-Content CLAUDE.md x", "Out-File -FilePath .claude/settings.local.json",
    "python - <<'PY'\nprint('.claude/hooks')",           # unterminated heredoc: fail closed
]
CP_ALLOW = [
    "cat CLAUDE.md", "head -40 CLAUDE.md", "sed -n '1,10p' CLAUDE.md", "grep -rn x .claude/reference/",
    "cat .claude/settings.json 2>/dev/null", "cat CLAUDE.md 2>&1 | head", "cat CLAUDE.md >/dev/null",
    "diff CLAUDE.md /tmp/x", "stat CLAUDE.md", "file .claude/reference/*.md", "wc -l .claude/reference/pitfalls.md",
    "node .claude/scripts/doctor.mjs", "node .claude/scripts/doctor.mjs | tail -2",
    "node .claude/scripts/doctor.mjs --json > .tmp/doctor.json",
    "bash .claude/scripts/context-weight.sh 2>&1 | tail -5", "bash -n .claude/hooks/session-start.sh && echo OK",
    "echo '{}' | python .claude/hooks/block-git-writes.py", "python .claude/scripts/test-hooks.py",
    "ls -la .claude/hooks", "ls .claude/skills | wc -l",
    "python -c \"import json; json.load(open('.claude/settings.json')); print('ok')\"",
    "node .claude/scripts/doctor.mjs && python -c \"import json; print(json.load(open('.claude/settings.json'))['permissions']['ask'])\"",
    "python - <<'PY'\nimport importlib.util\nspec = importlib.util.spec_from_file_location('h', '.claude/hooks/block-git-writes.py')\nPY",
    "echo x > .tmp/out.txt", "mkdir -p src/foo", "sed -i 's/a/b/' README.md", "sed -i 's/a/b/' README.md && cat CLAUDE.md",
    "python - <<'PY'\nprint(1)\nPY", "node doctor.mjs | tee .tmp/out.txt",
    "git diff CLAUDE.md", "git log --oneline -- .claude/hooks/",
]


def check(label, module, path, block, allow, write_cmd, read_cmd):
    failures = []
    for cmd in block:
        if module.find_violation(cmd) is None:
            failures.append(f"{label}: NOT BLOCKED: {cmd!r}")
    for cmd in allow:
        verdict = module.find_violation(cmd)
        if verdict is not None:
            failures.append(f"{label}: WRONGLY BLOCKED ({verdict}): {cmd!r}")
    if run_entrypoint(path, {"tool_name": "Bash", "tool_input": {"command": write_cmd}}) != 2:
        failures.append(f"{label}: entrypoint did not exit 2 on a write")
    if run_entrypoint(path, {"tool_name": "Bash", "tool_input": {"command": read_cmd}}) != 0:
        failures.append(f"{label}: entrypoint did not exit 0 on a read")
    if run_entrypoint(path, {"tool_name": "Read", "tool_input": {"command": write_cmd}}) != 0:
        failures.append(f"{label}: entrypoint did not ignore a non-Bash tool")
    if run_entrypoint(path, "not json") != 2:
        failures.append(f"{label}: entrypoint did not fail closed on bad input")
    print(f"{label}: {len(block)} block cases, {len(allow)} allow cases, 4 entrypoint checks")
    return failures


def check_tests_first():
    """require-tests-first.py against a temporary project root with a few fixture tests."""
    import shutil
    import tempfile

    module, path = load("require-tests-first.py")
    root = tempfile.mkdtemp(prefix="tests-first-")
    try:
        unit = os.path.join(root, "tests", "unit")
        os.makedirs(unit)
        with open(os.path.join(unit, "test_tokenizer.py"), "w", encoding="utf-8") as f:
            f.write("def test_roundtrip():\n    assert True\n")
        with open(os.path.join(unit, "test_database.py"), "w", encoding="utf-8") as f:
            f.write("def test_db():\n    assert True\n")          # must not satisfy base.py
        with open(os.path.join(unit, "test_policy.py"), "w", encoding="utf-8") as f:
            f.write("# placeholder, no test function yet\n")     # must not satisfy policy.py
        drive, rest = os.path.splitdrive(root)
        msys_root = "/" + drive[0].lower() + rest.replace("\\", "/") if drive else root

        cases = [
            ("Write", {"file_path": "src/dico_nli/models/scorer.py"}, True),
            ("Edit", {"file_path": os.path.join(root, "src", "dico_nli", "data", "loader.py")}, True),
            ("Write", {"file_path": "src/dico_nli/pipeline.py"}, True),
            ("Write", {"file_path": "src/dico_nli/baselines/majority.py"}, True),
            ("Write", {"file_path": "src/dico_nli/models/base.py"}, True),          # test_database is not a match
            ("Write", {"file_path": "src/dico_nli/eval/policy.py"}, True),          # stub without def test_
            ("Write", {"file_path": "src/dico_nli/tokenizer.py"}, False),           # fixture test exists
            ("Write", {"file_path": "src/dico_nli/__init__.py"}, False),
            ("Write", {"file_path": "src/dico_nli/models/__init__.py"}, False),
            ("Write", {"file_path": "src/dico_nli/conftest.py"}, False),
            ("Write", {"file_path": "scripts/tools/helper.py"}, False),                # outside the package
            ("Write", {"file_path": "tests/unit/test_scorer.py"}, False),
            ("Write", {"file_path": "README.md"}, False),
            ("Read", {"file_path": "src/dico_nli/models/scorer.py"}, False),
            ("Bash", {"command": "cat > src/dico_nli/models/scorer.py <<'EOF'\nx\nEOF"}, True),
            ("Bash", {"command": "echo x > src/dico_nli/data/validator.py"}, True),
            ("Bash", {"command": "cp x.py src/dico_nli/data/store.py"}, True),
            ("Bash", {"command": "echo x > $CLAUDE_PROJECT_DIR/src/dico_nli/models/scorer.py"}, True),
            ("Bash", {"command": f"echo x > {msys_root}/src/dico_nli/models/scorer.py"}, True),
            ("Bash", {"command": "echo x > src/dico_nli/tokenizer.py"}, False),
            ("Bash", {"command": "cat src/dico_nli/models/scorer.py"}, False),
            ("Bash", {"command": "echo x > .tmp/out.py"}, False),
            ("Bash", {"command": "python -m pytest tests/unit/test_tokenizer.py"}, False),
        ]
        failures = []
        for tool, tool_input, expect_block in cases:
            blocked = module.find_violation(tool, tool_input, root) is not None
            if blocked != expect_block:
                failures.append(f"tests-first: expected {'block' if expect_block else 'allow'}: {tool} {tool_input}")

        env = dict(os.environ, CLAUDE_PROJECT_DIR=root)
        def rc(payload):
            if not isinstance(payload, str):
                payload = json.dumps(payload)
            return subprocess.run([sys.executable, path], input=payload, capture_output=True, text=True, env=env).returncode
        if rc({"tool_name": "Write", "tool_input": {"file_path": "src/dico_nli/models/scorer.py"}}) != 2:
            failures.append("tests-first: entrypoint did not exit 2 on an untested module")
        if rc({"tool_name": "Write", "tool_input": {"file_path": "src/dico_nli/tokenizer.py"}}) != 0:
            failures.append("tests-first: entrypoint did not exit 0 on a tested module")
        if rc({"tool_name": "Read", "tool_input": {"file_path": "src/dico_nli/models/scorer.py"}}) != 0:
            failures.append("tests-first: entrypoint did not ignore a read")
        if rc("not json") != 2:
            failures.append("tests-first: entrypoint did not fail closed on bad input")
        print(f"tests-first: {sum(1 for c in cases if c[2])} block cases, {sum(1 for c in cases if not c[2])} allow cases, 4 entrypoint checks")
        return failures
    finally:
        shutil.rmtree(root, ignore_errors=True)


def check_feature_branch():
    """require-feature-branch.py against temporary roots with hand-written .git/HEAD files."""
    import shutil
    import tempfile

    module, path = load("require-feature-branch.py")
    failures = []
    made = []

    def root_with_head(head_text, via_gitdir=False):
        root = tempfile.mkdtemp(prefix="feature-branch-")
        made.append(root)
        if via_gitdir:
            real = os.path.join(root, "real-gitdir")
            os.makedirs(real)
            with open(os.path.join(real, "HEAD"), "w", encoding="utf-8") as f:
                f.write(head_text + "\n")
            with open(os.path.join(root, ".git"), "w", encoding="utf-8") as f:
                f.write("gitdir: real-gitdir\n")
        elif head_text is not None:
            os.makedirs(os.path.join(root, ".git"))
            with open(os.path.join(root, ".git", "HEAD"), "w", encoding="utf-8") as f:
                f.write(head_text + "\n")
        return root

    try:
        on_main = root_with_head("ref: refs/heads/main")
        outside = tempfile.mkdtemp(prefix="outside-")
        made.append(outside)
        cases = [
            (on_main, "Write", {"file_path": "src/dico_nli/pipeline.py"}, True),
            (on_main, "Edit", {"file_path": "CLAUDE.md"}, True),
            (on_main, "Write", {"file_path": os.path.join(on_main, "docs", "x.md")}, True),
            (on_main, "Write", {"file_path": ".tmp/notes.md"}, False),
            (on_main, "Write", {"file_path": ".venv/x"}, False),
            (on_main, "Write", {"file_path": os.path.join(outside, "elsewhere.txt")}, False),
            (on_main, "Read", {"file_path": "CLAUDE.md"}, False),
            (on_main, "Bash", {"command": "echo x > README.md"}, True),
            (on_main, "Bash", {"command": "rm docs/x.md"}, True),
            (on_main, "Bash", {"command": "mkdir docs/new"}, True),
            (on_main, "Bash", {"command": "cp a.py src/b.py"}, True),
            (on_main, "Bash", {"command": "echo x > .tmp/out.txt"}, False),
            (on_main, "Bash", {"command": "mkdir -p .tmp/x"}, False),
            (on_main, "Bash", {"command": "cat README.md"}, False),
            (on_main, "Bash", {"command": "git status"}, False),
            (on_main, "Bash", {"command": "uv run pytest"}, False),
            (root_with_head("ref: refs/heads/master"), "Write", {"file_path": "src/x.py"}, True),
            (root_with_head("0123456789abcdef0123456789abcdef01234567"), "Write", {"file_path": "src/x.py"}, True),
            (root_with_head("ref: refs/heads/wip"), "Write", {"file_path": "src/x.py"}, True),
            (root_with_head("ref: refs/heads/Fawwad-branch"), "Write", {"file_path": "src/x.py"}, True),
            (root_with_head("ref: refs/heads/assignment-1/literature-review"), "Write", {"file_path": "src/x.py"}, False),
            (root_with_head("ref: refs/heads/harness/branch-rule"), "Edit", {"file_path": "CLAUDE.md"}, False),
            (root_with_head("ref: refs/heads/assignment-1/baseline-run"), "Bash", {"command": "echo x > README.md"}, False),
            (root_with_head("ref: refs/heads/main", via_gitdir=True), "Write", {"file_path": "src/x.py"}, True),
            (root_with_head("ref: refs/heads/assignment-2/method", via_gitdir=True), "Write", {"file_path": "src/x.py"}, False),
            (root_with_head("ref: refs/heads/-bad/area"), "Write", {"file_path": "src/x.py"}, True),   # area must start alphanumeric
            (root_with_head("ref: refs/heads/Assignment-1/x"), "Write", {"file_path": "src/x.py"}, True),  # lower case only
            (root_with_head(None), "Write", {"file_path": "src/x.py"}, False),   # not a git repo
        ]
        for root, tool, tool_input, expect_block in cases:
            blocked = module.find_violation(tool, tool_input, root) is not None
            if blocked != expect_block:
                failures.append(f"feature-branch: expected {'block' if expect_block else 'allow'}: {tool} {tool_input} (HEAD={open(os.path.join(root, '.git', 'HEAD')).read().strip() if os.path.isdir(os.path.join(root, '.git')) else 'n/a'})")

        env = dict(os.environ, CLAUDE_PROJECT_DIR=on_main)
        def rc(payload):
            if not isinstance(payload, str):
                payload = json.dumps(payload)
            return subprocess.run([sys.executable, path], input=payload, capture_output=True, text=True, env=env).returncode
        if rc({"tool_name": "Write", "tool_input": {"file_path": "src/x.py"}}) != 2:
            failures.append("feature-branch: entrypoint did not exit 2 on main")
        if rc({"tool_name": "Write", "tool_input": {"file_path": ".tmp/x"}}) != 0:
            failures.append("feature-branch: entrypoint did not exit 0 on scratch")
        if rc({"tool_name": "Read", "tool_input": {"file_path": "src/x.py"}}) != 0:
            failures.append("feature-branch: entrypoint did not ignore a read")
        if rc("not json") != 2:
            failures.append("feature-branch: entrypoint did not fail closed on bad input")
        print(f"feature-branch: {sum(1 for c in cases if c[3])} block cases, {sum(1 for c in cases if not c[3])} allow cases, 4 entrypoint checks")
        return failures
    finally:
        for d in made:
            shutil.rmtree(d, ignore_errors=True)


def main():
    failures = []
    git, git_path = load("block-git-writes.py")
    failures += check("git", git, git_path, GIT_BLOCK, GIT_ALLOW, "cd x && git commit -m y", "git status")
    cp, cp_path = load("block-control-plane-writes.py")
    failures += check("control-plane", cp, cp_path, CP_BLOCK, CP_ALLOW, "echo x >> CLAUDE.md", "cat CLAUDE.md")
    failures += check_tests_first()
    failures += check_feature_branch()
    if failures:
        print("\n".join(failures))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
