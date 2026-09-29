# Secrets

> Environment variable names and purpose. Values never enter this file or git.

Convention: variables live in a gitignored `.env` at the repo root (`.gitignore` already excludes `.env`, `.env.local`, `.env.*.local`); this file lists each name, what it unlocks, and who holds it.

| Variable | Purpose | Held by |
|---|---|---|
| `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET` | Launch GPU jobs on Modal. `modal token new` writes them to `~/.modal.toml`; the env-var form is for scripts and CI. One Modal workspace per teammate, so each person holds their own pair | Each teammate, individually |

No model-provider API key is planned: the baseline and the method run on open-weight models. If a hosted model is added later, its key is listed here first.
