# Pitfalls

> Accumulated tool and harness gotchas, carried over from the previous project where they were about the tools rather than that project. Dated entries, newest at the bottom. If this file exceeds ~200 lines, split by area (`pitfalls-<area>.md`) and update the CLAUDE.md index.

## Worktree and checkout safety

Worktree changes are isolated. Before claiming a template change is available
somewhere else, verify the exact branch or checkout the user asked about. Do not
merge, pull into another checkout, or touch paths outside the current workspace
unless the user explicitly asks in the current session.

## Local preview servers: stale or wrong site (2026-07-18)

Symptom: opening a local dev/preview server shows an outdated version of the
site, or a completely different project.

Root causes:

1. **Server reuse on a busy port.** Preview tooling (and manual servers) reuse
   whatever is already bound to the port. A server left over from a prior
   session serves old code; a different project on a shared default port
   (3000/5173/8080) serves the wrong site entirely.
2. **Worktree mismatch.** Server launched from the main checkout while edits
   live in a git worktree (or the reverse) — edits never appear no matter how
   often the page reloads.
3. **Stale build output.** Serving `dist/`/`build/` without rebuilding after
   source edits.
4. **Browser cache / service worker.** Old assets persist even after the
   server itself is current.

Prevention protocol (run every time before trusting a preview):

1. Before starting: check the port (`netstat -ano | findstr :<port>` on
   Windows, `lsof -i :<port>` on Unix). Port busy → inspect the owning PID's
   command line and cwd; if they don't match the current checkout, kill it or
   start on a fresh unique port. Never assume a reused server is the right one.
2. After loading: **sentinel check** — verify the page contains a string unique
   to the change just made (via page-text extraction, not a screenshot glance).
   No sentinel visible → server is stale or wrong; stop and diagnose before
   claiming anything works.
3. Static builds: rebuild before serving; confirm output mtime is newer than
   the edited sources.
4. Staleness persists after 1–2 → hard reload, unregister service workers, or
   use a fresh browser profile.

## Cross-cutting engineering gotchas (2026-08-18, from cursor-team-kit review)

1. **History rewrites: tree-hash check.** Before any agreed rebase/squash of a
   pushed branch, capture `ORIGINAL_TREE=$(git rev-parse origin/<branch>^{tree})`;
   after rewriting, compare with `git rev-parse HEAD^{tree}`. Do not push if the
   tree changed unintentionally — the rewrite was supposed to reshape history,
   not content.
2. **JSON embedded in `<script>` tags.** `JSON.stringify`/`json.dumps` output is
   not HTML-safe: a `</script>` inside a string terminates the tag early. Escape
   `<`, `>`, `&` as `<`, `>`, `&` before embedding.
3. **Backgrounded dev servers: fixed port.** Background shells have no TTY, so
   server startup messages can sit buffered and unread — with port 0
   (auto-assign) you can never learn which port was chosen. Always pass an
   explicit port to servers started in the background.

## Headed Chrome steals the screen unless you place it (2026-08-23)

Visual verification runs headed on the real GPU, and a plain
`chromium.launch({ headless: false, channel: "chrome" })` drops that window on
top of whatever the operator is doing and takes the keyboard with it.

Minimizing does not solve it. Measured on Windows 10 with two displays: a window
minimized through CDP (`Browser.setWindowBounds`, `windowState: "minimized"`)
loses its compositor surface and requestAnimationFrame throttles to **1 Hz**,
with or without `--disable-features=CalculateNativeWinOcclusion`. Screenshots
still return fresh pixels at 1 Hz, so a static DOM check passes while every
frame timing, scroll narrative and animation reading is garbage.

Fix: `scripts/lib/launch-chrome.mjs` -> `launchPlacedChrome()`. It places the
window on a display that is not holding the foreground window, then hands the
foreground back to the window that had it. `CHROME_PLACE` picks the mode:
`other-monitor` (default), `offscreen` (parked at -2400,-2400, rendered but
never visible, and the fallback when only one display is attached), or `here`.
Both placed modes held 100.5 fps on a 100 Hz panel, same as an unplaced window.

Notes: `--window-position` applies to the first window of a launch, so one
launch per run. Placement is Windows-only and degrades to a plain headed launch
elsewhere. The DIP-to-pixel mapping assumes both displays share a scale factor.

