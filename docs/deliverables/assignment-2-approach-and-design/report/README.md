# Assignment 2 report

LaTeX source of the Assignment 2 report, on the ACL template in preprint mode (named authors, page numbers, no line numbers). `acl.sty` and `acl_natbib.bst` are the official files from `github.com/acl-org/acl-style-files`. The built PDF is `../SemEval_Task2_DiCo_NLI_Group_9_Assignment_2.pdf`.

| File | Holds |
|---|---|
| `main.tex` | Preamble, title, and the section includes |
| `sections/` | The abstract, one file per section of the brief (01 proposed approach to 11 planned experiments), and `A-appendix.tex` |
| `references.bib` | BibTeX for the whole report; every entry was checked at its source |
| `figures/` | `architecture.pdf`, the system diagram |

The main text has the length of the Assignment 1 report: it ends on page 8, before the references. The appendix holds the detailed tables (evidence, ablations, training settings, implementation parts, run list) and the protocol in full.

Who wrote what: sections 1, 8 and 9 Syed Fawwad Ahmed; sections 2 and 3 Ahmad Imran; sections 4, 5, 7 and 11 Aqib Raza; sections 6 and 10 M. Shaheer Saleh. The sections were then edited together into one text.

## Build locally

From this folder, with a TeX distribution installed:

```
latexmk -pdf main.tex
```

On Windows with MiKTeX, build from a copy of the folder if you want the auxiliary files out of the repository; BibTeX looks for `acl_natbib.bst` next to `main.aux`.

## Upload to Overleaf

In the Overleaf project, click **Upload** and drag in `main.tex`, `references.bib`, `acl.sty`, `acl_natbib.bst` and the `sections` and `figures` folders. In **Menu**, set **Main document** to `main.tex`. Overleaf compiles with pdfLaTeX by default, which is what this source expects.
