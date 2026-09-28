---
name: disapptrks-slides
description: Build a disappearing-track analysis talk or status update -- which results to pull from DisappTrks_Nano/PocketCoffea output for each slide (signal selection and highPurity/dE/dx decision, electron/muon/tau lepton backgrounds, fake-track background, search-region yields, limits, OSUv2 NanoAOD production status), where each number comes from, and which numbers are stale, unvalidated, or not yet produced and must be flagged on the slide. Use whenever asked for slides, a presentation, a group-meeting or approval-meeting update, or a status talk for the disappearing-tracks analysis. Layered on the root hep-slides skill, which supplies the generic structure, figure conventions, Beamer template, and build/check steps -- read that first; do not use this for producing the numbers themselves (see the disapptrks-* physics skills).
---

# Disappearing-Tracks Slides

The analysis-specific layer on top of the root `hep-slides` skill. Read that first for
talk structure, figure rules, the Beamer template, and the pre-delivery check; this skill
only adds what is particular to this analysis: which output feeds which slide, and what
must be qualified on the slide rather than presented as settled.

**This skill never produces a number.** Every yield, efficiency, and uncertainty on a
slide comes from a real output file (or from the user), produced by the relevant
`disapptrks-*` skill. If the number does not exist yet, the slide says so.

## Before drafting

Ask (per `hep-slides` step 0), plus these analysis-specific points:

- **Which run periods** (2022CD, 2022EFG, 2023C, 2023D, 2024, 2025 ...) and which
  layer bins (`NLayers4`/`NLayers5`/`NLayers6plus`/`combinedBins`) the talk covers.
- **Which checkout produced the outputs.** Confirm
  `git -C ref/DisappTrks_Nano branch --show-current` and that the outputs were made at
  a commit that includes the fixes below -- see "Provenance flags".
- **Approval status** -- nothing in this repo records that any result is approved for a
  "Preliminary" label; default to none.

## Slide-to-source map

| Slide topic | Source of the content | Skill that produces/explains it |
| --- | --- | --- |
| Physics goal, signal (chargino AMSB, mass/lifetime) | Dissertation ch. 7 (M. Carrigan, OSU 2025) -- the group's reference PDF; `ref/DisappTrks` legacy code | `disapptrks-datacards-limits` (signal grids) |
| Track selection, incl. `highPurity` + dE/dx | `search_track_mask` in `src/disapptrks/selections.py` | `disapptrks-signal-acceptance`, `disapptrks-track-diagnostics` |
| Cost of `highPurity` (signal efficiency per layer bin) | `summarize-signal-high-purity` output | `disapptrks-signal-acceptance` -- present as the *historical* cost that was weighed, not a pending decision |
| Fake-track vs. real-track discrimination (dE/dx) | `high_purity_study` Z-sideband PDFs | `disapptrks-track-diagnostics` |
| Lepton backgrounds (e, mu, tau): P_veto, P_offline, P_miss, N_est | `estimate-lepton-background` / `estimate-tau-background` JSON+TeX | `disapptrks-lepton-backgrounds` |
| Fake-track background (zeta, N_fake) | `make-standard-fake-track-estimate` -> Table-34-style TeX, fit PDFs | `disapptrks-fake-track-background` |
| Total background table (leptons + fakes) | `combine-total-background-table` | `disapptrks-lepton-backgrounds` (multi-period section) |
| Search-region yields | `search_region` mode, 1-bin `searchRegionYield_<layer>` histograms | `disapptrks-datacards-limits` |
| Limits (wino/higgsino exclusion vs. mass/lifetime) | Combine output | `disapptrks-datacards-limits`, root `pocketcoffea-datacards-limits` |
| Infrastructure/status (NanoAOD OSUv2 production) | `nano_v2_migration_checklist.md` | `disapptrks-nano-production-pass` |

Prefer the analysis's own LaTeX table outputs (`--output-tex`, `combine-*-table`) via
`\input` over retyping numbers into a slide -- retyped numbers drift from the source.
Per-period JSON outputs live under `tables/` and `analysis_output/<period>/...`; ask
where the user's current outputs are rather than assuming.

## Provenance flags -- check each before the slide goes out

These are known, documented caveats. Each one that applies gets stated on the slide
(a footnote or a "Status" line), not left for the audience to discover.

1. **Fake-track estimate vs. current selection.** The fake-track yield estimate
   predates `highPurity` + dE/dx being required in the production selection. Check
   whether it has been re-derived under the current selection; if not, label it as
   computed under the earlier selection. Do not present it as the final background.
2. **No datacard/limit yet from `search_region`.** The mode's categories and yields are
   verified, but no `Datacard` has been built from it. A limits slide is either an
   explicit projection/legacy comparison, or absent -- never a placeholder curve.