## Playwright MCP plugin browser is a single shared instance (2026-08-29)

The official playwright plugin launches `npx @playwright/mcp@latest` with a
persistent profile. Two MCP server processes (a main session plus a subagent
with its own connection) cannot share that profile: the second gets
"Browser is already in use ... use --isolated" and blocks. Observed as a
~10-minute deadlock between a verifier subagent and its main session.

Fixes: the template ships `.mcp.json` defining `playwright-iso`
(`@playwright/mcp@latest --isolated`, in-memory profile, N concurrent agents);
or drive an independent Chrome via a repo-local `playwright-core` +
`scripts/lib/launch-chrome.mjs`. Never point a verifier subagent and the main
session at the shared plugin browser at the same time.

Same shape, different tool (2026-09-09): the desktop app's Browser pane
(`mcp__Claude_Browser__*`, `preview_start`) is one Chrome per app. A second
session or subagent asking for it gets "Another task's Chrome owns browser
slot". `--isolated` does not apply there; that string comes from the app, not
from this repo. Use `playwright-iso` or `launchPlacedChrome()` instead.

## Bash tool cwd resets between calls (2026-08-29)

The shell tool's working directory does not reliably persist across calls; it
intermittently resets to the parent workspace directory. Symptoms observed:
`npx tsc` resolving the dummy "not the tsc command you are looking for"
package from the wrong directory, and `git add` failing with "fatal: not a git
repository". Start compound commands with `cd <repo> &&` or use `git -C`.

**Do not reach for `$TMPDIR` as the fallback (2026-09-21).** Git Bash on this machine
leaves `TMPDIR` unset, and `cd ""` returns 0 rather than failing, so the common idiom
`cd "$TMPDIR" 2>/dev/null || cd /c/Users/<user>/AppData/Local/Temp` never reaches the
fallback: it silently stays in the repository. A `curl -o` after it dropped an untracked
scratch file in the repo root, caught only by a `git status` run just before handing over
a commit block. Write scratch to the session scratchpad directory or to an explicit
absolute path, and prefer `curl` straight to stdout when the content is only being read.

## Redirected Python output dies on non-ASCII under Windows (2026-09-21)

A CLI or script that prints a check mark, an emoji, or any character outside cp1252 runs
fine attached to a terminal (UTF-8) and crashes the moment its output is redirected to a
file, because Python falls back to the Windows ANSI code page:

```
UnicodeEncodeError: 'charmap' codec can't encode character '✓'
```

The dangerous part is the exit status: the wrapping shell can still report success, so a
launcher that starts a job and moves on believes it started. Caught only because the
expected artifacts never appeared.

Fix: set `PYTHONIOENCODING=utf-8` (or `PYTHONUTF8=1`, which also covers file opens) on every
Python invocation whose output is logged, which is all of them in an experiment. This also
applies to local Python that re-emits another process's log text: the character travels.

## Harness transport quirks that corrupt written files (2026-09-21)

1. **A very long `bash -c` heredoc was silently truncated mid-body**, producing a file that
   looked written and was not. Long prose goes through the Write tool; append with `cat >>`
   only in small pieces.
2. **Editing a shell script while it is executing corrupts the running shell.** Bash reads
   the file by byte offset as it goes, so an edit mid-run shifts the offsets under it —
   observed as `erits: command not found` and a syntax error at an innocent `done`.
   Long-running launchers belong in Python, or must be finished before they are edited.
3. **The Write tool strips trailing whitespace.** A patch anchored to lines with trailing
   spaces silently matched nothing. Generate patch context by matching on `strip()` while
   preserving the original bytes, and verify the patch applies before relying on it.
4. **`shlex.split` eats Windows path separators.** It splits POSIX-style, so a
   `.tmp\foo\...` argument arrives mangled and the job dies on a missing file. Use forward
   slashes in anything that will pass through `shlex`.
5. **`block-git-writes.py` matches the string, not the intent.** A script that merely
   contains a git command string (say, because it clones a repository inside a container)
   cannot be written through a Bash heredoc. Author it with the Write or Edit tools. The
   same bites scratch files that quote a forbidden command.

## Line continuations vanish inside Bash-tool heredocs (2026-09-19)

