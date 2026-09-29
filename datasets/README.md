# Datasets

Metadata only. Raw data never lands in git (`.gitignore` excludes everything here except `*.md`, `*.json`, `*.yaml`, `*.yml`, `*.toml`).

For each dataset, a file here records: source and version, licence, size, split definitions, the download command or script, and the checksum of the downloaded archive. Data itself goes in a subfolder that stays ignored.

## DiCo-NLI (SemEval-2027 Task 2)

- Source: `https://github.com/ilopezgazpio/SemEval-2027-Task-2-DiCo-NLI`, folder `final_data/`. Licence: GPL-3.0.
- Tracks: 1 English, 2 Spanish, 3 Basque, 4 mixed (EN/ES/EU). Train 3,042 and dev 660 per monolingual track; mixed 18,252 and 3,960.
- Format: CSV per track and split. Participant files carry the phrase pair and label; submission template is `instance_id,label`; reference files add `reverse_pair_id` for the consistency metrics.
- Labels: `EQUIVALENCE`, `FORWARD_ENTAILMENT`, `BACKWARD_ENTAILMENT`, `NEGATIVE_OTHER`.
- Splits for the course: train is train; **dev is the course test set** (the official test set is released 10 January 2027). Any model selection uses a held-out slice of train, never dev.
- Download: clone the repository into `datasets/dico-nli/` (ignored) and record the commit hash in `datasets/dico-nli.json` when the first experiment runs. Until then the hash is unrecorded.
- Scorer: `python3 -m evaluation_functions --gold <reference.csv> --predictions <predictions.csv> --output-dir <results/>` from the repository.
