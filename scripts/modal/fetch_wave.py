"""Fetch one part of every job of a wave from the Modal volume, and check that it all arrived.

    PYTHONIOENCODING=utf-8 uv run python scripts/modal/fetch_wave.py --run-id <run-id> --jobs <wave jobs file> --part validation --dest artifacts/decoder-final-track1

``--part`` is ``validation``, ``dev`` or ``adapter`` (zero-shot jobs have no adapter). Fetch
``validation`` first; fetch ``dev`` only after the lambda choice is committed and pushed. Files
land in ``<dest>/<run-id>/<system>/<part>/``. ``--match <text>`` keeps only the systems whose
name contains the text, for example ``--part adapter --match lambda0.5``.

``modal volume get`` reports success in cases where it did not write what was asked for
(``.claude/reference/pitfalls.md``, Modal item 5), so each part is fetched into an empty staging
folder, located there, moved into place and compared with the list of files the job writes
(``PART_FILES`` in ``train_decoder.py``). The script exits with status 1 if anything is missing.
A part that is already complete locally is skipped; ``--force`` fetches it again.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_decoder import PART_FILES, VOLUME_NAME, load_jobs, system_name  # noqa: E402


def missing_files(folder: Path, part: str) -> list[str]:
    """The files of ``part`` that are absent from ``folder`` or empty."""
    return [name for name in PART_FILES[part]
            if not (folder / name).is_file() or (folder / name).stat().st_size == 0]


def volume_get(remote: str, local: Path) -> None:
    command = [sys.executable, "-m", "modal", "volume", "get", VOLUME_NAME, remote, str(local)]
    subprocess.run(command, check=False, env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def fetch_part(run_id: str, system: str, part: str, dest: Path, force: bool = False, get=volume_get) -> list[str]:
    """Fetch ``<run-id>/<system>/<part>`` into ``dest`` and return the files still missing."""
    target = dest / run_id / system / part
    if target.exists():
        if not force and not missing_files(target, part):
            return []
        shutil.rmtree(target)
    staging = dest / ".fetching" / f"{system}--{part}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)  # the local parent must exist before ``modal volume get``
    get(f"{run_id}/{system}/{part}", staging)
    # Depending on the CLI version the files arrive directly in the folder or under the remote
    # folder's name; take the folder that holds the first expected file.
    found = sorted(staging.rglob(PART_FILES[part][0]), key=lambda path: len(path.parts))
    if found:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(found[0].parent), str(target))
    shutil.rmtree(staging, ignore_errors=True)
    return missing_files(target, part)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--jobs", required=True, help="the wave's JSON jobs file")
    parser.add_argument("--part", required=True, choices=sorted(PART_FILES))
    parser.add_argument("--dest", required=True, help="local folder; <run-id>/<system>/<part>/ is created inside it")
    parser.add_argument("--match", default="", help="only systems whose name contains this text")
    parser.add_argument("--force", action="store_true", help="fetch again even if the part is complete locally")
    args = parser.parse_args()

    jobs = load_jobs(args.jobs)
    if args.part == "adapter":
        jobs = [job for job in jobs if job["mode"] == "lora"]
    systems = [name for name in map(system_name, jobs) if args.match in name]
    if not systems:
        print("no system matches")
        return 1
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    incomplete = {}
    for system in systems:
        missing = fetch_part(args.run_id, system, args.part, dest, force=args.force)
        print(f"{'MISSING ' + str(missing) if missing else 'ok':<10} {system}/{args.part}")
        if missing:
            incomplete[system] = missing
    shutil.rmtree(dest / ".fetching", ignore_errors=True)
    expected = len(systems) * len(PART_FILES[args.part])
    lacking = sum(len(missing) for missing in incomplete.values())
    print(f"{expected - lacking} of {expected} files present for {len(systems)} systems under {dest / args.run_id}")
    if incomplete:
        print(f"incomplete: {sorted(incomplete)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