A quoted heredoc (`<<'PY'`) is supposed to pass its body through untouched, but a
doubled backslash at end of line arrives as a single backslash. Python then reads
that backslash plus newline as a source line continuation and deletes both.

Probe: a two-line string written as `A\\` newline `B` came back as `'AB'`,
length 2, not `'A\
B'`, length 4.

Cost: an exact-match `assert old in s` failed against a shell script whose real
content was correct, because the search string had silently lost its continuation.
The edit looked wrong when the transport was.

Avoid end-of-line backslashes in any heredoc body. Match such lines by index or by
a distinctive substring, build the character with `chr(92)`, or edit with `sed`.
This also applies to shell snippets embedded in a heredoc for later execution.

**It is not only end of line (2026-09-24, reproduced twice).** The Bash tool turns `\\`
into `\` anywhere, inside `<<'EOF'` heredocs and inside single-quoted arguments alike:
`a\\b` arrived as `a\b`. The Write tool has a sibling quirk: `\uXXXX` escape sequences in
content are written as the literal character (a test literal meant to hold backslash-u00e9
landed as `é`). Build such strings with `chr()` in code, or use the Edit tool.

## Verifying animated SVG README panels (2026-09-19)

Three things that each cost a retry while building animated README panels:

1. **A CSS keyframe on `transform` replaces the element's whole transform**, including
   a base position set in an inline `style`. A chip rendered at the far left because its
   `translateY` animation wiped `translate(1074px,170px)`. Put the base position in an
   SVG `transform` attribute on a wrapper group and animate only a child; CSS cannot
   override an attribute on a different element.
2. **Page-level media emulation does not reach `<img>`-loaded SVGs.** Playwright's
   `emulateMedia({ reducedMotion: 'reduce' })` left the harness animating because each
   panel is a separate image document. To test a `prefers-reduced-motion` rule, inline
   the SVG into an HTML page and emulate there. Theming still goes through `<picture>`
   sources, which GitHub evaluates itself.
3. **`playwright-iso` blocks `file:` URLs** and navigating straight to a bare `.svg`
   timed out. Serve the scratch folder with `python -m http.server <port> --bind
   127.0.0.1` on a checked-free fixed port and load an HTML harness over
   `http://127.0.0.1:<port>/`. The browser also drops a `.playwright-mcp/` folder of
   snapshots at the repo root; it is gitignored.

Also: the feature-branch hook treats a `>` inside HTML in a heredoc as a shell
redirect and blocks the command. Build such files from a script file, not inline.

Two more from the DiCo-NLI panels (2026-09-29):

4. **Inlined panels share one document, so same-named `@keyframes` collide.** The wide and
   narrow hero both define `swap-a` with different travel distances; inlined side by side for
   measurement, the later definition won and the wide panel's chips flew 350 px instead of 240
   and left the card. The `<img>` rendering, one document per panel, was correct. When
   inlining several panels into one harness, give each panel's keyframes and classes a
   unique prefix, or inline one panel at a time. Frame checks are cheapest with frozen
   clones: set `animation-delay: -<t>s` and `animation-play-state: paused` on every `.anim`
   element and screenshot each phase, instead of racing the live loop.
5. **A reloaded `<img>` SVG does not restart its animation.** Chrome kept the cached image
   document, so a screenshot taken right after navigation showed the loop at 57 %, not 0 %.
   Add `?v=<n>` to the image `src` too, not only to the page URL, when a fresh start matters.

## Same test basename in two subdirectories collides without `__init__.py` (2026-09-21)

`tests/unit/<a>/test_report.py` and `tests/unit/<b>/test_report.py` share a basename. With
no `__init__.py` in either subdirectory, pytest's default (no-package) import mode assigns
both the same top-level module name `test_report`, and running the whole suite fails on the
second one collected:

    import file mismatch:
    imported module 'test_report' has this __file__ attribute:
      tests\unit\<a>\test_report.py
    which is not the same as the test file we want to collect:
      tests\unit\<b>\test_report.py

Each file passes in isolation, which is why this only shows up once a second subdirectory
reuses a name and `pytest tests/` runs everything together.

