# Disappearing Tracks Analysis

Search for disappearing tracks (short, high-pT charged-particle tracks with no
associated hits further out) as a signature of long-lived charged particles. The
active analysis work is migrating the custom-NanoAOD-tier, PocketCoffea-based
analysis framework `DisappTrks_Nano` from `OSU_VERSION` 1 to 2 -- see
`nano_v2_migration_checklist.md` for the live tracking doc, and the `disapptrks-*`
skills for the individual background-estimate and diagnostic pieces this involves.

## Active repos

| Repo | Kind | LPC work area |
| --- | --- | --- |
| `DisappTrks_Nano` | PocketCoffea analysis (Nano-tier) | Self-discovered -- the checkout runs its own `setup_lpc.sh`, which records the path and exports `$DISAPPTRKS_NANO_DIR` in the checkout's `.bashrc`. Nothing to configure locally; see the `disapptrks-lpc-execution` skill. |
| `OSUNano` (`CustomNanoAOD`) | CMSSW/CRAB-based custom NanoAOD production | A per-person CMSSW release `src/` directory, one per release actually used (CMSSW_13/15/16 -- see below). `scripts/setup.py` asks for each and records it in `CLAUDE.local.md`; see the `lpc-crab` skill for how it's used. |
| `DisappTrks` | Legacy CMSSW analysis code | Read-only, via `ref/DisappTrks` below -- not a live work area. |