3. **Lepton-background outputs and the Pveto category bug.** `estimate-lepton-background`
   / `estimate-tau-background` outputs from a checkout at or before `MattDev`
   `5414789` predate commit `7c331f5` (fixed 2026-09-15) and have P_veto silently
   forced to 0 for all four flavors. Confirm the outputs postdate it before trusting any
   P_veto/N_est value.
4. **Tau SS > OS.** SS exceeding OS pass counts in `tau_mu_pveto`/`tau_ele_pveto`
   (2-15x, driving OS-SS-subtracted P_veto to ~0) is expected per Matt, not a bug. If a
   tau slide shows N_tau ~ 0, say it is the expected shape of this control region and
   is statistically limited in early periods -- do not hide it and do not present it
   as a discovery-level statement about tau backgrounds.
5. **dE/dx working point.** The max/median dE/dx cut applies only to `NLayers4`/
   `NLayers5`; `NLayers6plus`/`combinedBins`-tail tracks always pass it (there is no
   plan for a 6plus working point). Say so wherever a per-layer-bin yield or efficiency
   is shown, or the layer bins look inconsistently treated.
6. **Signal MC coverage.** At least one local dev signal MC file predates the
   `IsoTrackDeDxHit` branch (needs `DISAPPTRKS_SEARCH_REQUIRE_DEDX_CUT=0`). A signal
   yield made that way is not production-representative -- say which was used.
7. **Fiducial maps.** Confirm both were loaded (nonzero
   `nElectronFiducialHotSpotsLoaded`/`nMuonFiducialHotSpotsLoaded`) before showing a
   production-representative number.
8. **Dissertation numbers are not this analysis's numbers.** The dissertation
   (Run 2/early Run 3, no `highPurity`) is the method reference, not a source for
   current yields. Do not put a dissertation number next to a Nano-tier number without
   labelling which is which and that the selections differ.
9. **Verification level.** If an output was verified only at the CLI/config level and
   not through an end-to-end PocketCoffea run, do not show it as a result.

## Suggested structure for this analysis

Follows the generic `hep-slides` order; adjust to the slot:

1. Title
2. Signal: long-lived chargino, disappearing-track signature
3. Selection (cutflow table), with the `highPurity` + dE/dx requirement and its
   per-layer signal cost (historical decision)
4. Background overview: leptons (e, mu, tau) and fake tracks, one method slide each
5. Per-flavor lepton backgrounds: P_veto/P_offline/P_miss -> N_est table
6. Fake-track background: transfer-factor fit + yield table, with flag 1 if it applies
7. Total background vs. observed (only if both actually exist for the same selection)
8. Limits (only if flag 2 is resolved) or an explicit "in progress" slide
9. Status and next steps -- concrete: which periods are done, which are blocked and on
   what (e.g. OSUv2 migration state from `nano_v2_migration_checklist.md`)
10. Backup: closure tests, per-period/per-layer tables, dE/dx study plots, cutflow
    details

For a group-meeting *status* talk, slides 2-4 can be one recap slide and most of the
time goes to 5-9; for an approval-style talk, invert that and keep slide 9 short.

## Conventions from the previous iteration (EXO-19-010 approval talk, 2019)

The group's earlier (2017-18) approval talk is the reference for how this analysis's
talks are organized. Reuse its *structure and conventions*; never its numbers -- those
are a different dataset and selection, and the yields, limits, and systematic tables
must not be presented as current results (see also the rule against dissertation
results tables).

- **Section navigation bar** in the footer (Intro / Selection / Backgrounds / Signal /
  Results / Conclusion) so the audience can see where they are in a long talk.
- **Title slide** carries the author list, both institutions' logos, the review
  links (analysis note version, paper draft, review twiki/hypernews) when they exist.
- **Source tag on every result slide** ("AN", "Paper") in the 2019 talk. This deck
  style does not print sources on the slides (they were removed from the footer);
  still trace every number to its source and list the sources in the hand-off
  message instead.
- **"Since <last review stage>" call-out** on each slide (e.g. "Unchanged since PA",
  "2018 added, no other changes"). For an approval or status talk, add the equivalent
  "Since last update" box -- it is the fastest way for reviewers to see what changed.
- **Annotated formulas**: the background formula is drawn once with arrows labelling
  each factor ("probability to pass the lepton veto, measured with tag-and-probe",
  "single-lepton control region"), rather than a bare equation.
- **Per-background arc**: method slide(s) -> systematics slide (with the size range and
  how it was derived) -> closure test. Systematics and closure are part of a
  background's story, not appendix material, in an approval-style talk.
- **Signal side**: corrections (hits, trigger efficiency, ISR) and a systematics
  summary table, before the expected-events table and the interpretation.
