#!/usr/bin/env python3
"""CLI entrypoint for generating EuroPulse reports."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from europulse import config
from europulse.reporting.html_generator import generate_html_report
from europulse.reporting.pdf_generator import generate_pdf_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate EuroPulse intelligence reports")
    parser.add_argument(
        "--format",
        choices=["html", "pdf", "both"],
        default="html",
        help="Output format (default: html)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file path (default: reports/europulse_report_<timestamp>.<ext>)",
    )
    parser.add_argument(
        "--title",
        "-t",
        type=str,
        default="EuroPulse Intelligence Report",
        help="Report title",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=config.DB_PATH,
        help=f"DuckDB path (default: {config.DB_PATH})",
    )
    args = parser.parse_args()

    # Ensure reports dir exists
    reports_dir = Path(config.REPORTS_DIR)
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = []

    if args.format in ("html", "both"):
        if args.output and args.format == "both":
            out = f"{args.output}.html"
        else:
            out = args.output or str(reports_dir / f"europulse_report_{timestamp}.html")
        generate_html_report(db_path=args.db, output_path=out, title=args.title)
        results.append(f"HTML report written to: {out}")

    if args.format in ("pdf", "both"):
        if args.output and args.format == "both":
            out = f"{args.output}.pdf"
        else:
            out = args.output or str(reports_dir / f"europulse_report_{timestamp}.pdf")
        generate_pdf_report(output_path=out, db_path=args.db, title=args.title)
        results.append(f"PDF report written to: {out}")

    for msg in results:
        print(msg)

    return 0


if __name__ == "__main__":
    sys.exit(main())
