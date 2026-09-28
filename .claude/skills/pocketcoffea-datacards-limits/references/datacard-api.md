# The `pocket_coffea.utils.stat` Datacard API

Condensed from `docs/statistical_analysis.md` in the `ref/PocketCoffea` clone plus the
actual `pocket_coffea/utils/stat/combine.py` source. Confirm against both before
proposing code -- this toolkit is younger than the rest of the framework and field
names/defaults have moved (see the parent skill's "Establish the current interface").

```python
from pocket_coffea.utils.stat import (
    MCProcess, DataProcess, MCProcesses, DataProcesses,
    SystematicUncertainty, Systematics, Datacard,
)
from pocket_coffea.utils.stat.combine import Datacard, combine_datacards
```

## 1. Load the output

```python
from coffea.util import load

df = load("output_all.coffea")
datasets_metadata = df["datasets_metadata"]
cutflow = df["cutflow"]
```

Pick one histogram per fit category -- `hist_dict = {"SR": df["variables"]["var"], ...}`
-- and, optionally, per-category rebin edges (`None` keeps native binning). The keys of
`hist_dict` are the values on the histogram's category axis; one `Datacard` is built
per key.

## 2. Processes

`MCProcess(name, samples, years, is_signal, has_rateParam=False, label=None)`:

- `samples` are analysis sample names as they appear in `datasets_metadata`, summed
  into this one datacard process.
- `is_signal` has no default -- always pass it explicitly. `True` gets process id ≤ 0.
- `has_rateParam=True` adds a free `SF_<name> rateParam * <name>_<year> 1 [0,5]` line
  per year for this (non-signal) process.
- `MCProcesses` is an ordered, name-indexable `dict` subclass -- build it
  programmatically (e.g. one process per template bin) when useful; its
  `signal_processes`/`background_processes`/`n_processes` already expand to the
  per-year column names.

`DataProcess(name="data_obs", samples, years)` inside a `DataProcesses` container.
Exactly one is supported per `Datacard`; omit `data_processes` entirely for an
Asimov/blinded card (`observation -1`).

## 3. Systematics

`SystematicUncertainty(name, typ, processes, years, value=None, datacard_name=None,
coffea_name_alias=None)`. Field is `typ`, not `type`. `processes` is either a list (all
get the shared `value`) or a `{process: value}` dict (then omit `value`).

- **`lnN`**: `value` is the κ factor -- scalar (symmetric), `(down, up)` tuple, or via
  the per-process dict form above.
- **`shape`**: `value=1.0` by convention. `name` is the coffea variation name to look up
  as `f"{name}{shift}"` on the histogram's `variation` axis (or the value from
  `coffea_name_alias` instead, which can be a plain string or a `{process: variation}`
  dict for per-process variation names). `datacard_name` (default `name`) is the
  nuisance name actually written to the card.
- **Correlation across years is controlled by which `years` a `SystematicUncertainty`
  covers, keyed on `datacard_name`.** Several objects sharing one `datacard_name` but
  disjoint `years` stay correlated within their own group and uncorrelated across
  groups. To decorrelate a physical variation by year while keeping the coffea lookup
  year-agnostic: emit one object per year with
  `datacard_name=f"{syst}_{year}"`, `coffea_name_alias=syst`, `years=[year]`.
- Missing variation on a sample -> falls back to nominal with a printed notice (not an
  error). A shape differing from nominal by >100% in some bin prints a warning
  (`_check_shapes`, threshold hardcoded to `1.0`).

`Systematics(list_of_SystematicUncertainty)` collects them, keyed on `datacard_name` --
duplicate `datacard_name`s silently overwrite each other in that dict, so treat
"unexpectedly few nuisances in the card" as a sign to check for a `datacard_name`
collision first.

## 4. Build one `Datacard` per category

```python
datacards = {}
for cat, histograms in hist_dict.items():
    datacard = Datacard(
        histograms=histograms,
        datasets_metadata=datasets_metadata,
        cutflow=cutflow,
        years=years,
        mc_processes=mc_processes,
        data_processes=data_processes,       # omit for a blinded/Asimov card
        systematics=systematics,
        category=cat,
        bin_suffix=label,                    # defaults to "_".join(years)
        bins_edges=bins_edges_dict[cat],      # None keeps native binning
    )
    datacard.dump(
        directory=output_dir,
        card_name=f"datacard_{cat}_{label}.txt",
        shapes_name=f"shapes_{cat}_{label}.root",
    )
    datacards[f"datacard_{cat}_{label}.txt"] = datacard
```

`mcstat` (default `True`) adds `autoMCStats` with `threshold=0, include_signal=0,
hist_mode=1`; pass `False` to disable, or a dict overriding a subset of those three
keys (an unrecognized key raises `ValueError`).

Useful post-construction attributes: `datacard.bin` (the Combine bin/channel name,
`[bin_prefix_]category[_bin_suffix]`), `datacard.observation`, `datacard.rate(process,
systematic="nominal")` (negative-bin-clipped, matches the written shape's integral).

**Rate formatting**: rates are written with `format_rate` (`f"{value:.6g}"`, 6
significant figures) -- this preserves the exponent of a small rate, unlike a naive
fixed-width string slice would. Not something to reimplement; mentioned only so a very
small or very large rate rendering in scientific notation in the card isn't mistaken
for a bug.

**Card-column spacing is cosmetic.** Long per-year process suffixes can make the
`rate`/systematic columns render tightly in the `.txt` card; `combineCards.py`/
`text2workspace.py` parse it regardless. Don't "fix" this by hand-editing column widths
in a script-generated card -- fix the generator if it matters, or ignore it.

## 5. Combine categories into a workspace

```python
combine_datacards(
    datacards,                             # {filename: Datacard}
    directory=output_dir,
    path=f"combine_datacards_{label}.sh",  # must end in .sh
    card_name=f"datacard_combined_{label}.txt",
    workspace_name=f"workspace_{label}.root",
    channel_masks=False,                   # True adds --channel-masks (blinding/subset fits)
)
```

This only **writes** a shell script (`combineCards.py <bin>=<file> ... > combined.txt`
then `text2workspace.py combined.txt -o workspace.root`) -- it does not invoke Combine
itself. Run the generated `.sh` inside a CMSSW+Combine environment; see
[combine-execution.md](combine-execution.md).

## Known sharp edges

- The `shape_only_for_rateparam`/`rateparam_norm_categories` constructor arguments
  documented in some `Datacard` docstrings (rescale a `has_rateParam` process's
  shape-systematic templates so their normalization component doesn't double-count
  against the floating rate) are **not present in every checkout's `Datacard`
  constructor** -- passing them can raise `TypeError` on an older branch. Check the
  actual constructor signature (step 3 of "Establish the current interface") before
  relying on this.
- `_check_histograms` raises `ValueError` for a sample/dataset genuinely missing from
  the histogram dict (as opposed to one that's empty in `presel`, per `cutflow`, which
  is skipped with a printed notice instead) -- a real "missing histogram" error usually
  means a sample name in `MCProcess.samples` doesn't match `datasets_metadata`, not a
  bug in the `Datacard` class itself.
