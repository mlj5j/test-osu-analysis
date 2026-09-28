#!/usr/bin/env python3
"""Export the two Beamer talks (method_overview, status_update) to .pptx.

The .tex decks stay the source of truth for structure. This script mirrors their
slide lists by hand (slide text below) and reads the numeric tables from the same
generated LaTeX table files (tables/generated/*.tex) the Beamer decks \\input, so
the numbers cannot drift from the tables. If a deck's frames change, update the
matching list here.

Usage (needs python-pptx; pdftoppm for the fit figure):
    python make_pptx.py            # writes pptx/method_overview.pptx, pptx/status_update.pptx
"""

import re
import subprocess
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor as RGB
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
NAVY = RGB(0x17, 0x49, 0x7F)
INK = RGB(0x1F, 0x1F, 0x1F)
GRAY = RGB(0x6B, 0x6B, 0x6B)
TINT = RGB(0xE8, 0xF0, 0xFA)
BAND = RGB(0xF4, 0xF6, 0xF9)
WHITE = RGB(0xFF, 0xFF, 0xFF)
FONT = "Calibri"
MONO = "Courier New"
W, H = 13.333, 7.5
LEFT, WIDTH = 0.6, 12.1


# ------------------------------------------------------------------ text markup
def add_runs(paragraph, text, size, color=INK, bold=False):
    """Add runs for `text` with light markup: **bold**, `mono`, _{sub}, ^{sup}."""
    pattern = re.compile(r"(\*\*.+?\*\*|`.+?`|_\{.+?\}|\^\{.+?\})")
    for part in pattern.split(text):
        if not part:
            continue
        run_bold, mono, baseline = bold, False, None
        if part.startswith("**"):
            part, run_bold = part[2:-2], True
        elif part.startswith("`"):
            part, mono = part[1:-1], True
        elif part.startswith("_{"):
            part, baseline = part[2:-1], -25000
        elif part.startswith("^{"):
            part, baseline = part[2:-1], 30000
        run = paragraph.add_run()
        run.text = part
        run.font.size = Pt(size)
        run.font.bold = run_bold
        run.font.name = MONO if mono else FONT
        run.font.color.rgb = color
        if baseline is not None:
            run._r.get_or_add_rPr().set("baseline", str(baseline))


def set_bullet(paragraph, indent_emu=342900):
    pPr = paragraph._p.get_or_add_pPr()
    pPr.set("marL", str(indent_emu))
    pPr.set("indent", str(-indent_emu))
    bu = pPr.makeelement(qn("a:buChar"), {"char": "\u2022"})
    pPr.append(bu)


def textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    return box, frame


# ------------------------------------------------------- LaTeX table -> cell text
REPL = [
    (r"\\pm", " ± "), (r"\\times", "×"), (r"\\geq", "≥"), (r"\\ge\b", "≥"),
    (r"\\mu", "μ"), (r"\\to", "→"), (r"\\,", " "), (r"\\hline", ""),
]


def tex_cell(text):
    text = text.strip().replace("$", "")
    for pattern, out in REPL:
        text = re.sub(pattern, out, text)
    text = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", text)
    # value with asymmetric limits: 0^{+0.066}_{-0}  ->  0 (+0.066 / −0)
    text = re.sub(r"\^\{(\+[^}]*)\}_\{(-[^}]*)\}",
                  lambda m: f" ({m.group(1)} / {m.group(2).replace('-', '−')})", text)
    text = text.replace("_{-0}", "").replace("^{+0}", "")
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("run period", "Run period")
    return text.replace("→ ee", "→ee").replace("→ μμ", "→μμ")


def parse_tex_table(path):
    """Return (rows, groups) from a bare tabular; rows = [[(text, span)...]]."""
    body = Path(path).read_text()
    body = body[body.index("}\n", body.index("\\begin{tabular}")) + 2:body.index("\\end{tabular}")]
    rows = []
    for raw in re.split(r"\\\\\s*\n", body):
        raw = raw.strip()
        raw = re.sub(r"\\(toprule|midrule|bottomrule)", "", raw).strip()
        if not raw:
            continue
        cells = []
        for cell in raw.split("&"):
            m = re.match(r"\s*\\multicolumn\{(\d+)\}\{[^}]*\}\{(.*)\}\s*$", cell)
            if m:
                cells.append((tex_cell(m.group(2)), int(m.group(1))))
            else:
                cells.append((tex_cell(cell), 1))
        rows.append(cells)
    return rows


