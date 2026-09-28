# Running Combine and Plotting Limits

Everything in `pocket_coffea.utils.stat` stops at writing a datacard/shapes `.root`
and a `combine_datacards_*.sh` script (see [datacard-api.md](datacard-api.md)). This
covers what happens after that: an actual CMSSW+Combine environment, running Combine,
and turning its output into an exclusion/limit plot. None of this is PocketCoffea-
specific -- it's the standard CMS Combine tool used downstream of any datacard.

## 1. The Combine environment

**Easiest route on the LPC (verified 2026-09-21, Combine v11): the standalone image on
cvmfs -- no CMSSW area, no build.**

```bash
IMG=/cvmfs/unpacked.cern.ch/gitlab-registry.cern.ch/cms-cloud/combine-standalone:latest
apptainer exec "$IMG" /bin/bash -c 'cd <dir-with-cards> && combine -M AsymptoticLimits -d card.txt -m 700 --run blind -n .M700'
```

`combine`, `combineCards.py` and `text2workspace.py` are all on the image's `PATH`. A
`cmsset_default.sh: No such file` warning from your `~/.bashrc` inside it is harmless. The
working directory must be visible in the container (home is; `/uscms_data/...` may not be
-- bind it explicitly with `-B`). Use the CMSSW-area route below only if you need a
specific Combine version or CMSSW-tied features.

Otherwise, `combineCards.py`, `text2workspace.py`, and `combine` come from the
[`HiggsAnalysis/CombinedLimit`](https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/latest/)
CMSSW package -- a *different* environment from the Apptainer/`lpcjobqueue` container a
PocketCoffea job runs in, which does not have CMSSW at all. Concretely, on the LPC this
means:

1. A CMSSW release area with `HiggsAnalysis/CombinedLimit` checked out and built
   (`cmsrel`, `cmsenv`, then the package's own install instructions -- check the
   [Combine docs](https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/latest/#installation)
   for the currently-recommended CMSSW release and install method; both drift over
   time, so don't hardcode a version from memory).
2. `cmsenv` inside that release area before any `combineCards.py`/`text2workspace.py`/
   `combine` command -- these are ordinary CMSSW-`scram`-built executables, not
   available in a bare shell or inside the PocketCoffea container.
3. If this release area doesn't exist yet for the analysis, that's a one-time setup
   step -- confirm with the user before running `cmsrel`/`scram b` (expensive,
   long-running), same as any other from-scratch CMSSW area setup.

Copy (or symlink) the datacard `.txt`, shapes `.root`, and `combine_datacards_*.sh`
from wherever the PocketCoffea job wrote them into this CMSSW area (or run Combine with
paths pointing back at them) -- the two environments are separate filesystem/software
contexts, not one continuous shell.

## 2. Build the workspace

Run the script `combine_datacards` wrote, inside `cmsenv`:

```bash
bash combine_datacards_<label>.sh
```

This runs `combineCards.py <bin>=<file> ... > datacard_combined_<label>.txt` then
`text2workspace.py datacard_combined_<label>.txt -o workspace_<label>.root`. Confirm
both commands actually printed success (no traceback, and both output files exist and
are nonzero size) before proceeding -- `text2workspace.py` failing on a malformed card
is a common silent-looking failure if only stdout is skimmed.

## 3. Run Combine

The method depends on what's being asked for:

- **Expected/observed exclusion limit** (the usual "95% CL upper limit on the signal
  strength/cross section" plotted as a function of a signal-model parameter):
  `combine -M AsymptoticLimits workspace_<label>.root`. Produces
  `higgsCombineTest.AsymptoticLimits.mH120.root` (name depends on `-n`/`-m` flags) with
  a `limit` TTree.
- **Significance** (is there an excess, not "what's excluded"): `combine -M
  Significance workspace.root [--pval] [-t -1 --expectSignal=1]` for expected, drop
  `-t -1 --expectSignal=1` for observed.
- A signal model with a very small or very large expected cross-section-times-BR can
  need explicit `--rMin`/`--rMax` bounds for the fit to converge sensibly -- if the
  default range gives a limit pinned at its edge, that's the usual cause, not
  necessarily a broken datacard. **But do not overshoot**: a huge `--rMax` (e.g. `1e6`
  for a counting experiment observing ~8 events) makes the Poisson mean vastly exceed the
  observation, the p.d.f. underflows to 0 (`RooFit ... top-level p.d.f not greater than
  zero`, `ERROR:Eval` lines), and `AsymptoticLimits` aborts after the first quantile --
  yet still writes a `higgsCombine*.root`, whose single row holds a nonsense number. Size
  `--rMax` per model from the yields (~30x the rough expected r limit is plenty; keep the
  Poisson mean at `--rMax` within a few hundred events of the observation).
- **Never trust a `higgsCombine*.root` just because it exists.** Check the `limit` tree
  has all five `quantileExpected` rows (0.025/0.16/0.5/0.84/0.975 for `--run blind`), the
  log has no `ERROR` lines, and the median is plausible against a hand estimate (e.g. sum
  the per-bin Asimov `2((s+b)ln(1+s/b) - s)` over bins for r=1 to get Z, and expect
  r_95 ~ 1.6/Z).
- `quantileExpected` is stored as float32: cast to float64 before `round`-ing and matching
  against Python float keys like `0.025`.
- Run once per signal-model point (mass, lifetime, coupling, ...) in the exclusion
  grid -- Combine itself doesn't scan a model grid; that loop lives in whatever script
  or Condor submission drives repeated `combine` invocations, one per (workspace,
  signal point).
- For a many-signal-point scan, batch via Condor rather than running each `combine`
  call serially in one shell -- see `lpc-remote-session` for the generic tmux/Condor
  mechanics; an analysis-specific job-orchestration skill (if one exists) may already
  cover the submission shape for this analysis's own grid.

## 4. Read the limit tree

`higgsCombine*.root`'s `limit` TTree has one row per quantile, keyed by
`quantileExpected`:

| `quantileExpected` | meaning |
|---|---|
| `-1` | observed limit |
| `0.025`, `0.16`, `0.5`, `0.84`, `0.975` | expected ±2σ, ±1σ, median |

```python
import uproot
with uproot.open("higgsCombineTest.AsymptoticLimits.mH120.root") as f:
    tree = f["limit"]
    quantiles = tree["quantileExpected"].array(library="np")
    limits = tree["limit"].array(library="np")
```

Match rows to quantiles by nearest value (`quantileExpected` is a float and can carry
rounding noise), not exact equality.

## 5. Build the exclusion/limit plot

An exclusion plot is built from **one point per signal-model grid point**: run steps
2-4 once per point, collect (model parameters, observed limit, expected median, ±1σ,
±2σ) into arrays, then:

- **1D scan** (limit vs. one parameter, e.g. mass at fixed lifetime): a simple line +
  shaded ±1σ/±2σ expected band, observed line overlaid, is standard (`TGraphAsymmErrors`
  in ROOT, or `matplotlib.fill_between` for the bands).
- **2D exclusion contour** (e.g. mass vs. lifetime, or mass vs. coupling): scatter the
  grid's limit values (observed and expected-median, at minimum) over the 2D parameter
  plane, then draw the excluded region as the contour where the limit crosses 1
  (`r = 1`, i.e. observed/expected cross section equals the theoretical prediction).
  With ROOT this is the standard `TGraph2D` + interpolated contour approach used in
  published CMS exclusion plots; `mplhep`/`matplotlib` with `scipy` interpolation
  (`griddata` + `contour`) is an equivalent modern alternative if the analysis isn't
  otherwise ROOT-plot-based. Grid resolution matters here -- a contour interpolated
  from a coarse grid can look smoother/more precise than the actual scan supports;
  state the grid spacing when presenting a contour.
- Use `mplhep.style.CMS` (or the analysis's own established ROOT `CMS_lumi`-style macro
  if one already exists) for CMS-standard plot styling -- axis labels, luminosity/energy
  label, "CMS Preliminary/Supplementary/[none]" tag placement -- rather than inventing a
  new house style. Check whether the analysis already has one before writing a new
  plotting script from scratch.

## Completion checks

- State which Combine method was run (`AsymptoticLimits`, `Significance`, ...) and
  whether `--rMin`/`--rMax` (or any other non-default option) was set, and why.
- For a grid scan: state how many signal points were actually run vs. how many the
  full grid calls for -- a limit plot built from a partial grid should say so, not be
  presented as the full exclusion.
- Confirm the observed/expected quantile rows were read from `quantileExpected`
  correctly (`-1` = observed) -- a swapped expected/observed line is a common,
  easy-to-miss plotting bug.
- State whether the plot came from an actual `combine` run against real Combine output,
  or is illustrative/untested.