- **Expected-events table** lists per period and `n_layers` bin leptons, spurious
  tracks, total, and (once unblinded) the observation -- the same layout the current
  `total_background_combined.tex` follows.
- **Conclusion** states what is requested/next (e.g. proceed to collaboration-wide
  review, publication) and what changed since the previous review.
- **Backup** holds fiducial-map details, per-flavor probability tables, closure, and
  comparisons with other experiments.
- **Cross-check for the selection slide**: the 2017-18 track selection (pT > 55 GeV,
  |eta| < 2.1, >= 4 pixel hits, no missing inner/middle hits, |d0| < 0.2 mm,
  |dz| < 5 mm, isolation < 0.05 pT, dR > 0.5 from jets, dR > 0.15 from leptons,
  E_calo < 10 GeV, >= 3 missing outer hits; basic selection with MET(no mu) > 120 GeV,
  a >= 110 GeV tight jet, dphi(jet, MET) > 0.5) agrees with `search_track_mask` in
  `DisappTrks_Nano` -- a useful sanity check, but always re-read the code for the
  current values since the Run 3 selection has since gained `highPurity` and dE/dx.

## Template

Start a new deck from [references/talk-template.tex](references/talk-template.tex)
(16:9, 12pt Beamer; compiles as-is with placeholders). It builds in the conventions
above: a section navigation bar in the footer (Intro / Selection / Backgrounds /
Signal / Results / Conclusion, backup excluded), and a `\sincebox{...}` (red, bottom right) macro, an annotated-formula frame, and
per-background method / systematics / closure frames. `\slidefig` and `\slidetable`
fall back to a labelled TODO box when a figure or table file is missing, so the deck
builds before the real outputs exist -- **a TODO box in a delivered deck is a bug**;
grep the PDF text for "TODO" before handing it over. The generic Beamer starter in
`hep-slides` remains the fallback for non-analysis decks. Group logos are not bundled;
ask for the approved files rather than recreating them.

## PowerPoint export

`slides/make_pptx.py` (in the analysis directory, not the skill) writes
`slides/pptx/method_overview.pptx` and `status_update.pptx`. The `.tex` decks stay
the source of truth: the script mirrors each deck's slide list by hand and reads the
numeric tables from the same `slides/tables/generated/*.tex` files Beamer `\input`s, so
numbers cannot drift -- but slide *text* must be updated in both places when a deck
changes. Needs `python-pptx` (install into a throwaway venv; it is not in the base
environment) and `pdftoppm`. Nothing renders these files locally (no LibreOffice on the
usual machine), so open the result in PowerPoint and check overflow by eye.

## Keynote export

Two routes, both scripted in `slides/`. **Editable:** open the `.pptx` from
`make_pptx.py` in Keynote (File > Open, or AppleScript) -- fonts and spacing follow
Keynote's importer. **Pixel-faithful:** `beamer_to_keynote.py` builds a Keynote deck
directly with one full-slide image per compiled Beamer page (page text goes in the
presenter notes); the look matches the PDF exactly but slide text is not editable.
Notes from getting it working: build the deck natively via AppleScript rather than
importing a big image-only `.pptx` (that import hung Keynote for 15+ minutes); create
the document with `width:1920, height:1080` (the default is 4:3 and crops 16:9
images); delete the default first slide *after* adding yours; wrap the script in
`with timeout of 600 seconds` (default Apple-event timeout is 120 s); and keep staging
files under the project, since sandboxed Keynote cannot read the system temp dir.

## Production/infrastructure-only status talks

When the update is about NanoAOD production rather than physics results (no analysis
outputs needed), source everything from `nano_v2_migration_checklist.md`: per-year
counts of datasets cleared vs. outstanding, and each outstanding dataset with its
named blocker (site problem, bad source file, recovery task). Quote the checklist's
own "status as of" date on the title slide and re-check with
`disapptrks-nano-production-pass` first if the user wants current numbers. Keep the
analysis caveats (flags 1 and 2 above) on one slide so the audience does not read
"production nearly done" as "results nearly done".

## Figures

Reuse the analysis's own PDFs where they exist (fit PDFs from
`make-standard-fake-track-estimate --fit-plots`, sideband/high-purity study plots,
`disapptrks` fiducial-map plots) rather than redrawing them. Any figure redrawn for
slides follows `hep-slides/references/slide-figures.md`. Read every figure image
before it goes on a slide -- and check that a reused figure's own label (period,
luminosity, "Preliminary") matches what the slide claims.

## Delivering

Build and check per `hep-slides` sections 3 and 5, then, in the hand-off message, list
which provenance flags above applied and how each was handled on the slides, so the
user can decide whether to soften or strengthen any of them.
