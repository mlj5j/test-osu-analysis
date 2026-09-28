---
name: hep-slides
description: Build a HEP analysis talk or status update as slides -- LaTeX Beamer (primary, PDF) with an optional editable .pptx export -- covering talk structure, one-message-per-slide layout, figure conventions for slides (mplhep CMS style, labels, legends, uncertainties), building/compiling, and a pre-delivery slide check. Use whenever a task asks for slides, a presentation, a talk, a group-meeting/status update, a conference or approval-meeting deck, or a Beamer/pptx file for a physics analysis. Do not use this for the analysis's own physics content (what the plots show, selections, backgrounds) -- see that analysis's own skills -- or for a non-physics deck.
---

# HEP Slides

Generic, analysis-independent guidance for turning existing analysis results into a
talk. An analysis's own talk outline, standard plots, and approval status belong in
that analysis's own skill layered on top of this one.

Adapted from the plotting and rendering-review conventions in
`references/OSU-Agentic-Analysis` (`src/methodology/appendix-plotting.md`,
`src/agents/plot_validator.md`, `src/agents/rendering_reviewer.md`,
`src/conventions/preamble.tex`). That reference has no slide-specific content, so the
talk structure and Beamer/pptx mechanics below are new, not lifted from it -- treat
them as a first draft to refine with real use.

## 0. Ask first

Before drafting, pin down (ask the user rather than guessing):

- **Audience and slot length** -- group meeting (deep, many slides), collaboration
  approval/pre-approval (rigorous, backup-heavy), conference (~1 slide/minute,
  polished). This sets slide count and depth.
- **Approval status** -- whether results may carry a CMS "Preliminary" label, or
  are internal/unapproved. Never assume; a wrong label on a shared deck is a real
  problem. Default to the most conservative (no approval claimed) and say so.
- **Format** -- Beamer PDF (default) and/or .pptx.
- **Which results** -- point at the actual plots/tables/output files; never invent
  numbers, and never restate a number without tracing it to a file or the user.

## 1. Structure

One message per slide; **every** slide title (including "Status" and "Next steps"
slides -- "Two datasets left to finish", not "Status") states the takeaway ("Fake-track background
is 12% of the total"), not a topic ("Backgrounds"). Typical order:

1. Title
2. Motivation / physics goal and signal signature (1-2 slides)
3. Analysis strategy overview (one diagram or flow)
4. Object and event selection (a cutflow table beats a paragraph)
5. Backgrounds -- one section per estimate: method, control region, validation
6. Systematic uncertainties (summary table, then only the dominant ones in detail)
7. Results -- data vs. prediction, then the statistical interpretation (limits)
8. Summary and next steps (concrete, dated where possible)
9. **Backup** -- everything a likely question would reach for: extra
   distributions, closure tests, per-year/per-channel breakdowns, cutflow details

A talk with no physics figures (a production/infrastructure status update) is fine:
use a "where things stand" summary slide, one table or short list per workstream with
counts and named blockers, then next steps. State the as-of date of the source on the
title slide, since such status goes stale quickly.

For an approval- or review-style talk, two habits from the group's earlier approval
talk are worth keeping: tag each table/figure with its source (note section, output
file, or paper), and put a short "since the last review" call-out on each slide so
reviewers see exactly what changed. A section navigation bar in the footer helps in
long talks.

Rules of thumb: ~1 slide/minute of talk; at most ~4 bullets of at most ~2 lines; a
figure slide has one figure (or two side by side) plus a one-line takeaway; put
detail in backup rather than shrinking text. Say plainly on the slide when a check
fails or a result is preliminary -- do not soften it (same principle as the
reference's "if the closure test fails, say it fails").

## 2. Figures for slides

Full rules in [references/slide-figures.md](references/slide-figures.md). Key points:

- Produce figures with `mh.style.use("CMS")` at `figsize=(10, 10)` (ratio panel via
  `height_ratios=[3, 1]`, `hspace=0`), save PDF+PNG with `bbox_inches="tight"`.
  Never override font sizes -- **size them in Beamer by height**
  (`\includegraphics[height=0.72\textheight]{...}`), which keeps fonts consistent
  across plots with and without colorbars.
- No `ax.set_title` -- the slide title is the title. Experiment label on every
  independent axes via `mh.label.exp_label`.
- Human-readable axis/legend labels, never code identifiers.
- Derived quantities (ratios, efficiencies, normalized distributions) need explicit
  `yerr`; mplhep's sqrt(N) is only right for raw counts.
- Every plot must be read as an image before it goes on a slide (legend overlap,
  legibility at projected size, absurd error bars).

## 3. Beamer (primary)

Start from [references/beamer-template.tex](references/beamer-template.tex) (16:9,
Madrid theme, no external theme dependency, a title-takeaway frame pattern, figure
and table frames, backup section). Build with:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error talk.tex
```

The reference builds with `tectonic`; use whichever of `latexmk`/`pdflatex`/`tectonic`
exists on the machine (`which` them -- do not assume). Run enough passes for
references/outline to resolve (`latexmk` does this automatically).

## 4. .pptx export (optional)

Only when the user wants an editable deck. Use the `anthropic-skills:pptx` skill for
the mechanics, and keep parity with the Beamer content: same slide titles, same
figures (use the **PNGs**, `dpi=200`), same backup section. Beamer stays the source
of truth for structure; do not let the two decks drift -- if both are requested,
generate the pptx from the same slide list rather than editing it by hand afterward.
`python-pptx` and `mplhep` may not be installed locally -- check before assuming.

## 5. Check before delivering

Adapted from the reference's rendering reviewer -- treat each as must-fix:

- Build succeeds with no errors; no `??` (unresolved ref) or `[?]` (unresolved
  citation) anywhere in the rendered PDF.
- No `Overfull \hbox`/`\vbox` warnings large enough to clip content; nothing runs
  off a slide.
- Render the PDF pages to images and **look at them** (e.g. `pdftoppm -r 60 -png`),
  not just the log -- check figure legibility at slide size, overlap, empty
  slides, orphaned titles.
- Every number, cut value, and uncertainty on a slide traces to a file or the user.
- Approval labelling matches what was agreed in step 0.
- Body text is legible at projected size (template default is 12pt; do not shrink
  below it -- move content to backup instead).
- Slide count fits the slot; anything past it is moved to backup.