# -------------------------------------------------------------------- slide parts
class Deck:
    def __init__(self, short_title):
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(W), Inches(H)
        self.blank = self.prs.slide_layouts[6]
        self.short_title = short_title
        self.section = ""
        self.number = 0

    def new_slide(self, title=None, footer=True):
        slide = self.prs.slides.add_slide(self.blank)
        self.number += 1
        if title:
            _, tf = textbox(slide, LEFT, 0.35, WIDTH, 1.1, MSO_ANCHOR.MIDDLE)
            add_runs(tf.paragraphs[0], title, 28, NAVY, bold=True)
        if footer:
            _, tf = textbox(slide, LEFT, 7.0, 8, 0.35)
            add_runs(tf.paragraphs[0], self.section, 11, GRAY)
            _, tf = textbox(slide, W - LEFT - 4, 7.0, 4, 0.35)
            tf.paragraphs[0].alignment = PP_ALIGN.RIGHT
            add_runs(tf.paragraphs[0], f"{self.short_title}   {self.number}", 11, GRAY)
        return slide

    def takeaway(self, slide, text):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(LEFT), Inches(6.15),
                                       Inches(WIDTH), Inches(0.6))
        shape.fill.solid()
        shape.fill.fore_color.rgb = TINT
        shape.line.fill.background()
        shape.shadow.inherit = False
        tf = shape.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.paragraphs[0].alignment = PP_ALIGN.LEFT
        add_runs(tf.paragraphs[0], text, 16, NAVY, bold=True)

    def title_slide(self, title, subtitle, author, institute, date):
        slide = self.new_slide(footer=False)
        _, tf = textbox(slide, 1.0, 1.8, W - 2.0, 1.6, MSO_ANCHOR.BOTTOM)
        add_runs(tf.paragraphs[0], title, 40, NAVY, bold=True)
        _, tf = textbox(slide, 1.0, 3.5, W - 2.0, 0.8)
        add_runs(tf.paragraphs[0], subtitle, 22, GRAY)
        _, tf = textbox(slide, 1.0, 4.9, W - 2.0, 1.6)
        for i, (line, size, bold) in enumerate([(author, 20, True), (institute, 16, False), (date, 16, False)]):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            add_runs(p, line, size, INK, bold)
            p.space_after = Pt(4)

    def bullets(self, title, items, takeaway=None, top=1.6, height=4.4, size=20):
        slide = self.new_slide(title)
        _, tf = textbox(slide, LEFT, top, WIDTH, height)
        for i, item in enumerate(items):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            set_bullet(p)
            p.space_after = Pt(10)
            add_runs(p, item, size)
        if takeaway:
            self.takeaway(slide, takeaway)
        return slide

    def table(self, slide, rows, widths, top, font=14, header_rows=1, row_h=0.36,
              merge_first_col=False, band_groups=False):
        ncols = len(widths)
        shape = slide.shapes.add_table(len(rows), ncols, Inches(LEFT), Inches(top),
                                       Inches(sum(widths)), Inches(row_h * len(rows)))
        tbl = shape.table
        tblPr = tbl._tbl.tblPr
        for attr in ("bandRow", "firstRow"):
            tblPr.set(attr, "0")
        for j, wd in enumerate(widths):
            tbl.columns[j].width = Inches(wd)
        group = 0
        for i, row in enumerate(rows):
            tbl.rows[i].height = Inches(row_h)
            if band_groups and i >= header_rows and row[0][0]:
                group += 1
            col = 0
            for text, span in row:
                cell = tbl.cell(i, col)
                if span > 1:
                    cell.merge(tbl.cell(i, col + span - 1))
                cell.margin_top = cell.margin_bottom = Inches(0.03)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                cell.fill.solid()
                header = i < header_rows
                cell.fill.fore_color.rgb = NAVY if header else (BAND if group % 2 == 0 else WHITE)
                tf = cell.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                if col >= 2 and not header:
                    p.alignment = PP_ALIGN.CENTER
                if header and col >= 1:
                    p.alignment = PP_ALIGN.CENTER
                add_runs(p, text, font, WHITE if header else INK, bold=header)
                col += span
        if merge_first_col:
            start = header_rows
            for i in range(header_rows + 1, len(rows) + 1):
                if i == len(rows) or rows[i][0][0]:
                    if i - 1 > start:
                        tbl.cell(start, 0).merge(tbl.cell(i - 1, 0))
                    start = i
        return tbl

    def table_slide(self, title, rows, widths, takeaway=None, top=1.6, **kw):
        slide = self.new_slide(title)
        self.table(slide, rows, widths, top, **kw)
        if takeaway:
            self.takeaway(slide, takeaway)
        return slide

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.prs.save(path)


