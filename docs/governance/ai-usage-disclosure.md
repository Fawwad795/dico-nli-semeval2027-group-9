# AI usage disclosure

Large Language Models course, semester research project.

Team: Muhammad Shaheer Saleh, Ahmad Imran, Syed Fawwad Ahmed, Aqib Raza.

## Rule

Every material AI-assisted artifact (a component, a document, an experiment, a review) gets a dated row below before the task that produced it ends. Typo fixes and formatting are not logged. AI use is disclosed here, never in git history (no attribution trailers in commits or pull requests).

## Log

| Date | Artifact | Tool | What the AI did | Reviewed by |
|---|---|---|---|---|
| 2026-09-28 | Repository setup: kernel (`CLAUDE.md`), hooks and their tests, reference library, directory layout, `pyproject.toml`, README, this document | Claude Code (Fable 5.1) | Retargeted a copied governance layer to this course project from a user-written plan; verified with the hook tests, the harness doctor, and an empty pytest run | Syed Fawwad Ahmed |
| 2026-09-29 | Topic selection: comparison of the SemEval-2027 tasks and ICASSP 2027 grand challenges, Azure and Modal compute check, decision record, placeholder replacement across the repo | Claude Code (Fable 5.1) | Fetched and summarized every task page and the Azure and Modal policy pages, ranked candidates, drafted the decision entry and the professor's notes; the topic and compute decisions were made by the team | Syed Fawwad Ahmed |
| 2026-09-29 | Package rename `llm_project` to `dico_nli`: package directory, `pyproject.toml`, `uv.lock`, tests-first hook pattern and fixtures, kernel and reference paths, READMEs; decision entry in `research-decisions.md` | Claude Code (Fable 5.1) | Located every reference, applied the rename, regenerated the lockfile, verified with the hook tests, the harness doctor, a package import, and pytest | Syed Fawwad Ahmed |
