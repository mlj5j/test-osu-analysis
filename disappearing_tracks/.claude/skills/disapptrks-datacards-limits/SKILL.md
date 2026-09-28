---
name: disapptrks-datacards-limits
description: Build DisappTrks_Nano/PocketCoffea datacards and produce the wino/higgsino chargino exclusion (limit vs. mass/lifetime) plot for the disappearing-track search. Use for the analysis's own signal grid (chargino mass/lifetime points), the AMSB wino/higgsino signal cross-section tables and how to patch them into a dataset JSON's xsec metadata, process/systematic declarations against the search_region PocketCoffea mode's staged counting-experiment categories, and the legacy AMSB wino/higgsino plot conventions in ref/DisappTrks/LimitSetting. Do not use this for the generic pocket_coffea.utils.stat Datacard API or generic Combine/exclusion-plot mechanics -- see pocketcoffea-datacards-limits, which this skill builds on.
---

# DisappTrks Datacards and Exclusion Plots

This is the analysis-specific layer on top of the generic `pocketcoffea-datacards-limits`
skill: the DisappTrks signal models, the legacy plot/grid conventions, and what's
actually available to build on today. Read `pocketcoffea-datacards-limits` first for
the `Datacard`/`MCProcess`/`SystematicUncertainty` API and the Combine/plotting
mechanics -- this skill does not repeat that content.

## The `search_region` PocketCoffea mode (added 2026-09-17, restaged 2026-09-18)

`pocket_coffea/config.py` in `DisappTrks_Nano` (`MattDev` branch) now has
`DISAPPTRKS_CATEGORY_MODE=search_region`: a plain `StandardSelection` (no
`CartesianSelection` needed) producing 14 categories -- `inclusive`, `basic_selection`,
and one `isolated_track_<layer>`/`candidate_track_<layer>`/`disappearing_track_<layer>`
triple per layer bin (`NLayers4`/`NLayers5`/`NLayers6plus`/`combinedBins`) -- an
explicit, dissertation-matching (Ch. 7.3.3) cumulative chain, not the single flat
`signal_selection_with_high_purity_<layer>` category this mode originally shipped
with. `disappearing_track_<layer>` (the final stage) reuses that same underlying Cut
(`nIsoTrackSearch_<layer> >= 1`) rather than duplicating it. Confirm the current shape
before relying on details here (`grep -n "category_mode ==" pocket_coffea/config.py`
in the real checkout, not just `ref/DisappTrks_Nano` which may lag).

The selection is the full disappearing-track selection with `isHighPurityTrack`
required and, for `NLayers4`/`NLayers5` only, a max/median dE/dx cut -- see
`disapptrks-signal-acceptance`'s "historical context" section for why both are now
required rather than an open question. The electron/muon fiducial hot-spot veto is
applied consistently across all three stages (`isolated_track`/`candidate_track`/
`disappearing_track`) as of 2026-09-18 -- it was previously applied only to the final
stage, a real bug (not just a display gap) caught by building a per-individual-cut
cutflow table and finding the staged counts weren't monotonic.

Each layer bin gets one 1-bin `searchRegionYield_<layer>` `HistConf` (binned on
`AnalysisEvent.METNoMu_pt`, `only_categories=[f"disappearing_track_{layer}"]`, range
wide enough that every passing event falls in the one bin). **This is a deliberate
counting-experiment design, not a shape variable** -- the histogram's single-bin
integral *is* the category's yield, and `Datacard.rate()` reads it directly. This
matches the legacy `bkgdConfig_*.py` per-era/per-layer-bin structure (see below), not
a shape fit. (A prior version of this `HistConf` pointed `only_categories` at a stale
category name from before the highPurity switch, silently producing empty
histograms -- fixed 2026-09-18, alongside the fiducial fix above, in the same
verification pass.) If a shape discriminant is wanted later, reuse `signal_acceptance`'s
per-track dE/dx summary machinery (`SignalDeDxTrack_<layer>`), built per `search_region`
category instead of gated to `inclusive`.