def plain_rows(header, body):
    rows = [[(h, 1) for h in header]]
    rows += [[(c, 1) for c in r] for r in body]
    return rows


def flow_diagram(slide):
    def box(x, y, w, h, text):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                                       Inches(w), Inches(h))
        shape.fill.solid()
        shape.fill.fore_color.rgb = TINT
        shape.line.color.rgb = NAVY
        shape.shadow.inherit = False
        tf = shape.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        for i, line in enumerate(text.split("\n")):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = PP_ALIGN.CENTER
            add_runs(p, line, 16, INK)

    def arrow(x1, y1, x2, y2):
        c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1),
                                       Inches(x2), Inches(y2))
        c.line.color.rgb = NAVY
        c.line.width = Pt(2)
        ln = c.line._get_or_add_ln()
        ln.append(ln.makeelement(qn("a:tailEnd"), {"type": "triangle"}))

    box(4.9, 1.55, 3.5, 0.8, "Disappearing-track\nselection")
    box(1.6, 3.05, 3.6, 0.9, "Charged leptons\n(e, μ, τ_{h})")
    box(8.1, 3.05, 3.6, 0.9, "Fake tracks")
    box(0.9, 4.65, 5.0, 1.1, "Non-reconstructed lepton\nN_{est} ∝ P_{veto} P_{offline} P_{trigger}")
    box(7.4, 4.65, 5.0, 1.1, "d_{0} sideband transfer factor\nN_{fake} = ζ N_{sideband} / N_{ctrl}")
    arrow(5.6, 2.35, 3.6, 3.05)
    arrow(7.7, 2.35, 9.9, 3.05)
    arrow(3.4, 3.95, 3.4, 4.65)
    arrow(9.9, 3.95, 9.9, 4.65)


