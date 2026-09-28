---
name: disapptrks-fake-track-background
description: Compute and interpret the DisappTrks Nano/PocketCoffea data-driven fake-track background estimate -- the N_fake = zeta * N_ctrl d0 transfer-factor method from Z->mumu/Z->ee/basic-JetMET sideband control regions, including the Chapter-5 AN-style fixed/fit-zeta path and the general transfer-factor-category path, plus sideband diagnostic plots and event manifests. Use for the fake_tracks PocketCoffea category mode, the estimate-fake-tracks/make-standard-fake-track-estimate CLI commands, or Table-34-style fake-track yield tables. Do not use for the dE/dx rejection-cut sideband study (see disapptrks-track-diagnostics) or the charged-lepton background (see disapptrks-lepton-backgrounds).
---

# DisappTrks Fake-Track Background Estimate

Work from the `DisappTrks_Nano` checkout (`ref/DisappTrks_Nano`). This is the
data-driven yield estimate for the fake-track background -- the number quoted in the
final result -- not the dE/dx rejection-cut study (`disapptrks-track-diagnostics`) or
the charged-lepton background (`disapptrks-lepton-backgrounds`).

**Active context:** `highPurity` (plus a max/median dE/dx cut for `NLayers4`/`NLayers5`)
is now required in the production selection (resolved 2026-09-17; see the
disappearing_tracks `CLAUDE.md`'s "`highPurity`/dE/dx selection update" section and
`search_track_mask` in `src/disapptrks/selections.py`). **This estimate predates that
change.** If asked for the current fake-track background, check whether it has been
re-derived under the highPurity+dE/dx selection, or say plainly that it hasn't --
don't assume an existing number still applies. Re-deriving it under the new selection
is a natural thing to propose, not just re-running the estimate as-is.

If asked to actually run a job or produce the estimate (not just say what
command would do it), this skill supplies the command but not how to execute
it on the LPC -- use `disapptrks-lpc-execution` for the SSH/proxy/tmux/
container mechanics.

If asked to add or change a `fake_tracks` category or histogram (not just run
the estimate), use `pocketcoffea-conventions` to check the change follows
PocketCoffea's own recommended patterns.

## Establish the current interface

Category names, histogram names, and CLI arguments below are illustrative; this code
evolves. Before proposing a command:

1. Check `disapptrks estimate-fake-tracks --help` and
   `disapptrks make-standard-fake-track-estimate --help`.
2. Search `pocket_coffea/config.py` for `fake_track_control_mode` and the
   `fake_track_*_categories` dicts to see the current category set for
   `DISAPPTRKS_CATEGORY_MODE=fake_tracks`.
3. Search `src/disapptrks/selections.py` for `fake_track_cuts` and
   `fake_track_diagnostic_cuts` for the current cut definitions behind those
   categories.
4. Read the module docstring and `AN_FIXED_TRANSFER_FACTORS` table at the top of
   `src/disapptrks/fake_tracks.py` for the current fixed zeta values and formula.

## Two estimate methods -- know which one is being asked for

- **AN/Chapter-5 method** (`estimate-fake-tracks --an-control zmumu|zee`): the
  dissertation's method (Section 7.4.2) -- a Z->ll control region, a Gaussian+constant
  fit (or a fixed, period-specific value) to the folded |d0| sideband gives a transfer
  factor zeta, and `P_fake = zeta * N_sideband/N_control`. This is what
  `make-standard-fake-track-estimate` runs by default.
- **General method** (`estimate-fake-tracks` without `--an-control`): the newer
  `N_fake = xi * N_ctrl` convention, where `xi` is a direct category-count ratio
  (`fake_basic3hits_d0_signal` / `fake_basic3hits_d0_sideband`, i.e. a 3-hit/basic-track
  proxy population's own d0 signal-vs-sideband ratio) rather than a fit, and the control
  region can be the basic/JetMET selection directly rather than only Z->ll.

If a request just says "the fake-track background," default to the AN/Chapter-5 method
via `make-standard-fake-track-estimate` -- it is the one with fixed dissertation-derived
zeta values and the one the standardized output layout expects. Ask, or say which one
you assumed, if it matters which.

For running PocketCoffea, producing the estimate, plotting, and the manifest, read
[references/workflow.md](references/workflow.md). For the exact formulas and how they
map onto the dissertation's Section 7.4.2 notation, read
[references/formulas.md](references/formulas.md).

## Preserve these invariants

- `basic`, `zmumu`, and `zee` control regions require *different* datasets
  (`DATA_JetMET`/`DATA_MET`, `DATA_Muon`, `DATA_EGamma` respectively) and different
  `DISAPPTRKS_FAKE_TRACK_CONTROL` values -- do not mix a `zmumu`-selected output with a
  `DATA_EGamma` sample or vice versa.
- Fake-track jobs need *both* electron and muon fiducial maps, unlike the leg-specific
  Pveto/tau modes -- legacy fake-track selections inherited both
  `cutTrkFiducialElectron` and `cutTrkFiducialMuon` (plus the ECAL fiducial flag) from
  the generic track selection. Both now resolve automatically from the shared EOS space
  by era; no local path needs to be hand-configured for either flavor.
- `--basic-files` requires `--basic-yield-category` -- the CLI raises `SystemExit`
  otherwise. `make-standard-fake-track-estimate` fills this in for you
  (`basic_selection` default).
- `--an-control` requires coffea files, not `--counts-json`; `--fit-plot` requires
  `--transfer-factor-source fit`.
- `--transfer-factor-source fit` needs enough sideband entries in
  `0.10 <= |d0| < 0.50 cm` to fit (the code raises `ValueError` if there are fewer than
  3 bins or zero total entries) -- fall back to `fixed` for a low-statistics period, and
  say so explicitly rather than silently reporting a fit that didn't really constrain
  anything.
- The fixed AN zeta values in `AN_FIXED_TRANSFER_FACTORS` are keyed by run period
  (`2022CD`, `2022EFG`, `2023C`, `2023D`) and control region (`zmumu`, `zee`) with
  built-in aliasing (e.g. `2022_postEE` -> `2022EFG`) -- if a period isn't in that table,
  either add it (with its own AN/fit derivation, not a guess) or use
  `--transfer-factor-source fit`.
- `DISAPPTRKS_ENABLE_FAKE_SIDEBAND_HISTOGRAMS=0` for production jobs -- it skips the
  exploratory per-hit-pattern/dE/dx histograms and event manifest while keeping the
  estimate counts and transfer-factor-fit histograms. Leave it at its default (`1`) only
  when the sideband diagnostic plots or manifest are actually wanted.

## Completion checks

- State which method was used (AN/Chapter-5 fixed, AN/Chapter-5 fit, or general) and
  why.
- For a fit-based transfer factor, report the fit quality (amplitude, sigma, constant,
  and whether `--fit-plot` was inspected) rather than just the resulting zeta.
- Cross-check a new estimate against the dissertation's Table 7.29/7.30 values (via
  [references/formulas.md](references/formulas.md)) when working on a run period that
  table already covers -- a large discrepancy likely means a category-name or
  dataset/control mismatch, not a real physics change.
- State whether verification was CLI/JSON-output-only or included inspecting the
  sideband diagnostic plots or event manifest.