A read-only clone of each framework repo also lives under `ref/` for Claude to consult
(CLI behavior, config variables, docs) -- see [Reference clones](#reference-clones-ref)
below.

### Standardized LPC working-area layout

For a **newly created** working area (see the `disapptrks-lpc-working-area-setup`
skill), OSUNano production uses three CMSSW releases, and DisappTrks_Nano is nested
inside the CMSSW_15 one (its own `./shell` doesn't need CMSSW, but the group `cmsenv`s
into CMSSW_15 before using it there):

```text
/uscms_data/d3/<user>/AnalysisWorkstation/
  NanoProd_CMSSW_13/CMSSW_13_0_13/src/OSUNano/
  NanoProd_CMSSW_15/CMSSW_15_0_10/src/OSUNano/
  NanoProd_CMSSW_15/CMSSW_15_0_10/src/DisappTrks_Nano/
  NanoProd_CMSSW_16/CMSSW_16_0_6_patch1/src/OSUNano/
```

**The three releases are not all on the same node/architecture** -- confirmed against
the real installed areas' `.SCRAM/Environment` files: `CMSSW_13_0_13` only exists
under `el8_amd64_gcc11` (needs the `cmslpc-el8.fnal.gov` node, not the usual el9
`cmslpc` alias); `CMSSW_15_0_10` uses `el9_amd64_gcc12` (the el9 node's default arch);
`CMSSW_16_0_6_patch1` uses `el9_amd64_gcc13` (el9, but needs `SCRAM_ARCH` set
explicitly since it isn't the node's default). See
`disapptrks-lpc-working-area-setup` for the full per-release node/arch table.
DisappTrks_Nano itself only needs an el9 node, independent of that.

Not every contributor needs all three releases or DisappTrks_Nano -- someone doing
only PocketCoffea analysis work may need none of the CMSSW/OSUNano areas at all. An
existing, differently-named/laid-out area (e.g. the lead's own `DisTrks/` area,
referenced throughout `nano_v2_migration_checklist.md`) is not migrated to match this
-- `AnalysisWorkstation` is the standard for setting up someone new, not for renaming
someone established.

## EOS

- Personal space: `/store/user/<lpc-username>/...` (see the root `CLAUDE.md` and
  `lpc-eos` skill for the redirector convention).
- Shared production space: `/store/group/lpcdisapptrks/nano/{dev,dev_v2,prod}/` --
  raw per-job CRAB output for custom NanoAOD (`dev`/`dev_v2`, versioned per
  `OSU_VERSION`) and separately `hadd`-merged copies (`prod`) for some datasets. See
  `nano_v2_migration_checklist.md` for the current dev -> dev_v2 migration state.

## FNAL Mount

Not in active use -- NanoAOD production and PocketCoffea jobs are run and monitored
over SSH (`lpc-remote-session`, `lpc-crab`), not through a local sshfs mount.

## Scratch dirs

`nano_v2_migration_checklist.md` is the living tracking doc for the current
dev -> dev_v2 migration (per-dataset verification status, validation log). No other
scratch directories exist in this analysis yet.

## Reference clones (`ref/`)

Gitignored, per-machine symlinks to local checkouts of framework repos this
analysis depends on. Not edited directly -- read-only source for Claude Code
to consult (CLI behavior, config variables, docs) when working on this
analysis. Each teammate points their own `ref/<name>` symlink at their own
checkout; see `.claude/settings.json` for the `additionalDirectories` grant
that makes `ref/` readable.

| Clone | Path | Purpose |
| --- | --- | --- |
| DisappTrks_Nano | `ref/DisappTrks_Nano` | PocketCoffea-based Nano-tier analysis framework (CLI, `pocket_coffea/config.py`, `docs/pocket_coffea_workflows.md`) referenced by the `disapptrks-track-diagnostics`, `disapptrks-lepton-backgrounds`, `disapptrks-fake-track-background`, `disapptrks-signal-acceptance`, and `disapptrks-job-submission` skills |
| DisappTrks | `ref/DisappTrks` | Legacy CMSSW/OSUT3 analysis code -- the physics reference for background-estimate formulas (`BackgroundEstimation/python/`, `StandardAnalysis/python/EventSelections.py`, `Cuts.py`) that the Nano migration must reproduce |
| OSUNano | `ref/OSUNano` | Custom NanoAOD production framework (shared with displaced-leptons) |
| PocketCoffea | `ref/PocketCoffea` | The upstream analysis framework itself (not a DisappTrks repo) -- the source of truth for how `config.py`/`workflow.py` should use `Cut`/`StandardSelection`/`CartesianSelection`, `HistConf`/`Axis`, `WeightsManager`, `ColOut`, and calibrators. See the root `pocketcoffea-conventions` skill. |

**Active branch:** `ref/DisappTrks_Nano` currently tracks the `MattDev` development
branch, not `main` -- this is where the background-estimate work these skills document
(lepton backgrounds, fake-track background) actually lives. Since this is a per-machine
symlink, confirm with `git -C ref/DisappTrks_Nano branch --show-current` before treating
the checkout as authoritative if this note might be stale, and flag it to the user
rather than silently assuming `main` if the branch has since changed or been merged.

## `highPurity`/dE/dx selection update (resolved 2026-09-17)

The `isHighPurityTrack` requirement -- previously an open question, evaluated via the
tradeoff below -- is now required in the production disappearing-track selection
(`search_track_mask` in `DisappTrks_Nano`'s `src/disapptrks/selections.py`, used by
the `search_region` PocketCoffea mode; see `disapptrks-datacards-limits`). A
max/median dE/dx cut (`PROBE_TRACK_DEDX_MAX_OVER_MEDIAN`, `NLayers4`/`NLayers5` only)
was added to the same selection alongside it, toggleable via
`DISAPPTRKS_SEARCH_REQUIRE_DEDX_CUT` (default on) -- a genuine escape hatch, not just
defensive boilerplate: at least one existing local dev signal MC file predates the
`IsoTrackDeDxHit` branch entirely and needs it disabled.

Three skills document the tradeoff that led to this decision -- now historical
context for *why* the selection is what it is, not an open question to help resolve:

- `disapptrks-track-diagnostics` -- the `high_purity_study` Z-sideband study: which
  track/dE/dx variables discriminate real tracks from fakes.
- `disapptrks-signal-acceptance` -- the `signal_acceptance` mode: how much signal
  efficiency `highPurity` cost, per layer bin -- the number that was weighed here.
- `disapptrks-fake-track-background` -- the fake-track yield estimate. **This estimate
  predates the selection change above.** If asked about the current fake-track
  background, check whether it has been re-derived under the new highPurity+dE/dx
  selection, or flag plainly that it hasn't, rather than assuming the existing number
  still applies unchanged.

When a request references "the highPurity requirement" or a signal/fake-rejection
tradeoff, it's most likely asking about *why* the selection is what it is, or about
re-deriving a downstream number (like the fake-track estimate) under the new
selection -- not asking Claude to help decide whether to add it.