# --------------------------------------------------------------- deck: method
def build_method():
    tables = HERE / "tables" / "generated"
    d = Deck("Disappearing tracks")
    d.title_slide("Disappearing-Track Search: Analysis Overview",
                  "Signal, selection, and background methods",
                  "Matt Joyce", "The Ohio State University", "Group meeting")

    d.section = "Intro"
    d.bullets("A long-lived chargino looks like a track that stops", [
        "Wino/higgsino-like charginos, nearly degenerate with the lightest neutralino",
        "Chargino travels ~cm through the tracker, then decays to an undetectably soft pion and an invisible neutralino",
        "Signature: an isolated, high-p_{T} track with **no hits in the outer layers**",
        "Produced recoiling against initial-state radiation, so the event has large p_{T}^{miss, no μ}",
    ], "The search is a counting experiment in the disappearing-track signal region")
    d.bullets("The search requires large missing energy and a vanishing track", [
        "HLT MET trigger, then offline p_{T}^{miss, no μ} > 120 GeV with |Δφ(leading jet, p_{T}^{miss, no μ})| > 0.5",
        "Candidate track: tight quality, isolated, and fiducial (next slide)",
        "Disappearance: ≥ 3 missing outer hits, calorimeter energy < 10 GeV",
        "Results binned by the track's number of layers with hits: `NLayers4`, `NLayers5`, `NLayers6plus`",
    ], "Fewer measured layers means a shorter-lived candidate, and a different background mix")

    d.section = "Selection"
    d.table_slide("The candidate-track selection is a short list of tight cuts",
                  plain_rows(["Requirement", "Cut"], [
                      ["Kinematics", "p_{T} > 55 GeV, |η| < 2.1"],
                      ["Fiducial", "Outside ECAL crack, DT/CSC/TOB gaps; electron/muon fiducial maps"],
                      ["Hits", "≥ 4 pixel, ≥ 4 valid; no missing inner/middle hits"],
                      ["Isolation", "Charged relative isolation < 0.05"],
                      ["Impact parameter", "|d_{0}| < 0.02 cm, |d_{z}| < 0.5 cm"],
                      ["Jet / lepton veto", "ΔR(track, jet) > 0.5; ΔR > 0.15 from e, μ, τ_{h}"],
                      ["Disappearance", "≥ 3 missing outer hits; calo energy < 10 GeV"],
                  ]), [3.2, 8.9], "From `search_track_mask` in `DisappTrks_Nano`", font=16, row_h=0.5)
    d.bullets("`highPurity` and a dE/dx cut are now part of the selection", [
        "Required since 2026-09-17: the track `highPurity` bit",
        "Plus a max/median dE/dx cut, for `NLayers4` and `NLayers5` only",
        "Motivation: reject fake tracks, weighed against the signal efficiency it costs per layer bin",
        "`NLayers6plus` tracks always pass the dE/dx term",
    ], "Background numbers later in this talk are the 2026-09-17 `_dedx` outputs")

    d.section = "Backgrounds"
    slide = d.new_slide("Three backgrounds, all estimated from data")
    flow_diagram(slide)
    d.takeaway(slide, "Each is measured in a control region, then applied to the search sample")

    slide = d.bullets("A lepton that fails reconstruction looks like a disappearing track", [
        "The lepton leaves a track but is not reconstructed as a lepton",
        "It must also pass the offline and HLT p_{T}^{miss, no μ} requirements",
        "Estimate per flavor (dissertation Eq. 7.9):",
    ], "Three measured probabilities, times a control-sample count", height=2.4)
    _, tf = textbox(slide, LEFT, 4.0, WIDTH, 1.4, MSO_ANCHOR.MIDDLE)
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    add_runs(tf.paragraphs[0], "N_{est}^{ℓ} = ( N_{ctrl}^{ℓ} / ε_{trig}^{ℓ} ) · P_{veto} · P_{offline} · P_{trigger}", 30, INK)

    d.table_slide("Each probability is measured in its own control sample",
                  plain_rows(["Term", "Question answered", "How measured"], [
                      ["P_{veto}", "Track passes the lepton non-reconstruction veto",
                       "Tag-and-probe; same-sign subtraction removes Drell–Yan/fake contamination"],
                      ["P_{offline}", "Passes offline p_{T}^{miss, no μ} and Δφ cuts",
                       "Single-lepton samples; lepton re-treated as invisible"],
                      ["P_{trigger}", "Passes HLT MET given offline",
                       "Trigger-efficiency curve convolved with the p_{T}^{miss, no μ} spectrum"],
                  ]), [1.8, 4.6, 5.7], "Taus need extra steps: next two slides", font=16, row_h=0.9)
    d.bullets("Taus need two decay channels to measure P_{veto}", [
        "Tag-and-probe with τ→eνν (EGamma dataset) and τ→μνν (Muon dataset)",
        "M_{T}(p_{T}^{miss, no μ}, lepton) < 40 GeV suppresses W+jets",
        "The ΔR(track, jet) > 0.5 requirement is dropped: a hadronic tau decay is expected near a jet",
        "Same-sign subtraction, as for electrons and muons",
        "Raw counts from the two legs are combined first, then the ratio is formed; two finished per-leg estimates are not averaged",
    ])
    slide = d.bullets("The tau normalization comes from a muon+tau cross-trigger", [
        "Run 3 has no low-p_{T} single-tau trigger",
        "Instead: P(τ) = N_{μ+τ} / N_{μ}, the ratio of a muon+tau cross-trigger to a muon-only trigger (dissertation Eqs. 7.7–7.8)",
        "For 4 and 5 layers, statistics are too low: these two probabilities are taken from the combined-layer sample",
    ], height=2.6, size=18)
    d.table(slide, plain_rows(["Job", "Provides"], [
        ["`tau_mu_pveto`, `tau_ele_pveto`", "P_{veto} pair counts, both legs"],
        ["`tau_pmiss_poffline`", "N_{ctrl}, P_{offline}, P_{trigger}"],
        ["`tau_trigger_probability`", "P(τ)"],
    ]), [5.6, 6.5], top=4.4, font=16, row_h=0.5)
    d.bullets("Fake tracks are estimated from the d_{0} sideband", [
        "Fakes have a broad |d_{0}| distribution; real tracks are peaked at zero",
        "Control region: Z→μμ or Z→ee events",
        "Transfer factor ζ: fit to the folded |d_{0}| distribution relates the signal window (< 0.02 cm) to the sideband (0.05–0.50 cm)",
        "P_{fake} = ζ · N_{sideband} / N_{ctrl},    N_{fake} = P_{fake} · N_{basic}",
    ], "Measured per layer bin, per control region")
    d.bullets("The methods were validated in simulation", [
        "Lepton closure (dissertation): t t̄ and Z→ℓℓ MC with relaxed selections; estimate agrees with the observed non-reconstructed-lepton count within 1σ in all layer bins and flavors",
        "Nano-tier migration cross-checks against the legacy CMSSW code",
    ], "Closure was shown before `highPurity`; repeating it under the current selection is open")

    d.section = "Results"
    tw = [1.9, 1.4, 2.9, 2.9, 2.9]
    d.table_slide("Fake tracks dominate at 4 layers, leptons at 6 or more",
                  parse_tex_table(tables / "total_1.tex"), tw, "2022–2023, statistical uncertainties only",
                  header_rows=2, font=14, row_h=0.33, merge_first_col=True, band_groups=True, top=1.5)
    d.table_slide("The 2024–2026 periods follow the same pattern",
                  parse_tex_table(tables / "total_2.tex"), tw,
                  "2025 is largest: 29.1 ± 1.9 (4 layers), 7.95 ± 0.59 (≥ 6); statistical only",
                  header_rows=2, font=14, row_h=0.36, merge_first_col=True, band_groups=True, top=1.5)

    d.section = "Conclusion"
    d.table_slide("Backgrounds are estimated; systematics, closure and limits remain",
                  plain_rows(["Item", "State"], [
                      ["Signal selection", "`highPurity` + dE/dx in production selection"],
                      ["Fake-track background", "Estimates produced for 2022–2026 (2026-09-17 `_dedx` outputs)"],
                      ["Lepton backgrounds", "Estimates produced for 2022–2026 (same outputs)"],
                      ["Search-region yields", "`search_region` mode verified end to end"],
                      ["Limits", "No datacard built yet"],
                  ]), [3.6, 8.5], font=16, row_h=0.6)
    d.bullets("Three steps to a first result", [
        "Add systematic uncertainties (tables are statistical only)",
        "Repeat the closure tests under the current selection",
        "Build the first datacard from `search_region`",
    ])

    d.section = "Backup"
    fw = [1.4, 1.0, 2.4, 2.4, 2.45, 2.45]
    d.table_slide("Backup: fake-track estimates, 2022–2023", parse_tex_table(tables / "fake_1.tex"), fw,
                  "Both control regions shown; the total uses Z→μμ", header_rows=1, font=12,
                  row_h=0.34, merge_first_col=True, band_groups=True, top=1.5)
    d.table_slide("Backup: fake-track estimates, 2024–2026", parse_tex_table(tables / "fake_2.tex"), fw,
                  header_rows=1, font=12, row_h=0.36, merge_first_col=True, band_groups=True, top=1.5)
    png = HERE / "figures" / "fake_zmumu_fit_2025.png"
    subprocess.run(["pdftoppm", "-r", "200", "-png", "-singlefile",
                    str(HERE / "figures" / "fake_zmumu_fit_2025.pdf"), str(png.with_suffix(""))], check=True)
    slide = d.new_slide("Backup: d_{0} fit, 2025 Z→μμ, 4 layers")
    slide.shapes.add_picture(str(png), Inches(3.4), Inches(1.6), height=Inches(5.0))
    d.bullets("Backup: implementation", [
        "`DisappTrks_Nano`: PocketCoffea-based, one `DISAPPTRKS_CATEGORY_MODE` per background and study",
        "Lepton: `*_pveto`, `*_pmiss_poffline`, `fiducial_maps`",
        "Fake tracks: `fake_tracks` (`basic`, `zmumu`, `zee`)",
        "Signal: `signal_acceptance`, `search_region`",
    ])
    return d