Fix: add an empty `__init__.py` to each such `tests/unit/<subdir>/` directory (not to
`tests/unit/` itself). pytest then imports each as `<subdir>.test_report`, a distinct name,
without `--import-mode=importlib` or a rename. Check for it before adding the second file,
not after `pytest tests/` fails.

## Ollama truncates silently, and calling code rarely forwards a seed (2026-09-24)

Measured on Ollama 0.32.4 on this machine:

1. **A prompt longer than `num_ctx` is cut without an error**, and `prompt_eval_count` reports the
   length *after* the cut. A multi-message chat loses whole messages with no log line at all. So a
   gate like `max(prompt_eval_count) >= num_ctx` can never fire. Fix: send `"truncate": false` in
   the `/api/chat` body; the server then refuses with HTTP 400 `exceed_context_size_error`
   (ollama-python 0.3.3 has no parameter for it, so hook the request body). Separately gate
   `prompt_eval_count + eval_count < num_ctx`, because context shift during generation is on by
   default and shows only as `slot context shift` in the server log. Grep for that phrase, not
   `context-shift`, which is a flag on every server start line.
2. **Third-party code often accepts a temperature or seed and drops it**, so every call samples at
   the server default with a random seed. Passing `options.seed` makes a repeated request
   reproducible for the same prompt-cache state; a cold call and a cached call with the same seed
   were once observed to diverge, so aim for the same request sequence from a fresh server.
3. **This machine's Ollama server sets `OLLAMA_CONTEXT_LENGTH=262144`.** Pass `num_ctx` per
   request; never rely on the server default.

## A slide-scale diagram needs 3 px arrows, a 44/36 size split and label chips (2026-09-25)

A first architecture diagram was rejected on sight: 2 px muted arrows on a 1728 px canvas
vanished except for their heads once the figure was scaled onto a slide; 40 px sub-lines under
44 px names read as the same size; labels floating beside an arrow looked misplaced; and a 100 px
row with two text lines clipped its descenders. Fixes that held: arrows in `ink` at 3 px with
`markerUnits="strokeWidth"`; names 44 px at weight 500 over 36 px muted sub-lines; every arrow
label a chip centred on the line with a pad in the region's own colour; rows 112 px for two lines;
one low-chroma structural tint per region so the blocks separate without adding a saturated colour.

## PDF from Markdown: pandoc, MiKTeX and biblatex-ieee quirks (2026-09-25)

Building a PDF with pandoc, latexmk and lualatex on this machine cost five failed builds:

- **TeX will not write a file whose name starts with a dot.** A temporary `.build.tex` failed
  with "file not writable for security reasons". Use a plain name.
- **Windows TeX needs drive-letter paths.** latexmk passed Git Bash's `/d/...` form through to
  lualatex and biber; convert with `cygpath -m` for `-outdir` and for bibliography paths.
- **`\,` in pandoc markdown is an escaped comma, not a thin space.** `2\,000` came out as "2,000".
  Type the narrow no-break space (U+202F) itself.
- **pandoc's uncaptioned tables need `\newcounter{none}`** in a custom template ("No counter 'none'").
- **biblatex-ieee sentence-cases titles through its own `sentencecase` format**, so overriding
  `titlecase` changes nothing and names come out as "Iso 7144". Use
  `\DeclareFieldFormat{sentencecase}{#1}`. Its bibliography has no `@standard` driver; use `@online`.
- **Bib `note` fields with unescaped URLs break the reference list** ("Missing $ inserted").
  Drop or escape notes holding URLs.
- **`\DocumentMetadata` (PDF/A) needs `latex-pdfmanagement`**, which this MiKTeX lacks; installing it
  changes every teammate's build, so stay with plain PDF.

## Slide text: measure titles and justified lines, and check the browser's scale (2026-09-25)

Building an HTML slide deck cost four rounds of fixes that measurement would have prevented:

- **Title length.** Atkinson Hyperlegible Next at 88 px bold runs about 40 px a character, so a
  one-line slide title holds about 42 characters; 36 px text runs about 16 px a character. Estimates
  were 20 % off; measure each candidate's width in the page before committing it.
- **Justified text in narrow columns.** Below about 40 characters a line, justified text opens gaps
  of 100 px and more. Measure each line's natural width (`text-align: left`, then the Range's client
  rects), reword until every line but the last is nearly full, and add soft hyphens (U+00AD) at
  dictionary breaks for long words. Never let one split an already hyphenated compound: a soft
  hyphen in "generated" produced "AI-generat-ed".
