# Paper

Source for the Assignment 3 paper-style report and its figures. Figures are generated from committed results under `experiments/`, never pasted from a notebook.

## Build

From this folder, with a LaTeX distribution installed:

```
latexmk -pdf main
```

or `pdflatex main && bibtex main && pdflatex main && pdflatex main`. The source also compiles on Overleaf: upload this folder and set `main.tex` as the main document.

## Layout

| File | Section | Owner |
|---|---|---|
| `main.tex` | Preamble, title, the order of the sections, the heading of section 8 | Fawwad (nobody else edits it) |
| `sections/01-abstract.tex` | 1 Title and Abstract | Fawwad |
| `sections/02-introduction.tex` | 2 Introduction and Research Questions | Fawwad |
| `sections/03-related-work.tex` | 3 Related Work | Aqib |
| `sections/04-task-and-dataset.tex` | 4 Task and Dataset | Ahmad |
| `sections/05-method.tex` | 5 Proposed Method | Fawwad |
| `sections/06-experimental-setup.tex` | 6 Experimental Setup | Fawwad |
| `sections/07-results.tex` | 7 Results | Shaheer |
| `sections/08a-ablation-analysis.tex` | 8.1 Ablation Analysis (starts with `\subsection`) | Shaheer |
| `sections/08b-error-analysis.tex` | 8.2 Error Analysis (starts with `\subsection`) | Ahmad |
| `sections/09-comparison.tex` | 9 Comparison with Relevant Work | Aqib |
| `sections/10-discussion.tex` | 10 Discussion and Limitations | Aqib |
| `sections/11-conclusion.tex` | 11 Conclusion and Future Work | Fawwad |
| `sections/A-appendix.tex` | Appendices | Fawwad collects them |
| `references.bib` | 12 References (starts as the Assignment 2 file) | Fawwad |
| `references-shaheer.bib`, `references-ahmad.bib`, `references-aqib.bib` | New entries from each author, folded into `references.bib` at the end | Each author |

## Rules for a section

- Replace your placeholder file. Keep its `\section{...}` (or `\subsection{...}`) heading and its `\label{sec:...}`, so cross-references from other sections keep working.
- Labels: `sec:introduction`, `sec:related`, `sec:task`, `sec:method`, `sec:setup`, `sec:results`, `sec:analysis`, `sec:ablations`, `sec:errors`, `sec:comparison`, `sec:discussion`, `sec:conclusion`. Prefix your tables and figures `tab:` and `fig:`, and refer to them with `\cref`.
- The macros `\EQ`, `\FW`, `\BW`, `\NO`, `\SoftCons`, `\HardCons`, `\Rev`, `\JS` and `\CE` are defined in `main.tex`, as in the Assignment 2 report.
- Figures go in `figures/` as PDF with ASCII-only labels, copied from the `experiments/` folder that generated them.
- A new reference goes into your own `references-<name>.bib`. Check `references.bib` first; cite an entry that is already there instead of adding it again.
- Build the paper before you push, and do not commit build files (`main.pdf`, `.aux`, `.bbl`, `.log` and the like).
