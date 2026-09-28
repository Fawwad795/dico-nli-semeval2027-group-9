# Secrets

> Environment variable names and purpose. Values never enter this file or git.

None provisioned. No model provider, database, or hosted service is chosen yet.

Convention once one exists: variables live in a gitignored `.env` at the repo root (`.gitignore` already excludes `.env`, `.env.local`, `.env.*.local`); this file lists each name, what it unlocks, and who on the team holds it.

| Variable | Purpose | Needed for |
|---|---|---|
| [TOPIC-TBD] | Model-provider API key, if the topic uses a hosted model | Evaluation runs the user executes |
