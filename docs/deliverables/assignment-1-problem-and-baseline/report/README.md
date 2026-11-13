# Assignment 1 report

LaTeX source of the Assignment 1 report, on the ACL template in preprint mode (named authors, page numbers, no line numbers). `acl.sty` and `acl_natbib.bst` are the official files from `github.com/acl-org/acl-style-files`.

| File | Holds |
|---|---|
| `main.tex` | Preamble, title, abstract, and the section includes |
| `sections/` | One file per section of the brief: 01 introduction to 11 next steps, then limitations and the run appendix |
| `references.bib` | BibTeX; Anthology entries where they exist, the rest checked at their source |
| `figures/` | The three figures used, copied from the run folders under `experiments/` |

## Build locally

From this folder, with a TeX distribution installed:

```
latexmk -pdf main.tex
```

On Windows with MiKTeX, build from a copy of the folder if you want the auxiliary files out of the repository; BibTeX looks for `acl_natbib.bst` next to `main.aux`.

## Upload to Overleaf

In the Overleaf project, click **Upload** and drag in `main.tex`, `references.bib`, `acl.sty`, `acl_natbib.bst` and the `sections` and `figures` folders, replacing the template's files when asked. In **Menu**, set **Main document** to `main.tex`, then delete the template's own example files. Overleaf compiles with pdfLaTeX by default, which is what this source expects. To start a fresh project instead, zip this folder and use **New Project**, then **Upload Project**.

If a figure changes, regenerate it from its notebook and copy it here again; the figures are copies, not links.