- **A `playwright-iso` page stuck at half scale.** After `browser_resize` to a smaller viewport and
  back, the page kept `devicePixelRatio` 0.5 (`innerWidth` 3840), and every screenshot showed the
  slide at half size; Ctrl+0 did not reset it. Closing the page and navigating again did. It also
  came back at the start of a later session with no resize, and resizing a page that was already
  open left it at 0.67 (`innerWidth` 2880). What works every time: close the page, navigate, then
  resize to 1920 by 1080 (a fresh page starts at the display's own scale, 1.5 here). Read
  `window.devicePixelRatio` and `innerWidth` before every screenshot batch.
- **Stale pages from the local server.** Chrome reused a cached copy of a page that
  `python -m http.server` served before it was regenerated, and one measurement round read the
  previous candidates. Add `?v=<timestamp>` to every URL, and reset each iframe's `src` the same
  way, when re-checking regenerated files.
- **Overflow checks must include absolutely positioned elements.** A title slide's bottom band
  was `position: absolute`, a check that skipped such elements passed, and the band ran off the slide.
- **The Claude Design skill is user-only.** `/design` has `disable-model-invocation`; the model's
  Skill call fails, and the skill says not to replicate it by other means. Ask the user to type
  `/design`, and prepare the artboards before they do.

## Slide loops to video, and video in a hand-built .pptx (2026-09-25)

Looping slides rendered to video and embedded in a hand-built `.pptx` cost these retries:

- **`browser_run_code_unsafe` has no `require`.** Put the renderer in a file and pass it as
  `filename`. Open a fresh context with `viewport` 1920 by 1080 and `deviceScaleFactor: 1`, and throw
  if `devicePixelRatio`, `innerWidth` or `innerHeight` is off: one new context came up at 0.67.
- **A loop's time 0 is not the static slide.** A video whose poster is the static slide snaps to
  its first frame when playback starts. Find loop times whose frame equals the static render and
  start there: rotate the frames for the video, and give each CSS track a negative
  `animation-delay` on the canvas. Compare shapes, not pixels: Chrome draws text with LCD
  antialiasing on a still page and greyscale inside animated layers, so no animated frame matches
  the still pixel for pixel. Threshold the difference at 16, then erode 3 by 3.
- **The video extension id must be exact.** `<p:ext uri="{DAA4B4D4-6D71-4841-9C94-3DE7FCFB9230}">`
  holds `p14:media`. A mistyped id still opens, but PowerPoint reports the clip as 0 ms with blank
  settings. To get PowerPoint's own XML, insert the clip through COM (`AddMediaObject2`) into a
  windowless presentation, `SaveAs`, and unzip it. Its `PlayOnEntry` writes an on-click effect;
  "start automatically" is the main-sequence `onBegin` plus `afterEffect` form, and mute is
  `mute="1"` on `p:cMediaNode`.
- **Test slide-show playback without taking the screen:** open a copy windowless,
  delete the other slides, run `CreateVideo`, and compare its frames with the clip.
- **A Design canvas publish after a context reset is refused** ("haven't viewed the latest
  version") even when the version is unchanged. A `read` with `paths` did not count; a plain
  `read` of the canvas URL did.

## Modal: launch, container, volume, and billing quirks (2026-09-21 to 2026-09-24, restored 2026-09-29)

Observed on modal 1.5.x during multi-hour GPU experiments in the previous project. Restored when Modal became this project's primary compute.

1. **`modal run` without `--detach` dies with the local connection.** A network drop on this machine (`socket.gaierror`, then `ConnectionResetError`) tore down the whole remote app, GPU container included, not just the log stream; `modal container list` showed nothing to reconnect to. Pass `--detach` on any run longer than a few minutes, from the start. A detached run is watched with `modal app list`, `modal app logs <app-id>`, and `modal volume get` on its checkpoints.
2. **App creation is rate-limited.** Five `modal run` invocations within seconds got two rejected with `RESOURCE_EXHAUSTED` / `App create rate limit exceeded`, exit code 1, before any container started. Stagger concurrent launches by 60 s or more, and reconcile the artifact count against the expected cell count before aggregating a sweep.
3. **Long GPU containers get preempted and restart from zero.** A pass was preempted 57 minutes in with nothing to resume from, roughly one preemption per four-hour pass. Anything expected to run beyond about an hour needs checkpointing designed in before launch: split the work into slices, write a volume checkpoint per slice, and make the launcher resume from the last one.
4. **A warm container is reused across `Function.remote()` calls**, so filesystem changes persist into the next call. A container-side patch succeeded on the first call and hit an already-patched tree on the second. Make container-side mutation idempotent.
5. **`modal volume get <vol> <id> <dest>` with a non-existent `<dest>` concatenates the whole run directory into one file** and reports success. The local parent must already exist; the reliable form is `modal volume get <vol> <run_id> <existing-parent>`. Re-fetching into an existing directory refuses without `--force`. `dir/*` globs are no longer accepted. Verify the fetched file count, not the exit code.
6. **`modal run <file>` refuses to choose** once the file defines more than one local entrypoint; name it: `file.py::entrypoint`.
7. **The streamed log is not strictly ordered.** `grep ... | tail -1` showed batch 1 while batch 26 was already logged. Take the maximum, never the last line.
8. **Redirected Modal output needs `PYTHONIOENCODING=utf-8`** on Windows (the check-mark entry above); the CLI prints one at startup.
9. **Billing:** `modal billing summary` runs ahead of `modal billing report` by up to about $11 and converges an hour later; quote the per-app report. `modal app list` drops stopped apps after about two hours, so the billing report is the lasting record. An A10G request can land on an A10 (billed as A10G); record the GPU per attempt.
10. **Compiled CUDA extensions in a plain image fail fast.** A `flash-attn` pin failed at metadata generation in `modal.Image.debian_slim()` (no `packaging`, no `torch`, then no `nvcc`). Before reaching for a CUDA-devel image and a 20-minute compile, check for a PyTorch-native alternative such as `attn_implementation="sdpa"`.

## chromadb: open copies only, and 0.5.0 rebuilds the index on every open (2026-09-23)

A newer chromadb migrates an older store's sqlite schema **in place** when it opens it, so open a
copy, never a shipped store. And chromadb 0.5.0 rebuilds the HNSW graph on every open when the
store ships without `index_metadata.pickle`, so top-1 retrieval varied by 0 to 2 of 400 queries
between process starts. If a result depends on retrieval, freeze the retrieved results once in a
committed cache rather than re-querying.

## A run folder holds hand-written notes too; a rerun must not wipe them (2026-09-29)

`experiment_dir(..., overwrite=True)` was changed to empty the folder so stale outputs of an
earlier run cannot masquerade as current ones. The first rerun then deleted `findings.md`,
which had been written by hand into the same folder minutes earlier. The function now keeps
`findings.md` and removes everything else; anything else a person writes into a run folder
needs the same treatment, or a home outside it. Write notes after the final rerun, and check
`git status` for a vanished file after any overwrite.

## pandas 3 string columns are not numpy dtypes (2026-09-29)

pandas 3.0 stores text columns as its own `StringDtype`, and `np.issubdtype(series.dtype, ...)`
raises `TypeError: Cannot interpret '<StringDtype(...)>' as a data type` on them. A test that
classified feature columns this way failed on the first string column. Use
`pd.api.types.is_numeric_dtype` / `is_string_dtype` (they accept the Series itself), and expect
`object` to be rare in frames pandas built from Python strings.

## Renaming the project folder breaks the uv venv's script launchers (2026-09-29)

After the repository folder was renamed, `uv sync` reported success and `uv run python -c
"import dico_nli"` worked, but `uv run pytest` died with `error: uv trampoline failed to
canonicalize script path`. The `.venv/Scripts/*.exe` launchers embed the absolute path of the
interpreter at install time (`strings .venv/Scripts/pytest.exe` showed the old folder), and
`uv sync` only reinstalls packages whose spec changed, so the stale launchers survive. Fix: delete
`.venv` and run `uv sync` again; `uv run python -m pytest` also works in the meantime. Do this on
every machine where the folder moves; the `prompt =` line in `.venv/pyvenv.cfg` still naming the
old project is the tell.
