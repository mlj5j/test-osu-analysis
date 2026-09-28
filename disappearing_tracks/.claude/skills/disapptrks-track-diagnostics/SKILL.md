---
name: disapptrks-track-diagnostics
description: Run, plot, diagnose, and interpret DisappTrks Nano fake-track sideband high-purity and per-hit/per-track dE/dx studies, including the corresponding full-selection signal comparison. Use for PocketCoffea configuration, EOS dataset JSONs, output validation, or these diagnostic PDFs; do not use for unrelated CMS histogramming.
---

# DisappTrks Track Diagnostics

Use the repository's existing PocketCoffea modes and plotting commands. Inspect
the current CLI and configuration before changing code; this workflow evolves,
and commands in an old conversation may be stale.

If asked to actually run a job or make the plots (not just say what command
would do it), this skill supplies the command but not how to execute it on the
LPC -- use `disapptrks-lpc-execution` for the SSH/proxy/tmux/container mechanics.

If asked to add or change a category, cut, or histogram in `pocket_coffea/config.py`
or `workflow.py` (not just run an existing mode), use `pocketcoffea-conventions` to
check the change follows PocketCoffea's own recommended patterns.

## Establish the current interface

Work from the `DisappTrks_Nano` checkout. Before proposing a run command:

1. Read `docs/pocket_coffea_workflows.md` for the current supported workflow.
2. Check the relevant CLI with `disapptrks <command> --help`.
3. Search `pocket_coffea/config.py` for the active `DISAPPTRKS_*` variables.
4. Treat dataset JSONs in the user's LPC checkout as authoritative when the
   user says local copies are stale. Do not rewrite or stage unrelated JSONs.

## Route by study

- For the Z fake-track sideband high-purity study, read
  [references/workflows.md](references/workflows.md), section **Z sideband**.
- For signal distributions after the complete disappearing-track selection,
  read [references/workflows.md](references/workflows.md), section **Signal**.
- For dataset creation, schema failures, missing tables, or Dask failures, read
  [references/troubleshooting.md](references/troubleshooting.md).
- When explaining or reviewing the PDFs, read
  [references/plots.md](references/plots.md).
- If asked to investigate or improve the fake-track background itself (not just
  the dE/dx diagnostics), first read
  [references/fake-track-background-estimate.md](references/fake-track-background-estimate.md)
  to distinguish this skill's rejection-cut study from the separate d0-sideband
  yield-estimate method -- then use the `disapptrks-fake-track-background` skill
  if the yield estimate itself is what's being asked about.

## Preserve these analysis invariants

- A candidate-level quantity must be calculated only from the selected
  candidate track. Link `IsoTrackDeDxHit` rows through `isoTrackIdx`; never use
  every hit row in the event as if it belonged to the candidate.
- The high-purity input plots compare the same sideband selection before and
  after the `highPurity` requirement. Each curve is shape-normalized
  independently; use the legend's `N` to assess absolute retention.
- Detailed `DeDxHitInfo` is available only for tracks satisfying the MiniAOD
  retention condition. Do not present a before/after dE/dx overlay when the
  before population lacks equivalent hit information.
- Signal dE/dx summaries must use tracks passing the full event selection, all
  disappearing-track requirements, requested fiducial maps, and `highPurity`.
- Apply the layer category to the same track that passes every other track
  requirement. Keep 4, 5, and at-least-6-layer bins distinct unless the user
  explicitly requests `combinedBins`.
- Put every environment assignment before `scripts/run_lpc_dask.sh`; anything
  after the script name is a command-line argument, not an environment value.
- Both electron and muon fiducial maps must be in effect when the comparison is meant
  to match the production search selection. Since the `MattDev` fiducial-map-auto-resolve
  change, this happens automatically by era (`self._year`/`self._era`) from the group's
  shared EOS space -- no local path needs to be set for the common case. Keep
  `DISAPPTRKS_REQUIRE_FIDUCIAL_MAPS=1` set regardless, so a resolution failure (EOS
  unreachable, an era not in the mapping) fails loudly instead of silently running with
  zero hot spots.

## Scientific interpretation

The Z sideband is enriched in fake candidates but is not truth-labeled. Treat
long tails as candidate rejection handles, not proof of fakes. Before adding a
cut, compare its sideband rejection with signal efficiency after the full
selection -- for the specific case of the `highPurity` bit itself, that signal
side is what `disapptrks-signal-acceptance` measures. That tradeoff is now decided
(`highPurity` plus a max/median dE/dx cut for `NLayers4`/`NLayers5` are required in the
production selection; see the disappearing_tracks `CLAUDE.md`'s "`highPurity`/dE/dx
selection update" section), so this study is the historical basis for it and the
template for evaluating any further track-quality cut. Be especially cautious with
upper dE/dx cuts because a slow charged signal particle can be genuinely highly
ionizing. Hit-to-hit inconsistency (for example maximum/median or spread) may be
safer than absolute ionization, but it still requires a signal scan.

Report low-statistics limitations explicitly, especially for the
six-or-more-layer sideband bin. Verify the semantics of technical flags such as
strip-shape selection before recommending them as cuts.

A new cut found here does not itself change the fake-track background's quoted
yield -- that yield comes from the separate d0-sideband transfer-factor estimate
(see [references/fake-track-background-estimate.md](references/fake-track-background-estimate.md)).
It changes the yield indirectly, by removing fakes before the full selection.

## Completion checks

- Confirm the output contains the expected histogram variable names before
  running the plotting command.
- Check entry counts and underflow/overflow annotations; unequal plot entries
  can indicate missing branches, masked values, or unavailable hit summaries.
- Keep compact per-track signal summaries separate from the much larger
  per-hit sideband diagnostics unless the user explicitly needs both.
- State whether verification was CLI/configuration-only or an end-to-end run
  inside the PocketCoffea environment.