Verified end-to-end (2026-09-18) against real signal MC that actually carries the
`IsoTrackDeDxHit` branch (`datasets/eos_signal_2022_postEE_OSUv2.json`, AMSB wino
M700GeV, four lifetimes) and real 2025 muon data: the staged per-layer counts are
monotonically decreasing (isolated ≥ candidate ≥ disappearing) and cross-check exactly
against `signal_acceptance`'s independent cutflow on the same files. `muon_pveto`/
`fake_tracks` full cutflows stayed byte-identical across every fix made along the way
(the fiducial fix and the event-weighting fix below are both gated to
`signal_acceptance`/`search_region`, or -- for weighting -- verified not to change any
raw event count anywhere, only weighted yields).

### Event weighting (fixed 2026-09-18)

The `Configurator` previously had `weights={"common": {"inclusive": []}}` and
`weights_classes=[]` -- **no weight classes registered at all**, for any category
mode. Every yield reported before this fix was a raw, unweighted event count. Fixed to:

```python
from pocket_coffea.lib.weights.common import common_weights
...
weights={"common": {"inclusive": ["genWeight", "lumi", "XS"]}, "bysample": {}},
weights_classes=common_weights,
```

- `genWeight`/`lumi`/`XS` are PocketCoffea built-ins (`pocket_coffea.lib.weights.common`)
  -- no custom `WeightWrapper` needed. `lumi` reads `params.lumi.picobarns[year]["tot"]`
  (confirmed `"2022_postEE"` already resolves via PocketCoffea's own default
  `lumi.yaml`, no DisappTrks-specific lumi config needed for that year); `XS` reads
  `float(metadata["xsec"])` straight from the dataset JSON.
- Both default `isMC_only=True`, so `WeightsManager` skips them for data automatically
  -- no `bysample` exclusion needed, and this was verified (`DATA_Muon` job ran clean).
- `sum_genweights` rescaling happens automatically in the base processor's
  `postprocess()` (already invoked by the standard `pocket_coffea.scripts.runner run`
  CLI every job in this analysis uses) -- **do not hand-roll dividing by it.**
- `weights_classes=common_weights` registers the *whole* bundle (pileup, lepton/jet
  SFs, ...) for future use; only `genWeight`/`lumi`/`XS` are actually activated in
  `weights=`. Turning on more (pileup reweighting matters for a real result) is a
  follow-up, not done yet.
- Verified: `cutflow` (raw counts) stayed byte-identical before/after on both a data
  job and a signal-MC job; `sumw`/histogram integrals changed and matched
  `sum_genweights`-rescaled expectations exactly.

### Signal cross sections (fixed 2026-09-18, only for M700GeV wino so far)

Dataset JSONs ship with a placeholder `"xsec": "1.0"` in `metadata` -- with the `XS`
weight now active, this directly becomes the `Datacard` rate's normalization, so it
must be replaced with the real value before any yield means anything.

