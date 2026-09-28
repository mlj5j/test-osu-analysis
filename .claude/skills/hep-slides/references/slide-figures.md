# Figure conventions for slides

Adapted from `references/OSU-Agentic-Analysis/src/methodology/appendix-plotting.md`
(analysis-note rules). Slides keep the same figure-producing rules so a plot can go
in a note or a talk unchanged; only the *placement* differs (height-based in Beamer,
one message per slide).

## Base template

```python
import matplotlib.pyplot as plt
import mplhep as mh
import numpy as np

np.random.seed(42)
mh.style.use("CMS")

fig, ax = plt.subplots(figsize=(10, 10))
# Ratio plot:
# fig, (ax, rax) = plt.subplots(2, 1, figsize=(10, 10),
#     gridspec_kw={"height_ratios": [3, 1]}, sharex=True)
# fig.subplots_adjust(hspace=0)   # required -- no gap between panels

# ... plotting ...

mh.label.exp_label(exp="CMS", text="", data=True, llabel="...", lumi=..., com=13.6, ax=ax)
# text="" = no approval claimed. Set "Preliminary" ONLY if the user confirms
# the result is approved for it.

fig.savefig("name.pdf", bbox_inches="tight", dpi=200, transparent=True)
fig.savefig("name.png", bbox_inches="tight", dpi=200, transparent=True)
plt.close(fig)
```

Use `com`/`lumi`/`llabel` values that match the actual dataset -- take them from the
analysis, do not fill in plausible ones. (The reference's example uses open-data
labels for a non-CMS project; for this group's own data, the CMS label applies, with
`data=True` and `llabel` controlling the left label so "Simulation" is not stacked.)

## Rules that carry over unchanged

- **Never set absolute font sizes** -- the CMS stylesheet is tuned for 10x10. Size
  the figure on the slide instead. Relative strings (`"x-small"`) only where needed.
- **Legends:** `fontsize="x-small"`, `loc="upper right"`, then
  `from mplhep.plot import mpl_magic; mpl_magic(ax)` after all plotting so the
  y-range makes room. Manual placement only where a region is truly empty (ROC
  curves, steeply falling tails). Legend-data overlap is a must-fix -- read the
  rendered image, do not trust `loc=`.
- **No `ax.set_title`, `ax.text`, `ax.annotate`** -- use `mh.label.add_text()` for
  annotations. The slide title carries the message.
- **Histograms:** `mh.histplot` (not `ax.step`/`ax.bar`) for raw-count
  histograms; stacked MC via `mh.histplot([...], stack=True)`.
- **Derived quantities need explicit `yerr`** (ratios, efficiencies, normalized
  distributions, correction factors). Without it mplhep draws sqrt(value), e.g.
  0.03 -> 0.17 (570%), silently wrong. Test: filled with `h.fill(raw)` -> auto
  errors fine; assigned via `h.view()[:] = ...` or computed -> pass `yerr`.
- **2D plots with a colorbar:** `mh.hist2dplot(H, cbarextend=True)` or
  `mh.utils.make_square_add_cbar(ax)` -- never `fig.colorbar(im)`/`ax=ax`/
  `plt.colorbar`, which squashes the main axes.
- **Ratio panels:** `hspace=0`; hide main-panel x tick labels; pick ratio y-limits/
  ticks so no tick label sits on the panel boundary (e.g. `set_ylim(0.85, 1.15)`,
  ticks `[0.9, 1.0, 1.1]`). Experiment label on the main axes only.
- **Log y** when the range spans more than 2 decades.
- **Bin-width labels** round (0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10...) or omitted;
  never "Tracks / 0.04583".
- **No matplotlib offset text** ("1e6") -- use plain format or fold the factor into
  the label, e.g. `r"Tracks [$\times 10^6$]"`.
- **Human-readable labels** -- "Fake-track rate", not `fake_track_rate`.
- Deterministic: seed RNGs, keep the plotting script next to the figure so the
  slide can be regenerated.

## Slide-specific additions (new, not from the reference)

- Size by **height** in Beamer so a colorbar plot and a 1D plot at the same
  setting have matching plot areas: `\includegraphics[height=0.72\textheight]`
  for a single figure; two side by side at `height=0.55\textheight` each (or
  `width=0.48\textwidth`, `keepaspectratio`).
- Prefer PDF (vector) in Beamer; PNG at `dpi=200` for pptx.
- If a plot is unreadable at the size a slide allows, it is the wrong plot for a
  slide: split it, drop series, or move it to backup -- do not shrink it.
- Keep a `figures/` directory of exactly what the deck uses, plus the scripts.