# --------------------------------------------------------------- deck: status
def build_status():
    tables = HERE / "tables" / "generated"
    d = Deck("Status update")
    d.title_slide("Disappearing Tracks: Status Update",
                  "OSUv2 NanoAOD reprocessing and background estimates",
                  "Matt Joyce", "The Ohio State University",
                  "Production status as of 2026-09-11 (checklist pass 18)")

    d.section = "Production"
    d.table_slide("Reprocessing is done for 2025 and close for 2022–2023",
                  plain_rows(["Production", "Tasks", "Cleared or complete", "Outstanding"], [
                      ["2025 (CMSSW_15)", "56", "54 cleared", "2"],
                      ["2022/23 data (CMSSW_13)", "46", "44 cleared", "2"],
                      ["2022 EGamma (CMSSW_13)", "5", "3 cleared", "2"],
                      ["2024 (CMSSW_15)", "48", "26 complete, 18 cleared", "22 running"],
                      ["2026 (CMSSW_16)", "24", "11 complete", "13 running"],
                  ]), [4.6, 1.4, 3.6, 2.5],
                  "“Cleared” = verified against v1 (files, events, lumis); “complete” = CRAB finished",
                  font=16, row_h=0.55)
    d.table_slide("Six tasks carry known problems",
                  plain_rows(["Dataset", "Problem"], [
                      ["`Muon0_Run2025F_v2`", "Stuck at one slow site; fresh-submitted 2026-09-08 with the site blacklisted"],
                      ["`JetMET1_Run2025E_v1`", "99.8%: one job blocked by a bad source file, accepted gap"],
                      ["`Muon1_Run2023C_v4`", "99.8%: one job blocked by a bad source file, accepted gap"],
                      ["`JetMET1_Run2023C_v3`", "Resubmitted; FatJet-bug recovery task built"],
                      ["`EGamma_Run2022F`", "1.5% complete, progressing"],
                      ["`EGamma_Run2022G`", "Not started"],
                  ]), [3.8, 8.3], font=16, row_h=0.6)
    d.bullets("2024 and 2026 are running cleanly", [
        "2024: 26 of 48 complete (up from 18 the previous pass)",
        "2026: 11 of 24 complete, no failures in the latest pass",
        "Site problem at `T2_CH_CSCS` found and fixed by blacklisting it",
        "2026 era C is not being reprocessed (special runs, not used)",
        "Four AMSB wino signal MC samples (700 GeV) are complete",
    ], "Remaining failures are ordinary resubmit churn with no site pattern")

    d.section = "Selection"
    d.bullets("`highPurity` and a dE/dx cut are now in the selection", [
        "Required since 2026-09-17: the track `highPurity` bit",
        "Plus a max/median dE/dx cut for `NLayers4` and `NLayers5` only",
        "`NLayers6plus` tracks always pass the dE/dx term",
        "`search_region` yields verified end to end",
    ], "Background numbers next are the 2026-09-17 `_dedx` outputs")

    d.section = "Backgrounds"
    tw = [1.9, 1.4, 2.9, 2.9, 2.9]
    d.table_slide("Fake tracks dominate at 4 layers, leptons at 6 or more",
                  parse_tex_table(tables / "total_1.tex"), tw, "2022–2023, statistical uncertainties only",
                  header_rows=2, font=14, row_h=0.33, merge_first_col=True, band_groups=True, top=1.5)
    d.table_slide("The 2024–2026 periods follow the same pattern",
                  parse_tex_table(tables / "total_2.tex"), tw,
                  "2025 is largest: 29.1 ± 1.9 (4 layers), 7.95 ± 0.59 (≥ 6); statistical only",
                  header_rows=2, font=14, row_h=0.36, merge_first_col=True, band_groups=True, top=1.5)

    d.section = "Conclusion"
    d.bullets("Next: systematics, closure, and a first datacard", [
        "Finish the outstanding datasets; clear 2024 and 2026 as they complete",
        "Add systematic uncertainties (tables are statistical only)",
        "Repeat closure tests under the current selection",
        "Build the first datacard from `search_region`",
    ], "No limits yet: no datacard has been built")
    return d


if __name__ == "__main__":
    out = HERE / "pptx"
    build_method().save(out / "method_overview.pptx")
    build_status().save(out / "status_update.pptx")
    print("wrote", *sorted(p.name for p in out.glob("*.pptx")))