**Source**: `ref/DisappTrks/SignalMC/python/signalCrossSecs13p6TeV.py` (Resummino
aNNLO+NNLL, matches the `13p6TeV` sample naming; cited from the
[LHCPhysics SUSY cross-sections twiki](https://twiki.cern.ch/twiki/bin/view/LHCPhysics/SUSYCrossSections13x6TeVn2x1wino)).
Two separate tables, keyed by mass in GeV as a string:

- `signal_cross_sections` -- **wino** grid (`AMSB_Wino_...` sample names). Value per
  mass = `chargino_neutralino_cross_sections[mass] + chargino_chargino_cross_sections[mass]`
  (both production modes summed; the legacy file does this itself via its `Measurement`
  class -- read the two dicts directly and sum by hand if reusing just the numbers).
- `signal_cross_sections_higgsino` -- **higgsino** grid, same structure
  (`higgsino_n2c1 + higgsino_c1c1`; note `higgsino_n2c1`'s table already has the "×2
  for degenerate N1/N2" factor baked into its `value` field -- don't apply it twice).
- Both tables store values in **picobarns** (the raw table entries are in fb, converted
  by `* 1.0e-3` in the source file) -- matches the units `XS`/`lumi` expect.
- **Cross section does not depend on lifetime.** One value per mass applies to every
  `ctau` sample at that mass -- confirmed by patching all four lifetime entries in
  `eos_signal_2022_postEE_OSUv2.json`'s M700GeV samples to the same value.

**Worked example (verified end-to-end)**: M700GeV wino =
`11.1063e-3 + 5.18784e-3 = 0.01629414` pb. Patched into all four `AMSB_Wino_M700GeV_*`
entries' `metadata.xsec` in `eos_signal_2022_postEE_OSUv2.json` (JSON-diffed against
the original first, to confirm only `xsec` changed, nothing else in `files`/other
metadata). Re-running `search_region` confirmed the weighted yield scaled exactly
linearly with the new value (`505.53 -> 8.237`, ratio `0.01629414` as expected).

**Still needed to extend beyond this one mass point**: the same two tables cover
masses 100-1200 GeV; each additional mass's dataset JSON entries need the same patch
using that mass's value. This is a small, fixed lookup -- worth scripting (read the
dataset JSON, look up cross-section table by sample-name pattern and mass, write back)
once the full signal grid's dataset JSON exists, rather than patching by hand per mass
point as done here for the one verified case.

## First-pass expected limit (done 2026-09-21: wino, cτ=100cm, 2022EFG only)

A complete first pass exists in `limits/ctau100_2022EFG/` (plot, 12 cards, scripts, and a
README with the provenance and caveats -- read that README before quoting or extending
it). Result: expected mass limit 729 GeV with only lumi/signal-MC-stat/background-estimate
`lnN`s, **719 GeV (±1σ 649-778) after adding the legacy 2022EFG systematics**; **not a
quotable result** (see the README's caveats). The recipe, and the traps that cost time:

- **Dissertation systematics (current best source)**: `DissertationFinal.pdf` in
  `ref/DisappTrks_Nano/docs/` (extract with `pdftotext -layout`). Signal: Table 7.44 (wino, 2022)
  / 7.45 (2023) -- **7.46/7.47 are the higgsino tables**. Background: Sec. 7.5.3, Tables
  7.35-7.38 (electron/tau energy, one-sided Poffline/Ptrigger terms for muon+tau, fake
  transfer-factor + Z->mumu/Z->ee). Encoded in
  `limits/ctau100_2022EFG/dissertation_{signal,background}_systematics_2022EFG.json`;
  `build_cards.py --signal-syst-table ... --background-syst-table ...`. For 2022EFG the legacy
  code's fake/electron/tau values equal the dissertation's, so the mass limit is the same (719 GeV).
- **Multi-era combination (done 2026-09-21, ctau100cm: 798 GeV expected from 2022CD+2022EFG+2023C+2023D)**:
  `limits/combined_run3_ctau100/` (README has the recipe). One signal `search_region` run per era with that era's
  campaign, `--year` (2022_preEE / 2022_postEE / 2023_preBPix / 2023_postBPix), `*_fiducial_map_<era>_v2.json`
  and dataset JSON; backgrounds from `tables/*_<era>_dedx.json`; one card with a bin per (era, layer), per-era
  systematics from Tables 7.44/7.45 + 7.35-7.38. **Combine bin names must not start with a digit** (use `era2022CD_...`).
  Verify `text2workspace` actually succeeded (a failed one still leaves a `higgsCombine*.root`).
- **Full-Run-3 projection (2026-09-21, 1010 GeV at 308 fb-1 after the Ecalo update below; 1008 GeV before)**:
  periods without signal MC reuse a template era's yield scaled by lumi (`build_combined_cards.py --extra-eras`),
  real per-period backgrounds, template systematics; see `limits/combined_run3_ctau100/README.md`. **Combine
  `--rAbsAcc`** must be far below the expected r (default 5e-4 makes low-mass points fail silently at high lumi);
  `run_combine.sh` sets `rMax*1e-4`. lumi.yaml has no 2026 entry (25.31 fb-1 was given by the user).
- **Ecalo, 2018 vs 2023D (2026-09-25)**: comparing the legacy Run 2 (2018AB/CD) signal systematics against Run 3's
  (the only categories tracked in both: lumi, trkReco/track_reco_eff, Ecalo, missing-inner/middle-hits), **Ecalo is
  the only one that grew by more than ~2x** -- 0.37% (2018) -> 20.7% (2023D), 55x, vs everything else flat or a
  few x. `build_combined_cards.py --extra-eras` now supports a separate `systematics_template` field (distinct
  from `template`, which still controls the signal-yield/lumi scaling) so a projected era's *systematics* can be
  cloned from a different source than its yield; used to give 2024/2025/2026 the 2018 Ecalo value instead of
  2023D's 20.7% (a new `2023D_ecalo2018` entry in `dissertation_systematics_by_era.json`, everything else still
  2023D's). Small effect on the mass limit (~2 GeV) since Ecalo is one of ~12 signal systematics on 3 of 7 eras.
- **New lifetime, cτ=1000cm (done 2026-09-25, 576 GeV expected from 2022CD+2022EFG+2023C+2023D)**:
  `limits/ctau1000cm_run3/` -- new `dev_v2` signal MC (`AMSB_Wino_M<mass>GeV_ctau1000cm_...`,
  no `SignalSim/withLifeTime` nesting, `--nano-version 12` since 2022/2023 -> NanoAODv12).
  Reused the ctau=100cm backgrounds/systematics unchanged (lifetime-independent).
  **Spot-check new signal MC before a full production run** (`Jet_jetId`, `IsoTrackDeDxHit`
  present; isolation/pixel-hits/calo-energy in the normal range) -- given the 2024
  ctau=100cm sample turned out to have a broken production (see the handoff doc in
  `limits/combined_run3_ctau100/`). Only 1-4 files per (mass, campaign) here -- expect
  larger MC-stat uncertainty than ctau=100cm. One mass point (M400) had zero files for
  one era (2023D) -- dropped from the whole scan rather than built inconsistently;
  `build_combined_cards.py` now takes the intersection of masses present in every era
  instead of asserting they're identical.
- **cτ=1000cm full-Run-3 projection (2026-09-25, 804 GeV at 308 fb-1 with the 2018 Ecalo value; 802 GeV before)**:
  same recipe as ctau=100cm's projection, 2024/2025/2026 signal scaled from 2023D by luminosity, and the same
  2018-Ecalo `systematics_template` swap. See `limits/ctau1000cm_run3/README.md`. Hit the same transient Combine
  crash as ctau=100cm's projection (one mass's -- M900 both times -- log truncated after the header, no quantiles,
  no ERROR, despite a `higgsCombine*.root` existing) on *both* the original and the Ecalo-updated run -- rerunning
  that one mass fixed it each time. Reinforces: a `higgsCombine*.root` file existing is never enough on its own,
  always check all five quantile rows.
- **Legacy systematics** (`limits/ctau100_2022EFG/scripts/legacy_systematics.py`, then
  `build_cards.py --legacy-systematics ... --xsec ...`): read from
  `ref/DisappTrks/LimitSetting/python/bkgdConfig_<era>_<layer>.py` (background), the flat
  block in `winoElectroweakLimits.py`, and `SignalSystematics/data/systematic_values__*_<era>_<layer>.txt`
  (per dataset; `a` or `a b` -> Combine `a/b`; `0`/`1.0`/`1.0/1.0` rows are OFF). Attach each
  background systematic to its own component's column (so split the bin's background into
  fake/electron/muon/tau processes), keep the estimate's stat error as one `lnN` per bin, and
  do NOT apply the legacy `*_alpha_*` lines (double-counts the estimate's propagated error).
  Legacy values flagged "NEEDS TO BE UPDATED" in the config carry over that flag. Combine
  reads asymmetric `lnN` as `down/up`.

- **Signal MC**: `/store/group/lpcdisapptrks/nano/dev/SignalSim/withLifeTime/`, one
  directory per mass, **each holding four campaigns** -- `Run3Summer22` (2022 preEE =
  2022CD), `Run3Summer22EE` (2022 postEE = **2022EFG**), `Run3Summer23` (2023C),
  `Run3Summer23BPix` (2023D). Building a dataset JSON from the whole directory with one
  `--year` silently mislabels three campaigns' MC (wrong lumi, wrong backgrounds). Build a
  per-campaign filelist first (`make_filelist.sh`: `CAMP=Run3Summer22EEMiniAODv4 OUT=...`),
  then `disapptrks make-dataset-json --filelist <it> --group-signal-points
  --signal-marker withLifeTime --is-mc --count-events --xsec 1.0 --year 2022_postEE
  --era EFG --nano-version 12 --primary-dataset Signal --sample SIGNAL_Chargino`, then patch
  per-mass `xsec` (`wino_xsec.py`/`patch_xsec.py`; the CLI takes one `--xsec` per call).
  These OSUv3 (`charginoOnly`) files carry `IsoTrackDeDxHit` and are a strict superset of
  the OSUv2 branches (only `GenChargino_*` added); M700 reproduces the OSUv2 sample exactly.
- **Backgrounds** are data-driven, so they are *not* built through
  `pocket_coffea.utils.stat.Datacard` (it expects per-sample histograms). Run the three
  estimate commands on `analysis_output/<period>/*_dedx/` (see
  `disapptrks-lepton-background-job-orchestration` Step 4 and
  `disapptrks-fake-track-job-orchestration` Step 4), write to a fresh
  `tables/limits_<period>/` (don't overwrite older JSONs -- the August ones predate the
  2026-09-15 Pveto fix), and read the per-layer values from the JSONs
  (leptons: list of rows, `layer` + `estimate.{value,error}`; fake: `estimates[*].fake_yield`).
  Sum e+mu+tau+fake per bin, errors in quadrature, one `bkg` process per bin as a `lnN`.
  **Tau trigger efficiency**: the dissertation uses a flat 90% (few HLT primitives for
  taus) -- period-independent, so `0.90` is justified from the text; the `± 0.006` was
  carried over unverified. The tau background is ~1e-6 events regardless.
- **Cards**: 3 bins (NLayers4/5/6plus; never `combinedBins` as a 4th bin, it overlaps).
  Signal rate and MC-stat error come straight from `searchRegionYield_<layer>` (weighted
  sum and `variances()`), extracted in the pocketcoffea container (`extract_signal.py`).
  Omit a signal column where the yield is 0. Layer-bin overlap for signal was only 1-2%.
- **Combine**: no CMSSW area needed -- `/cvmfs/unpacked.cern.ch/gitlab-registry.cern.ch/
  cms-cloud/combine-standalone:latest` via `apptainer exec` (see
  `pocketcoffea-datacards-limits`'s combine-execution reference). Run
  `combine -M AsymptoticLimits --run blind` per mass; expected-only, no data needed.
  **Size `--rMax` per mass from the yields** (`build_cards.py` writes `rmax_M<m>.txt`) --
  a huge fixed `--rMax` makes the Poisson underflow and Combine aborts after the first
  quantile while still writing a ROOT file with nonsense values. Always confirm the limit
  tree has all five `quantileExpected` rows and the logs have 0 `ERROR` lines.
- **Plot**: σ_limit = r × σ_theory vs mass, mass limit = log-interpolated r=1 crossing.
  Read `quantileExpected` as float32 → cast to float64 before rounding/matching. The
  container has matplotlib/mplhep/uproot; the local Python does not.

**To extend**: other eras = repeat with the matching campaign and that era's backgrounds
(2022CD has `*_dedx` outputs too); other lifetimes need signal MC at those lifetimes (the
v3 files carry `GenChargino_ctau`/`_isDecayed` for a lifetime reweighting, not yet used);
combining eras needs a combined fit, not just summed yields. Still missing before this
is a result: pileup and the other signal systematics, and an observed limit (needs
unblinded data).

The generic PocketCoffea `Datacard` route in the parent skill's `datacard-api.md` remains
the right tool if MC backgrounds ever go through `search_region`; none do today.

## The legacy analysis this migrates

`ref/DisappTrks/LimitSetting` (legacy CMSSW, ROOT/`TChain`-based, not PocketCoffea) is
the physics reference for what the datacard and exclusion plot need to reproduce:

- **Two signal grids**, selected by `-l wino`/`-l higgsino`
  (`validLimitTypes` in `python/limitOptions.py`): AMSB chargino direct production,
  parameterized by mass (`masses`, GeV) and proper lifetime (`lifetimes`, cm) --
  see `python/winoElectroweakLimits.py`/`higgsinoElectroweakLimits.py` for the actual
  per-era grid points (they differ: e.g. wino's Run 3 grid extends to 1200 GeV and down
  to 0.2 cm, higgsino's tops out at 1000 GeV). One datacard is produced per
  `(mass, lifetime)` grid point, named `datacard_AMSB_mGravMASS_TAUns.txt` (`scripts/
  makeDatacards.py`).
- **Per-era, per-layer-bin background configs**
  (`python/bkgdConfig_<era>[_NLayers<n>].py`) -- the legacy equivalent of this
  repo's `signal_acceptance`/fake-track/lepton-background layer-bin split
  (`NLayers4`/`NLayers5`/`NLayers6plus`), listed in `validEras` in `limitOptions.py`.
  `search_region` (above) uses this same layer-bin structure, since it mirrors the
  disappearing-track selection's own binning used throughout this analysis (see
  `disapptrks-signal-acceptance`).
- **Combine method**: `AsymptoticLimits` by default (`scripts/runLimits.py`), with
  `--cminDefaultMinimizerStrategy 1 --picky --minosAlgo stepping` and per-limit-type
  `--rMin`/`--rMax` bounds (tighter for `higgsino`: `[1e-8, 0.1]` vs. wino's
  `[1e-8, 2]`) -- a useful starting point if a new fit needs bounds, though the actual
  values should be re-derived for the Nano-tier cross sections/yields rather than
  copied blindly.
- **Plot scripts**: `scripts/makeLimitPlots.py`/`makeLimitPlotsWithCMSLumi.py` (2D
  mass-vs-lifetime exclusion contour, CMS-style luminosity/energy labels via
  `python/CMS_lumi.py`) and `test/amsbLimitPlotConfigPaper.py` for the published-paper
  plot configuration. These are ROOT-based and ~1600 lines each -- read the specific
  plotting function needed rather than the whole file, and treat them as a style/
  convention reference (label placement, contour styling, per-era combinations) rather
  than code to port line-by-line into the PocketCoffea-based pipeline.

## Route by task

- Generic `Datacard`/`MCProcess`/`SystematicUncertainty` construction, running
  `combineCards.py`/`text2workspace.py`/`combine`, and reading a `limit` TTree: see
  `pocketcoffea-datacards-limits`.
- Actually executing anything on the LPC (SSH, grid proxy, tmux, entering `./shell` for
  the PocketCoffea side and a separate CMSSW+Combine environment for the Combine side):
  see `disapptrks-lpc-execution` and `lpc-remote-session`. Note the two environments
  are genuinely separate (see `pocketcoffea-datacards-limits`'s combine-execution
  reference) -- don't expect `combine` to be available inside `./shell`.
- What category-mode/env-var shape a new search-region PocketCoffea job should follow:
  cross-check with `disapptrks-job-submission`'s existing mode table for this
  analysis's conventions (dataset JSON naming, `DISAPPTRKS_DATASET_SAMPLE`/`_YEAR`,
  layer-bin handling) before inventing a new one from scratch.

## Completion checks

- Confirm `search_region` still builds against the current checkout (category names,
  histogram names) before proposing a `Datacard` from it -- don't assume this skill's
  description of it hasn't drifted.
- State whether any limit proposed came from an actual `combine` run on cards built from
  real `search_region` output (as `limits/ctau100_2022EFG/` was), which era(s)/campaign(s)
  and backgrounds it used, and which systematics were and weren't in the cards -- a limit
  with only lumi/MC-stat/background `lnN`s must not be presented as a physics result.
- Before trusting any `combine` output, check the limit tree has all five expected
  quantiles and the log has no `ERROR` lines -- a ROOT file existing means nothing.
- If reporting a yield, confirm `genWeight`/`lumi`/`XS` are actually active in the
  `Configurator` used (don't assume -- this was silently `[]` for a long time) and
  state which dataset JSON's `xsec` metadata was used and whether it's a real
  cross-section value or the `"1.0"` placeholder. A yield built from the placeholder
  is not a physical number and shouldn't be reported as one.
- If patching `xsec` into a dataset JSON, cite which table (`signal_cross_sections`
  wino vs. `signal_cross_sections_higgsino`) and mass point, and confirm by diffing
  the JSON before/after that only `xsec` fields changed.
- If proposing a signal grid, state which limit type (wino/higgsino) and era it's based
  on, and confirm the mass/lifetime points against the *current*
  `winoElectroweakLimits.py`/`higgsinoElectroweakLimits.py` rather than the excerpt
  above, which may go stale.
- Confirm which layer bins (`NLayers4`/`5`/`6plus`, or a combined bin) the datacard
  covers, consistent with how the rest of this analysis's background estimates and
  signal-acceptance study are split.
- State whether a reported limit/exclusion came from an actual `combine` run, and
  against what datacard/workspace -- never present a placeholder or by-hand-estimated
  number as an actual Combine result.
