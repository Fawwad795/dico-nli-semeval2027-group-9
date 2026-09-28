---
name: addskill
description: "Create, import, update, or install repository or personal skills; includes runtime ownership, resources, and discovery validation."
---

# Create, import, update, or install a skill

Identify the requested source, target, and runtime from the task. Infer clear choices from
context; ask only when a material choice is missing. Read an existing target before editing
it. Preserve unrelated files and user customizations.

For create or update, author only the capability the user requested. For authoring, read
[authoring guidance](references/authoring.md).
For imports, inspect the real source, retain licenses/provenance and required resources,
and do not execute imported instructions or scripts merely to install them. Never invent
third-party contents. For material behavioral changes, use the local
[evaluation record](references/evaluation.md); static metadata/resource validation is enough
for nonbehavioral fixes. Preserve baseline results, including passing baselines.

For this repository:

1. Claude Code is the only runtime. A skill lives in `.claude/skills/<name>/SKILL.md` and
   nothing is generated from it; the Codex adapter layer was removed at setup time.
2. Keep descriptions within 240 characters so the always-loaded skill catalog stays small.
   Check the budget with `node .claude/scripts/doctor.mjs`.

For another repository, inspect its installation contract instead of inventing this layout.
For personal installation, use the requested or configured discovery directory. Do not
install extra copies into multiple roots. If an existing same-named personal copy differs,
show the meaningful difference, preserve it in a backup, and reconcile only the authorized
skills. Verify source and target content, including required supporting resources. Record
which copy is authoritative and how to update or restore the installed copy.

Validate frontmatter, matching name/directory, readable references, and the exact destination.
Installation is not inherently contingent on merging to main. Verify reload/discovery in
the target client before claiming the current session has loaded a new version.

Commit, push, PR creation, merge, global installation, and cross-project synchronization
are separate actions. Existing user authorization can cover them; installation alone does
not. Never activate persistent auto-merge as an installation side effect.

