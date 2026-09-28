---
name: pocketcoffea-datacards-limits
description: Turn a merged PocketCoffea .coffea output into CMS Combine datacards (pocket_coffea.utils.stat's Datacard/MCProcess/DataProcess/SystematicUncertainty/combine_datacards), then run combineCards.py/text2workspace.py/combine and turn the resulting limit trees into exclusion/limit plots. Use for any PocketCoffea analysis producing a statistical result -- declaring datacard processes/systematics, building a per-category Datacard, combining categories into a workspace, running AsymptoticLimits (or another Combine method), and plotting an exclusion curve/contour from higgsCombine*.root. Do not use this for the PocketCoffea config/processor conventions that produce the input histograms in the first place (cuts, categories, weights) -- see pocketcoffea-conventions -- or for an analysis's own signal grid/process list, which belongs in that analysis's own skill layered on top of this one.
---

# PocketCoffea Datacards and Limit Plots

This is the generic, framework-level half of turning a PocketCoffea histogram output
into a published exclusion plot. It covers the mechanics that are the same for any
PocketCoffea analysis: the `pocket_coffea.utils.stat` datacard API, and the
CMSSW+Combine execution/plotting steps downstream of it. An analysis's own process
list, systematics, signal grid, and plot styling belong in that analysis's own skill,
layered on top of this one (see `disapptrks-datacards-limits` in `disappearing_tracks`
for an example of that layering).

If asked only to write PocketCoffea config/processor code that *produces* the
histograms this skill consumes (cuts, categories, weights, `HistConf`), use
`pocketcoffea-conventions` instead -- this skill starts from an existing
`output_*.coffea` file.

## Establish the current interface

This toolkit is newer and less stable than the rest of PocketCoffea; re-check before
proposing code:

1. Find the analysis's `ref/PocketCoffea` clone (see that analysis's `CLAUDE.md`
   reference-clone table).
2. Read `docs/statistical_analysis.md` in full -- it is the canonical, example-driven
   walkthrough this skill is condensed from.
3. Read `pocket_coffea/utils/stat/combine.py` (the `Datacard` class and
   `combine_datacards`) and `pocket_coffea/utils/stat/systematics.py`/`processes.py`
   for the actual current constructor signatures -- the doc can lag the code (a
   commented-out `shape_only_for_rateparam`/`rateparam_norm_categories` section in
   `combine.py`, present in the docstring but explicitly marked not-yet-live in
   `docs/statistical_analysis.md` on at least one branch, is a confirmed example of
   this). If a keyword argument documented below raises `TypeError`, trust the source
   over this skill.
4. If a law-based (`luigi`) pipeline is in use, `pocket_coffea/law_tasks/tasks/
   datacard.py` shows the `DatacardProducer` task -- the same `Datacard` call, driven
   by a `stat_config` module instead of an ad hoc script.

## Route by task

- Building the datacard/workspace itself (processes, systematics, one `Datacard` per
  category, combining categories), read
  [references/datacard-api.md](references/datacard-api.md).
- Running Combine on the resulting workspace and turning the limit tree into an
  exclusion/limit plot, read
  [references/combine-execution.md](references/combine-execution.md).

## Framework invariants to preserve

- **Every `(process, year)` pair is its own datacard column** (`"{process}_{year}"`);
  only `data_obs` is summed across years into a single column. A systematic's
  correlation across years is controlled entirely by which `years` each
  `SystematicUncertainty` object covers -- don't try to encode correlation any other
  way (e.g. by hand-editing the written card).
- **`Systematics` keys on `datacard_name`.** Two `SystematicUncertainty` objects that
  should be independent nuisances must have different `datacard_name`s, even if they
  share a `name` (the coffea variation to look up); two that should be one correlated
  nuisance spanning several `years` groups must share the same `datacard_name`.
- **A `shape` systematic's `name` is a coffea variation, not a nuisance name.** The
  code looks up `f"{coffea_name}{shift}"` (or the per-process alias from
  `coffea_name_alias`) on the histogram's `variation` axis, and writes
  `f"{datacard_name}{shift}"` into the card -- conflating the two when renaming a
  nuisance per-year (`datacard_name=f"{syst}_{year}"`, `coffea_name_alias=syst`) is the
  documented pattern for decorrelating a shared variation by year; don't invent a
  differently-named variation on the histogram side to achieve the same thing.
- **Negative bin content is silently clipped to zero before being written to ROOT**
  (`_clip_negative_bins`), with a warning naming the shape -- Combine cannot handle
  negative templates. `Datacard.rate()` applies the identical clip before summing so
  the declared `rate` line matches the written template's integral; don't "fix" a
  negative-yield warning by editing the card's `rate` line by hand, since that would
  desync it from the actual shape.
- **`mcstat=True` (the default) writes an `autoMCStats` line** with
  `threshold=0, include_signal=0, hist_mode=1`. Passing a dict overrides only the keys
  given; an unrecognized key raises `ValueError` rather than being silently ignored.
- **A non-signal process needs `has_rateParam=True` to float.** The `rateParam` line
  (`SF_<name> rateParam * <name>_<year> 1 [0,5]`) is emitted automatically per
  `(process, year)` for every such process -- don't hand-write a `rateParam` line into
  a card built by `Datacard.dump`; add it via the `MCProcess` declaration instead so it
  stays consistent with everything else the class derives from that process (its id,
  its entry in `expectation_section`, etc.).
- **`combine_datacards` only writes a shell script** (`combineCards.py`/
  `text2workspace.py` invocations); it does not run Combine. That script needs a
  CMSSW+Combine environment to actually execute -- see
  [references/combine-execution.md](references/combine-execution.md).

## Completion checks

- State which `.coffea` file, which categories, and which years the datacards were
  built from.
- For each `Datacard`, confirm no unexpected "missing histogram for sample" /
  "missing the following systematics" / shape-differs-by->100%-from-nominal messages
  were printed during construction -- these come from `_check_histograms`/
  `_check_shapes` and usually mean a sample, year, or variation name doesn't match
  what's actually in the `.coffea` output.
- Before trusting a limit: confirm the combined workspace's `text2workspace.py` step
  ran without error, and that the datacard's declared processes/`rate`s match what was
  intended (an accidentally-omitted background, or a signal process with the wrong
  `is_signal`, silently produces a wrong but plausible-looking limit).
- State whether the reported limit/exclusion came from an actual `combine` run on real
  Combine output, or is illustrative/untested.
