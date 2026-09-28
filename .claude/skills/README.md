Generic, tool-focused skills only:

- `lpc-eos` -- EOS storage on the FNAL LPC (listing/copying via the xrootd
  redirector, reading EOS files from ROOT/uproot/python)
- `lpc-crab` -- submitting, monitoring, and recovering CRAB jobs on the LPC
- `lpc-root` -- reading/writing ROOT files via uproot vs. pyroot
- `lpc-remote-session` -- SSH/grid-proxy/tmux mechanics for actually running
  something on cmslpc (not just stating the command). Never creates or
  refreshes a grid proxy itself -- checks validity and asks the user to
  refresh it when needed.
- `pocketcoffea-conventions` -- how to write PocketCoffea config/processor code
  the framework's own recommended way: `Cut`/`StandardSelection`/
  `CartesianSelection` for cutflows and categories, `HistConf`/`Axis` (and the
  `parameters.histograms` factories) for histograms, `WeightsManager`/
  `WeightWrapper` for scale factors, `ColOut` for ntuple-style output,
  Calibrators for object corrections/systematics. Generic to any analysis
  using PocketCoffea, even though only `disappearing_tracks` does today --
  check that analysis's `CLAUDE.md` for its `ref/PocketCoffea` clone.
- `pocketcoffea-datacards-limits` -- turn a merged PocketCoffea `.coffea` output into
  CMS Combine datacards via `pocket_coffea.utils.stat` (`Datacard`/`MCProcess`/
  `DataProcess`/`SystematicUncertainty`/`combine_datacards`), then run
  `combineCards.py`/`text2workspace.py`/`combine` and turn the resulting limit trees
  into exclusion/limit plots. Generic to any PocketCoffea analysis, same as
  `pocketcoffea-conventions` -- an analysis's own signal grid/process list/plot
  conventions belong in that analysis's own skill layered on top (see
  `disapptrks-datacards-limits` in `disappearing_tracks`).
- `hep-slides` -- build a HEP talk/status update as LaTeX Beamer (primary) with an
  optional .pptx export: talk structure, slide-figure conventions (mplhep CMS
  style, labels, legends, explicit `yerr` for derived quantities), a compiling
  Beamer starter template, and a pre-delivery slide check. Adapted from the
  plotting/rendering-review rules in `references/OSU-Agentic-Analysis`; that repo has
  no slide-specific content, so the talk structure and Beamer/pptx parts are a
  first draft, not lifted from it. Analysis-specific talk outlines belong in that
  analysis's own skill.
- `python-style` -- PEP 8 import organization and blank-line style

`lpc-eos`, `lpc-crab`, `lpc-root`, and `python-style` were migrated from a
personal Codex/Claude workstation setup; `lpc-crab` and `lpc-eos` were
genericized in the process (placeholder usernames/paths in place of one
person's LPC account details, and `lpc-eos`'s description no longer ties it
to one analysis). `lpc-remote-session` was written from scratch to formalize
the execution mechanics `disapptrks-lpc-execution` (in `disappearing_tracks`)
needed and to fix a gap `lpc-crab` already followed implicitly but never
stated: never create or refresh a grid proxy -- only check it.
`pocketcoffea-conventions` was written from the upstream PocketCoffea
project's own docs (`docs/concepts.md`, `docs/configuration.md`, etc.) in its
`ref/PocketCoffea` clone, not general CMS-analysis assumptions.
`pocketcoffea-datacards-limits` was written the same way, from
`docs/statistical_analysis.md` and the `pocket_coffea/utils/stat/` source, plus
general CMS Combine documentation for the parts (CMSSW+Combine environment, limit-tree
format, exclusion-plot conventions) downstream of what PocketCoffea itself provides.

Anything analysis-specific belongs in that analysis's own `.claude/skills/` instead.
