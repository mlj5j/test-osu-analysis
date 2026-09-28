#!/usr/bin/env python3
"""Split a combined per-period LaTeX table into slide-sized tabular chunks.

The combined tables written by `disapptrks combine-*-table` are one long
`table` float (20+ rows), too tall for a Beamer frame. This keeps the numbers
untouched and only re-groups whole run-period blocks: each output file holds the
column header plus a subset of periods, as a bare `tabular` (no float, no
caption) ready for `\\input` inside a frame.

Usage:
    make_slide_tables.py tables/total_background_combined.tex \\
        --group 2022CD,2022EFG,2023C,2023D --group 2024,2025,2026 \\
        --out-prefix tables/generated/total
"""

import argparse
import re
from pathlib import Path


def split_tabular(text: str) -> tuple[str, list[str], list[str]]:
    """Return (colspec, header lines, period blocks); each block is a list of rows."""
    match = re.search(r"\\begin\{tabular\}\{([^}]*)\}\n(.*?)\\end\{tabular\}", text, re.S)
    if match is None:
        raise SystemExit("no tabular environment found")
    colspec, body = match.group(1), match.group(2)
    segments = [seg.strip("\n") for seg in re.split(r"^\\hline\s*$", body, flags=re.M)]
    segments = [seg for seg in segments if seg.strip()]
    header, blocks = segments[0], segments[1:]
    return colspec, header, blocks


def block_period(block: str) -> str:
    return block.splitlines()[0].split("&")[0].strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("table", type=Path)
    parser.add_argument("--group", action="append", required=True,
                        help="comma-separated run periods for one output file")
    parser.add_argument("--out-prefix", type=Path, required=True)
    args = parser.parse_args()

    colspec, header, blocks = split_tabular(args.table.read_text())
    by_period = {block_period(block): block for block in blocks}
    args.out_prefix.parent.mkdir(parents=True, exist_ok=True)

    for index, group in enumerate(args.group, start=1):
        periods = [p.strip() for p in group.split(",")]
        missing = [p for p in periods if p not in by_period]
        if missing:
            raise SystemExit(f"periods not in table: {missing}; have {list(by_period)}")
        parts = [f"\\begin{{tabular}}{{{colspec}}}", "\\toprule", header, "\\midrule"]
        for i, period in enumerate(periods):
            parts.append(by_period[period])
            parts.append("\\midrule" if i < len(periods) - 1 else "\\bottomrule")
        parts.append("\\end{tabular}")
        out = Path(f"{args.out_prefix}_{index}.tex")
        out.write_text("\n".join(parts) + "\n")
        print(out)


if __name__ == "__main__":
    main()
